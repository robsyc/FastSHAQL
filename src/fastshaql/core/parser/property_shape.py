"""Parse ``sh:PropertyShape`` blank nodes / named shapes into :class:`PropertyShapeIR`.

See: https://www.w3.org/TR/shacl12-core/#property-shapes
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rdflib import RDF, SH, Literal, URIRef

from fastshaql.core.ir import PropertyShapeIR
from fastshaql.core.ir.node_expr import is_multivalued_capable
from fastshaql.core.ir.shacl_path import PredicatePath

from .datatypes import datatypes_from_shape
from .node_expr import (
    UnsupportedShapeError,
    arm_label,
    parse_default_value,
    parse_node_expr,
    reject_derived_path_targets,
)
from .shacl_in import parse_shacl_in
from .shacl_path import parse_shacl_path
from .util import (
    SH_AND,
    SH_CLASS,
    first_localized_str,
    object_int,
    property_graphql_field_name,
    read_code_identifier,
    strict_rdf_list,
    synthesize_inline_shape_iri,
)

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node

    from fastshaql.core.ir.node_expr import NodeExprIR
    from fastshaql.core.ir.shacl_path import ShaclPropertyPath

logger = logging.getLogger(__name__)


def _check_derived_field_boundaries(
    shape_iri: URIRef,
    field_name: str,
    path: ShaclPropertyPath,
    values_expr: NodeExprIR,
    *,
    is_relationship: bool,
    datatypes: tuple[URIRef, ...],
    min_count: int | None,
    max_count: int | None,
) -> None:
    """Enforce the derived-field boundary (ADR-0015) on one ``sh:values`` field.

    A multi-entry (string-union) datatype set satisfies the requirement — a
    derived field may carry tagged values; the chain lowering covers it.

    Raises:
        UnsupportedShapeError: When the path is composite, a non-relationship
            field lacks ``sh:datatype``, or list cardinality rides a
            single-valued node-expression arm.
    """
    if not isinstance(path, PredicatePath):
        raise UnsupportedShapeError(
            f"sh:values on {shape_iri} field {field_name!r} requires a predicate sh:path (composite paths are not supported)"
        )
    if not is_relationship and not datatypes:
        raise UnsupportedShapeError(
            f"derived field {field_name!r} on {shape_iri} requires sh:datatype (or a relationship anchor sh:class/sh:node)"
        )
    if min_count is not None:
        logger.warning(
            "sh:minCount on derived field %r on %s is ignored for validation (expression is the source of truth); cardinality emission still uses min_count=%s",
            field_name,
            shape_iri,
            min_count,
        )
    if max_count != 1 and not is_multivalued_capable(values_expr):
        raise UnsupportedShapeError(
            f"derived list field {field_name!r} on {shape_iri} uses "
            f"{arm_label(values_expr)} (≤1 value per focus node); "
            "use a multi-valued arm (sh:select, shnex:pathValues, "
            "shnex:ListExpression, multi-branch shnex:if) for list derivation"
        )


def _check_default_value_boundaries(
    shape_iri: URIRef,
    field_name: str,
    path: ShaclPropertyPath,
    default_expr: NodeExprIR,
    *,
    is_relationship: bool,
    datatypes: tuple[URIRef, ...],
    max_count: int | None,
) -> None:
    """Enforce the scalar-only ``sh:defaultValue`` boundary (ADR-0015)
    on one defaulted field.

    A multi-entry (string-union) datatype set satisfies the requirement —
    the fallback composes with the chain lowering. The step-3 fallback
    lowers to ``OPTIONAL { … } BIND(COALESCE(?v, d) AS ?out)`` — per-entity
    set-emptiness is flat-expressible exactly for a single
    statically-single-valued scalar, so composite paths, relationships,
    list cardinality, and multi-valued arms reject loudly.
    """
    at = f"sh:defaultValue on {shape_iri} field {field_name!r}"
    if not isinstance(path, PredicatePath):
        raise UnsupportedShapeError(
            f"{at} requires a predicate sh:path (composite paths are not supported)"
        )
    if is_relationship:
        raise UnsupportedShapeError(
            f"{at} is scalar-only "
            "(a defaulted relationship would need per-entity emptiness over join rows)"
        )
    if not datatypes:
        raise UnsupportedShapeError(f"{at} requires sh:datatype")
    if max_count != 1:
        raise UnsupportedShapeError(
            f"{at} requires maxCount 1 (multi-valued fallbacks are not supported)"
        )
    if is_multivalued_capable(default_expr):
        raise UnsupportedShapeError(
            f"{at} uses {arm_label(default_expr)} — the fallback must be statically "
            "single-valued"
        )


def _and_class_values(graph: Graph, prop_shape: Node) -> tuple[URIRef, ...]:
    """Classes contributed by ``sh:and`` members whose sole constraint is
    ``sh:class`` (SHACL Core §7.7.2 — the same conjunction as repeated
    ``sh:class`` values, §3.1.1). A member carrying any other constraint
    warns and voids the whole ``sh:and``: consuming its class slice alone
    would loosen it.
    """
    classes: list[URIRef] = []
    for head in graph.objects(prop_shape, SH_AND):
        for member in strict_rdf_list(graph, head, what=f"sh:and on {prop_shape}"):
            values = list(graph.objects(member, SH_CLASS))
            if set(graph.predicates(member, None)) != {SH_CLASS} or not all(
                isinstance(v, URIRef) for v in values
            ):
                logger.warning(
                    "sh:and on %s carries members beyond sh:class — "
                    "validator-only, ignored for reads",
                    prop_shape,
                )
                return ()
            classes.extend(v for v in values if isinstance(v, URIRef))
    return tuple(classes)


def _class_values(
    graph: Graph, prop_shape: Node, *, node_ref: URIRef | None
) -> tuple[URIRef, ...]:
    """The binding class constraints (SHACL Core §7.1.1): the ``sh:class``
    values conjoined with classes from class-only ``sh:and`` members
    (§7.7.2), IRI-sorted for deterministic emission.

    The 1.2 list form (union semantics) rejects loudly until polymorphic
    relationships land (ADR-0026); conjoined classes without ``sh:node``
    reject with guidance — their intersection names no target shape.

    Raises:
        UnsupportedShapeError: On a literal value (§7.1.1: IRIs or lists
            of IRIs only), the list form, or conjoined classes without
            ``sh:node``.
    """
    at = f"sh:class on {prop_shape}"
    flat = {v for v in graph.objects(prop_shape, SH_CLASS) if isinstance(v, URIRef)}
    for value in graph.objects(prop_shape, SH_CLASS):
        if value == RDF.nil:
            raise UnsupportedShapeError(
                f"{at}: the sh:class list form is empty — declare at least one class IRI"
            )
        if isinstance(value, Literal):
            raise UnsupportedShapeError(
                f"sh:class value {value!r} on {prop_shape} is not an IRI "
                "(SHACL §7.1.1: values are IRIs or lists of IRIs)"
            )
        if not isinstance(value, URIRef):
            raise UnsupportedShapeError(
                f"{at}: the sh:class list form (union of target classes, SHACL 1.2 "
                "§7.1.1) is not lowered yet — declare one class per property until "
                "polymorphic relationships land"
                + (
                    " (a list cannot express the binding union beside sh:node either)"
                    if node_ref is not None
                    else ""
                )
            )
    flat.update(_and_class_values(graph, prop_shape))
    values = tuple(sorted(flat, key=str))
    if len(values) > 1 and node_ref is None:
        raise UnsupportedShapeError(
            f"{at}: multiple conjoined classes (sh:class, sh:and) intersect "
            "(SHACL §7.1.1) but name no shape — add sh:node to select the target"
        )
    return values


def _sole_node_ref(graph: Graph, prop_shape: Node) -> URIRef | None:
    """The ``sh:node`` value-shape anchor (SHACL Core §7.8.1) — the target.

    Values must be well-formed node shapes. A blank node (an inline shape)
    rejects loudly — silently dropping it would degrade the field to a
    scalar. Multiple values reject with the targeting model's remedy:
    conformance to several node shapes selects no single GraphQL type.

    Raises:
        UnsupportedShapeError: On a literal value, a blank-node value, or
            multiple values.
    """
    values = list(graph.objects(prop_shape, SH.node))
    if len(values) > 1:
        raise UnsupportedShapeError(
            f"Multiple sh:node values on {prop_shape} — the spec conjoins them "
            "(SHACL §7.8.1) but conformance to several shapes selects no single "
            "GraphQL type; declare one target"
        )
    if not values:
        return None
    value = values[0]
    if isinstance(value, Literal):
        raise UnsupportedShapeError(
            f"sh:node value {value!r} on {prop_shape} is not a node shape (SHACL §7.8.1)"
        )
    if not isinstance(value, URIRef):
        raise UnsupportedShapeError(
            f"Blank-node sh:node on {prop_shape} — inline node shapes are not supported"
        )
    return value


def parse_property_shape(
    graph: Graph,
    prop_shape: Node,
    *,
    parent_graphql_type_name: str,
    description_language: str = "en",
) -> PropertyShapeIR | None:
    """Parse a single ``sh:PropertyShape`` into :class:`PropertyShapeIR`.

    Blank-node property shapes receive a synthesized ``urn:fastshaql:inline:…`` IRI.

    Args:
        graph: An RDFLib graph containing the property shape definition.
        prop_shape: The property shape resource (URIRef or BNode).
        parent_graphql_type_name: GraphQL type name of the parent node shape
            (used for blank-node IRI synthesis).
        description_language: BCP 47 tag for selecting ``description`` text. Defaults to ``"en"``.

    Returns:
        The parsed property shape, or ``None`` when the property can never
        hold values — empty ``sh:in`` (§7.9.3) or ``sh:maxCount`` below 1
        (§7.2.2) — in which case no field is generated and a warning is
        logged (the ``sh:deactivated`` reading, §3.1.6).

    Raises:
        MissingShaclPathError / UnsupportedShaclPathError: ``sh:path`` absent
            or ill-formed — multiple values (§3.3), unsupported modifiers,
            empty or short lists (§4.2/§4.3), cycles (§4).
        MissingCompositePathCodeIdentifierError: composite path without
            ``sh:codeIdentifier``.
        InvalidCodeIdentifierError: ``sh:codeIdentifier`` outside the §8.4 grammar.
        UnsupportedShapeError: malformed ``sh:minCount``/``sh:maxCount``
            (§7.2); derived-field and default-value boundary violations
            (ADR-0015); datatype/``sh:or`` forms fastshaql cannot lower
            (:func:`~fastshaql.core.parser.datatypes.datatypes_from_shape`);
            and the targeting forms with no lowering (ADR-0025): the
            ``sh:class`` list form (§7.1.1 union — ADR-0026), conjoined
            classes without ``sh:node``, multiple ``sh:node`` values, or a
            blank-node ``sh:node`` (inline node shape).
    """
    path = parse_shacl_path(graph, prop_shape)

    field_name = property_graphql_field_name(
        path=path,
        code_identifier=read_code_identifier(graph, prop_shape),
        prop_shape=prop_shape,
    )
    shape_iri = (
        prop_shape
        if isinstance(prop_shape, URIRef)
        else synthesize_inline_shape_iri(
            parent_graphql_type_name=parent_graphql_type_name,
            graphql_field_name=field_name,
        )
    )

    node_ref = _sole_node_ref(graph, prop_shape)
    value_classes = _class_values(graph, prop_shape, node_ref=node_ref)

    in_values = parse_shacl_in(graph, prop_shape)
    if in_values == ():
        logger.warning(
            "Empty sh:in on %s — the property can never hold values; no field is generated",
            prop_shape,
        )
        return None
    values_expr = parse_node_expr(graph, prop_shape)
    default_expr = parse_default_value(graph, prop_shape)

    is_relationship = bool(value_classes) or node_ref is not None
    if is_relationship and in_values is not None:
        logger.warning(
            "Relationship-overlay sh:in on %s field %r — read-ignored; fastshaql performs no write-validation",
            shape_iri,
            field_name,
        )

    datatypes = datatypes_from_shape(
        graph, prop_shape, shape_iri=shape_iri, field_name=field_name
    )
    min_count = object_int(graph, prop_shape, SH.minCount, what="sh:minCount")
    max_count = object_int(graph, prop_shape, SH.maxCount, what="sh:maxCount")
    if max_count is not None and max_count < 1:
        logger.warning(
            "sh:maxCount %d on %s — the property can never hold values; no field is generated",
            max_count,
            prop_shape,
        )
        return None

    if values_expr is not None:
        _check_derived_field_boundaries(
            shape_iri,
            field_name,
            path,
            values_expr,
            is_relationship=is_relationship,
            datatypes=datatypes,
            min_count=min_count,
            max_count=max_count,
        )
        reject_derived_path_targets(graph, values_expr, shape_iri, field_name)
    if default_expr is not None:
        _check_default_value_boundaries(
            shape_iri,
            field_name,
            path,
            default_expr,
            is_relationship=is_relationship,
            datatypes=datatypes,
            max_count=max_count,
        )
    return PropertyShapeIR(
        iri=shape_iri,
        description=first_localized_str(
            graph,
            prop_shape,
            SH.description,
            SH.name,
            lang=description_language,
        ),
        graphql_field_name=field_name,
        path=path,
        datatypes=datatypes,
        min_count=min_count,
        max_count=max_count,
        value_classes=value_classes,
        value_shape_iri=node_ref,
        in_values=in_values,
        values_expr=values_expr,
        default_expr=default_expr,
    )
