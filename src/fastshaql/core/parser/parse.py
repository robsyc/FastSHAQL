"""SHACL shapes graph → ShapeRegistry.

Three-pass parse:
(1) walk the graph into ``NodeShapeIR`` / ``PropertyShapeIR`` dataclasses,
(2) resolve relationships per the targeting model (ADR-0025) and
polymorphic members (ADR-0026),
(3) flatten ``sh:node`` inheritance (ADR-0005) — merge parent property shapes
into each child and reject cycles, then resolve visibility.

See: https://www.w3.org/TR/shacl12-core/#shapes
"""

from __future__ import annotations

import dataclasses
import logging
from graphlib import CycleError, TopologicalSorter
from typing import TYPE_CHECKING, cast

from rdflib import RDF, SH, URIRef

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR, ValueType
from fastshaql.core.ir.node_expr import SparqlExprNodeExpr
from fastshaql.core.ir.property_shape import UnionMember
from fastshaql.core.kernel.constants import SYNTHETIC_SHAPE_PREFIX
from fastshaql.core.kernel.identifiers import local_name
from fastshaql.core.registry import ShapeRegistry, index_by_target_class

from .errors import UnsupportedShapeError
from .node_expr.semantics import reads_focus
from .node_shape import parse_node_shape
from .util import SH_SHAPE_CLASS, graphql_type_name, is_deactivated
from .visibility import resolve_visibility

if TYPE_CHECKING:
    from rdflib import Graph

log = logging.getLogger(__name__)


def _merge_parent_prop(
    child: NodeShapeIR,
    own_names: set[str],
    merged: dict[str, PropertyShapeIR],
    parent_iri: URIRef,
    prop: PropertyShapeIR,
) -> None:
    """Merge one inherited property shape into *merged* (ADR-0005).

    Own-beats-inherited: a field the child declares itself overrides the
    inherited one wholesale, with a warning naming the route. Two parents
    contributing different property shapes under one name (child silent)
    raises — no principled tiebreaker. The same property shape reaching the
    child via two paths (diamond) dedupes.
    """
    name = prop.graphql_field_name
    existing = merged.get(name)
    if existing is None:
        merged[name] = prop
        return
    if name in own_names:
        log.warning(
            "Field override on %s: field %r (property shape %s) "
            "replaces inherited %s from %s",
            child.graphql_type_name,
            name,
            existing.iri,
            prop.iri,
            parent_iri,
        )
    elif existing.iri != prop.iri:
        raise ValueError(
            f"Field name collision on {child.graphql_type_name}: "
            f"{name!r} from property shapes {existing.iri} and {prop.iri}"
        )
    # else: same property shape via two paths — diamond, dedupe


def _resolve_inheritance(shapes: list[NodeShapeIR]) -> list[NodeShapeIR]:
    """Flatten ``sh:node`` inheritance into each shape's ``property_shapes`` (ADR-0005).

    Field-only: parents contribute their property shapes, not node-level
    constraints. A topological order (parents before children) makes the
    transitive merge a single iterative pass — no recursion or memo — and
    ``TopologicalSorter`` detects cycles, which SHACL §6.5.3 leaves undefined
    and sanctions rejecting for static-SPARQL architectures.

    Reads parents' post-pass-2 ``property_shapes`` so inherited ``sh:class``
    fields carry ``value_shape_iri`` into ``resolve_visibility`` — pass order
    (2 → 3 → visibility) is load-bearing; reordering silently breaks visibility
    for inherited relationship fields.
    """
    by_iri = {shape.iri: shape for shape in shapes}
    parents = {shape.iri: shape.inherited_shape_iris for shape in shapes}

    try:
        order = list(TopologicalSorter(parents).static_order())
    except CycleError as exc:
        cycle = " -> ".join(str(node) for node in exc.args[1])
        raise ValueError(f"Inheritance cycle: {cycle}") from None

    effective: dict[URIRef, dict[str, PropertyShapeIR]] = {}
    for iri in order:
        if iri not in by_iri:
            continue  # predecessor IRI with no NodeShape — surfaced at the merge below
        child = by_iri[iri]
        merged: dict[str, PropertyShapeIR] = dict(child.property_shapes)
        own_names = set(child.property_shapes)
        for parent_iri in parents[iri]:
            if parent_iri not in by_iri:
                raise ValueError(
                    f"Unknown inherited shape {parent_iri} referenced from {iri}"
                )
            for prop in effective[parent_iri].values():
                _merge_parent_prop(child, own_names, merged, parent_iri, prop)
        effective[iri] = merged

    return [
        dataclasses.replace(shape, property_shapes=effective[shape.iri])
        for shape in shapes
    ]


def _make_synthetic_shape(class_iri: URIRef) -> NodeShapeIR:
    """Minimal node shape for ``sh:class`` with no matching ``sh:targetClass`` shape."""
    return NodeShapeIR(
        iri=URIRef(f"{SYNTHETIC_SHAPE_PREFIX}{local_name(class_iri)}"),
        description=None,
        graphql_type_name=graphql_type_name(code_identifier=None, iri=class_iri),
        target_class=None,
        property_shapes={},
    )


def _class_target_shape(
    class_iri: URIRef,
    by_target_class: dict[URIRef, NodeShapeIR],
    synthetics: dict[URIRef, NodeShapeIR],
) -> NodeShapeIR:
    """The shape targeting *class_iri* — the class-indexed shape, or a
    freshly minted synthetic when no shape targets the class (ADR-0025)."""
    target = by_target_class.get(class_iri)
    if target is not None:
        return target
    if class_iri not in synthetics:
        synthetics[class_iri] = _make_synthetic_shape(class_iri)
        log.warning(
            "No shape targets class %s — created synthetic %s",
            class_iri,
            synthetics[class_iri].iri,
        )
    return synthetics[class_iri]


def _resolve_relationship(
    prop: PropertyShapeIR,
    by_iri: dict[URIRef, NodeShapeIR],
    by_target_class: dict[URIRef, NodeShapeIR],
    synthetics: dict[URIRef, NodeShapeIR],
) -> PropertyShapeIR:
    """Resolve one relationship property per the targeting model
    (ADR-0025): a ``sh:node`` property keeps its target and is
    auto-typed from the target shape's ``indexed_class`` when it
    declares no classes; a class-only property resolves its target via
    ``by_target_class``, creating a synthetic shape when no shape
    targets the class. Polymorphic members (ADR-0026) resolve via
    :func:`_resolve_union_relationship`.
    """
    if prop.union_members:
        return _resolve_union_relationship(prop, by_iri, by_target_class, synthetics)
    if prop.value_shape_iri is not None:
        target = by_iri.get(prop.value_shape_iri)
        if prop.value_classes or target is None or target.indexed_class is None:
            return prop
        return dataclasses.replace(prop, value_classes=(target.indexed_class,))
    if prop.value_classes:
        return dataclasses.replace(
            prop,
            value_shape_iri=_class_target_shape(
                prop.value_classes[0], by_target_class, synthetics
            ).iri,
        )
    return prop


def _resolve_union_relationship(
    prop: PropertyShapeIR,
    by_iri: dict[URIRef, NodeShapeIR],
    by_target_class: dict[URIRef, NodeShapeIR],
    synthetics: dict[URIRef, NodeShapeIR],
) -> PropertyShapeIR:
    """Resolve polymorphic members (ADR-0026): a ``sh:class`` member takes
    the class-indexed shape (or a synthetic); an ``sh:node`` member must be
    class-indexed — the class is the member discriminator. The binding-union
    row (list form beside ``sh:node``) keeps its single target: pass 1
    already paired the declared classes with it, so members resolve as-is.
    A sole member collapses to the plain single-target binding — one
    member names one target and one binding class, rows 2/3 of the
    targeting model: no union artifact for a monomorphic field.
    """
    if prop.value_shape_iri is not None:
        members = prop.union_members
    else:
        members = tuple(
            _resolve_member(prop, member, by_iri, by_target_class, synthetics)
            for member in prop.union_members
        )
    _reject_duplicate_members(prop, members, by_iri, synthetics)
    if len(members) == 1:
        return dataclasses.replace(
            prop,
            union_members=(),
            value_shape_iri=cast(URIRef, members[0].shape_iri),
            value_classes=(cast(URIRef, members[0].class_iri),),
        )
    return dataclasses.replace(prop, union_members=members)


def _reject_focus_bound_sparql_expr(shape: NodeShapeIR, prop: PropertyShapeIR) -> None:
    """Reject a derived relationship whose ``sh:sparqlExpr`` reads the focus
    node (ADR-0026 hazard containment).

    The ``BIND`` needs the focus binding, so it cannot live in the
    projecting sub-SELECT every guarded derived emission goes through — the
    values would drop — while uncontained an erroring row fabricates values.
    Any relationship anchor qualifies, not just typed bindings: the filter
    paths contain every derived link emission. ``sh:select`` re-binds the
    focus inside its body and stays lowerable.

    Raises:
        UnsupportedShapeError: On the combination.
    """
    values_expr = prop.values_expr
    if (
        prop.value_type is ValueType.RELATIONSHIP
        and isinstance(values_expr, SparqlExprNodeExpr)
        and reads_focus(values_expr.expr)
    ):
        raise UnsupportedShapeError(
            f"derived relationship {prop.graphql_field_name!r} on {shape.iri} "
            "computes its values with sh:sparqlExpr reading $this — the BIND "
            "cannot live in the guard's containing sub-SELECT (its values "
            "would drop), and uncontained an erroring row fabricates values; "
            "derive it with sh:select (its body re-binds the focus) or "
            "shnex:pathValues instead"
        )


def _resolve_member(
    prop: PropertyShapeIR,
    member: UnionMember,
    by_iri: dict[URIRef, NodeShapeIR],
    by_target_class: dict[URIRef, NodeShapeIR],
    synthetics: dict[URIRef, NodeShapeIR],
) -> UnionMember:
    """Resolve one raw union member to its (shape, class) pair (ADR-0026).

    A class member resolves through the class index, with the synthetic
    fallback; a shape member must be class-indexed — the class is the lane
    guard and the ``__typename`` source.

    Raises:
        UnsupportedShapeError: On a shape member referencing an unknown
            shape or a target with no class discriminator (class-less or
            derived targets do not discriminate).
    """
    field_name = prop.graphql_field_name
    if member.class_iri is not None:
        target = _class_target_shape(member.class_iri, by_target_class, synthetics)
        return UnionMember(shape_iri=target.iri, class_iri=member.class_iri)
    target = by_iri.get(cast(URIRef, member.shape_iri))
    if target is None:
        raise UnsupportedShapeError(
            f"sh:or member on {prop.iri} field {field_name!r} references unknown "
            f"shape {member.shape_iri} — a sh:deactivated shape parses to "
            "nothing and is not addressable"
        )
    if target.indexed_class is None:
        raise UnsupportedShapeError(
            f"sh:or member target {member.shape_iri} on {prop.iri} field "
            f"{field_name!r} has no class discriminator — union members need "
            "a class-indexed target (sh:targetClass or an implicit class "
            "target; derived targets do not discriminate)"
        )
    return UnionMember(shape_iri=member.shape_iri, class_iri=target.indexed_class)


def _reject_duplicate_members(
    prop: PropertyShapeIR,
    members: tuple[UnionMember, ...],
    by_iri: dict[URIRef, NodeShapeIR],
    synthetics: dict[URIRef, NodeShapeIR],
) -> None:
    """Reject duplicate members (ADR-0026): two resolving to the same class
    (a value would match two lanes under one discriminator), or — polymorphic
    only — two member shapes deriving the same GraphQL type name, which would
    repeat an object type in the union (local-name collisions across
    namespaces). The binding-union row shares its one target by construction
    and passes both checks. Member shapes post-:func:`_resolve_member` live
    in *by_iri* or — minted synthetics, keyed by class — in *synthetics*."""
    field_name = prop.graphql_field_name
    check_type_names = prop.value_shape_iri is None
    seen_classes: set[URIRef] = set()
    seen_type_names: dict[str, URIRef] = {}
    for member in members:
        class_iri = cast(URIRef, member.class_iri)
        if class_iri in seen_classes:
            raise UnsupportedShapeError(
                f"duplicate union member on {prop.iri} field {field_name!r} — "
                f"two members resolve to the same class {class_iri}; "
                "declare it once"
            )
        seen_classes.add(class_iri)
        if not check_type_names:
            continue
        shape = by_iri.get(cast(URIRef, member.shape_iri)) or synthetics.get(
            cast(URIRef, member.class_iri)
        )
        if shape is None:
            raise AssertionError(  # pragma: no cover — _resolve_member indexes every member shape
                "member shape unindexed in duplicate check"
            )
        type_name = shape.graphql_type_name
        prior_class = seen_type_names.get(type_name)
        if prior_class is not None:
            raise UnsupportedShapeError(
                f"union members on {prop.iri} field {field_name!r} ({prior_class} "
                f"and {class_iri}) derive the same GraphQL type name "
                f"{type_name!r} — disambiguate the shapes with sh:codeIdentifier"
            )
        seen_type_names[type_name] = class_iri


def parse_shapes(graph: Graph, *, description_language: str = "en") -> ShapeRegistry:
    """Parse every named ``sh:NodeShape`` in *graph* and return a :class:`ShapeRegistry`.

    Pass 1 builds ``NodeShapeIR`` with raw ``value_classes`` set and
    ``value_shape_iri`` populated for ``sh:node`` properties (the ``sh:node``
    value IS the shape IRI). Pass 2 resolves relationships per the targeting
    model (ADR-0025, :func:`_resolve_relationship`). Pass 3 flattens
    node-shape inheritance (``sh:node`` on node shapes, ADR-0005) before
    visibility.

    Shapes typed ``sh:ShapeClass`` (Core §3.1.3.3) are enumerated alongside
    ``sh:NodeShape`` — a shape may carry either or both types.

    Blank-node node shapes and inline ``sh:node`` on property shapes are deferred.

    Args:
        graph: An RDFLib graph containing SHACL shape definitions.
        description_language: BCP 47 tag for selecting shape descriptions at
            parse time (ADR-0007). Defaults to ``"en"``.

    Returns:
        Registry with resolved relationship properties and lookup indexes.
    """
    shapes: list[NodeShapeIR] = []
    shape_iris: dict[object, None] = {}  # ordered set — a shape may carry both types
    for shape_class in (SH.NodeShape, SH_SHAPE_CLASS):
        for shape_iri in graph.subjects(RDF.type, shape_class):
            shape_iris.setdefault(shape_iri, None)
    for shape_iri in shape_iris:
        if not isinstance(shape_iri, URIRef):
            log.warning(
                "Skipping blank-node NodeShape (not addressable by IRI): %s",
                shape_iri,
            )
            continue
        if is_deactivated(graph, shape_iri):
            continue  # SHACL Core §3.1.6: not evaluated → no GraphQL type
        shapes.append(
            parse_node_shape(
                graph,
                shape_iri,
                description_language=description_language,
            )
        )

    by_target_class = index_by_target_class(shapes)
    by_iri = {shape.iri: shape for shape in shapes}
    synthetics: dict[URIRef, NodeShapeIR] = {}

    resolved: list[NodeShapeIR] = []
    for shape in shapes:
        props: dict[str, PropertyShapeIR] = {}
        for name, prop in shape.property_shapes.items():
            resolved_prop = _resolve_relationship(
                prop, by_iri, by_target_class, synthetics
            )
            _reject_focus_bound_sparql_expr(shape, resolved_prop)
            props[name] = resolved_prop
        resolved.append(dataclasses.replace(shape, property_shapes=props))

    resolved = _resolve_inheritance(resolved)

    all_shapes = sorted(
        [*resolved, *synthetics.values()],
        key=lambda s: s.graphql_type_name,
    )
    visibility = resolve_visibility(graph, all_shapes)
    return ShapeRegistry(all_shapes, visibility=visibility)
