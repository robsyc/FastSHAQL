"""SHACL shapes graph → ShapeRegistry.

Three-pass parse:
(1) walk the graph into ``NodeShapeIR`` / ``PropertyShapeIR`` dataclasses,
(2) resolve ``sh:class`` cross-references via target-class lookup,
set ``value_shape_iri`` on relationship properties,
and create synthetic shapes for untargeted classes,
(3) flatten ``sh:node`` inheritance (ADR-0005) — merge parent property shapes
into each child and reject cycles, then resolve visibility.

See: https://www.w3.org/TR/shacl12-core/#shapes
"""

from __future__ import annotations

import dataclasses
import logging
from graphlib import CycleError, TopologicalSorter
from typing import TYPE_CHECKING

from rdflib import RDF, SH, URIRef

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR
from fastshaql.core.kernel.constants import SYNTHETIC_SHAPE_PREFIX
from fastshaql.core.kernel.identifiers import local_name
from fastshaql.core.registry import (
    ShapeRegistry,
    index_by_target_class,
    resolve_visibility,
)

from .node_shape import parse_node_shape
from .util import SH_SHAPE_CLASS, graphql_type_name, is_deactivated

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


def _resolve_shape_iri(
    prop: PropertyShapeIR,
    by_target_class: dict[URIRef, NodeShapeIR],
    synthetics: dict[URIRef, NodeShapeIR],
) -> URIRef | None:
    """Resolve the target shape IRI for a relationship property.

    For ``sh:class``: look up the target shape via ``by_target_class``,
    creating a synthetic shape if no match is found. Properties without
    ``sh:class`` (including ``sh:node``) return ``None``, leaving their
    pass-1 ``value_shape_iri`` untouched.
    """
    if prop.value_class is not None:
        target = by_target_class.get(prop.value_class)
        if target is not None:
            return target.iri
        if prop.value_class not in synthetics:
            synthetics[prop.value_class] = _make_synthetic_shape(prop.value_class)
            log.warning(
                "No shape targets class %s — created synthetic %s",
                prop.value_class,
                synthetics[prop.value_class].iri,
            )
        return synthetics[prop.value_class].iri
    return None


def parse_shapes(graph: Graph, *, description_language: str = "en") -> ShapeRegistry:
    """Parse every named ``sh:NodeShape`` in *graph* and return a :class:`ShapeRegistry`.

    Pass 1 builds ``NodeShapeIR`` with raw ``value_class`` set and
    ``value_shape_iri`` populated for ``sh:node`` properties (the ``sh:node``
    value IS the shape IRI). Pass 2 resolves ``sh:class`` properties by mapping
    ``value_class`` to the target shape IRI via ``by_target_class``, creating
    synthetic shapes for untargeted classes. Pass 3 flattens node-shape
    inheritance (``sh:node`` on node shapes, ADR-0005) before visibility.

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
    synthetics: dict[URIRef, NodeShapeIR] = {}

    resolved: list[NodeShapeIR] = []
    for shape in shapes:
        props: dict[str, PropertyShapeIR] = {}
        for name, prop in shape.property_shapes.items():
            target_iri = _resolve_shape_iri(prop, by_target_class, synthetics)
            if target_iri is not None:
                props[name] = dataclasses.replace(prop, value_shape_iri=target_iri)
            else:
                props[name] = prop
        resolved.append(dataclasses.replace(shape, property_shapes=props))

    resolved = _resolve_inheritance(resolved)

    all_shapes = sorted(
        [*resolved, *synthetics.values()],
        key=lambda s: s.graphql_type_name,
    )
    visibility = resolve_visibility(graph, all_shapes)
    return ShapeRegistry(all_shapes, visibility=visibility)
