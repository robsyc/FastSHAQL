"""Parse ``sh:PropertyShape`` blank nodes / named shapes into :class:`PropertyShapeIR`.

See: https://www.w3.org/TR/shacl12-core/#property-shapes
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rdflib import RDF, SH, URIRef

from fastshaql.core.ir import PropertyShapeIR
from fastshaql.core.ir.node_expr import is_multivalued_capable
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.kernel.constants import STRING_FAMILY_DATATYPES

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
    SH_CLASS,
    SH_CODE_IDENTIFIER,
    first_localized_str,
    object_int,
    object_str,
    object_uri,
    property_graphql_field_name,
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


def _datatypes_from_shape(
    graph: Graph,
    prop_shape: Node,
    *,
    shape_iri: URIRef,
    field_name: str,
) -> tuple[URIRef, ...]:
    """Declared datatype constraints from ``sh:datatype`` / datatype-only
    ``sh:or`` (SHACL 1.2 Core §7.1.2, §7.7.3) — both union syntaxes
    normalize into one tuple.

    Rules: a single ``sh:datatype`` IRI is the classic form; a ``sh:datatype``
    SHACL list and an ``sh:or`` list whose members' only constraint is a
    single ``sh:datatype`` IRI are the union forms. Any other ``sh:or`` is
    parse-recognized-and-inert (warning; datatypes unchanged). Multi-entry
    sets are restricted to the string family
    (:data:`STRING_FAMILY_DATATYPES`) — outside it, loud rejection:
    silently flattening e.g. a numeric/string union to ``String`` would
    misdescribe the field.

    Raises:
        UnsupportedShapeError: On ``sh:datatype`` together with ``sh:or``
            or more than one ``sh:or`` value (legal SHACL, ANDed §7.7.3 —
            fastshaql lowers one datatype constraint); more than one
            ``sh:datatype`` value (ill-formed per the at-most-one rule,
            §7.1.2); an empty ``sh:datatype`` list; a malformed list; a
            non-IRI list member; or a multi-entry set outside the string
            family (message names the supported members).
    """
    at = f"sh:datatype/sh:or on {shape_iri} field {field_name!r}"
    datatypes = _datatype_objects(graph, prop_shape, at=at)
    or_values = list(graph.objects(prop_shape, SH["or"]))
    if datatypes and or_values:
        raise UnsupportedShapeError(
            f"{at}: sh:datatype and sh:or together is unsupported "
            "(SHACL ANDs the constraints, §7.7.3; fastshaql lowers one datatype constraint)"
        )
    if len(or_values) > 1:
        raise UnsupportedShapeError(
            f"{at}: multiple sh:or values are unsupported "
            "(SHACL ANDs the lists, §7.7.3; fastshaql lowers one)"
        )
    if or_values:
        or_datatypes = _or_datatypes(
            graph, or_values[0], shape_iri=shape_iri, field_name=field_name
        )
        if or_datatypes is None:
            return ()
        datatypes = or_datatypes
    if len(datatypes) > 1 and not set(datatypes) <= STRING_FAMILY_DATATYPES:
        raise UnsupportedShapeError(
            f"{at}: multi-entry datatype sets support the string family only "
            f"(xsd:string rdf:langString rdf:dirLangString; got "
            f"{' '.join(str(dt) for dt in datatypes)})"
        )
    return tuple(dict.fromkeys(datatypes))


def _datatype_objects(graph: Graph, prop_shape: Node, *, at: str) -> list[URIRef]:
    """``sh:datatype`` objects — the IRI form directly, the SHACL-list form
    walked (well-formedness and all-IRI members enforced; the empty list
    ``rdf:nil`` rejects — it is an IRI, not a datatype)."""
    values = list(graph.objects(prop_shape, SH.datatype))
    if len(values) > 1:
        raise UnsupportedShapeError(
            f"{at}: multiple sh:datatype values (SHACL 1.2 §7.1.2: "
            "a shape has at most one value for sh:datatype)"
        )
    if not values:
        return []
    value = values[0]
    if value == RDF.nil:
        raise UnsupportedShapeError(
            f"{at}: sh:datatype list is empty — declare at least one datatype IRI"
        )
    if isinstance(value, URIRef):
        return [value]
    members = strict_rdf_list(graph, value, what=f"{at}: sh:datatype")
    iri_members: list[URIRef] = []
    for member in members:
        if not isinstance(member, URIRef):
            raise UnsupportedShapeError(
                f"{at}: sh:datatype list members must be IRIs (got {member!r})"
            )
        iri_members.append(member)
    return iri_members


def _or_datatypes(
    graph: Graph,
    or_head: Node,
    *,
    shape_iri: URIRef,
    field_name: str,
) -> tuple[URIRef, ...] | None:
    """Datatypes of a datatype-only ``sh:or`` list, or ``None`` when any
    member carries another constraint (that ``sh:or`` is inert — warning)."""
    members = strict_rdf_list(
        graph, or_head, what=f"sh:or on {shape_iri} field {field_name!r}"
    )
    datatypes: list[URIRef] = []
    for member in members:
        datatype = _sole_datatype_constraint(graph, member)
        if datatype is None:
            logger.warning(
                "sh:or on %s field %r carries non-datatype constraints — "
                "validator-only, ignored for reads",
                shape_iri,
                field_name,
            )
            return None
        datatypes.append(datatype)
    return tuple(datatypes)


def _sole_datatype_constraint(graph: Graph, member: Node) -> URIRef | None:
    """The member's single ``sh:datatype`` IRI when it is the member's only
    constraint, else ``None``."""
    predicates = set(graph.predicates(member, None))
    if predicates != {SH.datatype}:
        return None
    objects = list(graph.objects(member, SH.datatype))
    if len(objects) != 1 or not isinstance(objects[0], URIRef):
        return None
    return objects[0]


def parse_property_shape(
    graph: Graph,
    prop_shape: Node,
    *,
    parent_graphql_type_name: str,
    description_language: str = "en",
) -> PropertyShapeIR:
    """Parse a single ``sh:PropertyShape`` into :class:`PropertyShapeIR`.

    Blank-node property shapes receive a synthesized ``urn:fastshaql:inline:…`` IRI.

    Args:
        graph: An RDFLib graph containing the property shape definition.
        prop_shape: The property shape resource (URIRef or BNode).
        parent_graphql_type_name: GraphQL type name of the parent node shape
            (used for blank-node IRI synthesis).
        description_language: BCP 47 tag for selecting ``description`` text. Defaults to ``"en"``.

    Returns:
        A parsed property shape.

    Raises:
        MissingShaclPathError: When ``sh:path`` is absent.
        UnsupportedShaclPathError: When ``sh:path`` uses unsupported modifiers.
        MissingCompositePathCodeIdentifierError: When a composite path lacks ``sh:codeIdentifier``.
        UnsupportedShapeError: When ``sh:values`` violates the derived-field
            boundary (ADR-0015) — composite path, missing ``sh:datatype`` on a
            non-relationship, list cardinality on a single-valued arm, or an
            unsupported node-expression form — when ``sh:defaultValue``
            violates the scalar-only fallback boundary (composite path,
            relationship anchor, missing ``sh:datatype``, list cardinality,
            multi-valued arm), or when the ``sh:datatype``/datatype-only
            ``sh:or`` declaration combines forms fastshaql cannot lower or
            sits outside the recognized string-family universe for
            multi-entry sets (:func:`_datatypes_from_shape`).
    """
    path = parse_shacl_path(graph, prop_shape)

    field_name = property_graphql_field_name(
        path=path,
        code_identifier=object_str(graph, prop_shape, SH_CODE_IDENTIFIER),
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

    value_class = object_uri(graph, prop_shape, SH_CLASS)
    if value_class is not None:
        class_values = [
            o for o in graph.objects(prop_shape, SH_CLASS) if isinstance(o, URIRef)
        ]
        if len(class_values) > 1:
            raise NotImplementedError(
                f"Multiple sh:class values on {prop_shape} — AND semantics (SHACL §7.1.1) not yet supported"
            )

    node_ref = object_uri(graph, prop_shape, SH.node)
    if node_ref is not None and not isinstance(node_ref, URIRef):
        raise NotImplementedError(
            f"Blank-node sh:node on {prop_shape} — inline node shapes are not supported"
        )

    in_values = parse_shacl_in(graph, prop_shape)
    values_expr = parse_node_expr(graph, prop_shape)
    default_expr = parse_default_value(graph, prop_shape)

    is_relationship = value_class is not None or node_ref is not None
    if is_relationship and in_values is not None:
        logger.warning(
            "Relationship-overlay sh:in on %s field %r — read-ignored; fastshaql performs no write-validation",
            shape_iri,
            field_name,
        )

    datatypes = _datatypes_from_shape(
        graph, prop_shape, shape_iri=shape_iri, field_name=field_name
    )
    min_count = object_int(graph, prop_shape, SH.minCount)
    max_count = object_int(graph, prop_shape, SH.maxCount)

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
        value_class=value_class,
        value_shape_iri=node_ref,
        in_values=in_values,
        values_expr=values_expr,
        default_expr=default_expr,
    )
