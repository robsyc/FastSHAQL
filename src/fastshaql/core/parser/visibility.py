"""Resolve API-view visibility from ``graphql:Schema`` declarations (ADR-0008).

Parse-time pass-3 logic, run by :func:`~fastshaql.core.parser.parse_shapes`
after target and inheritance resolution: read the graph's zero-or-one
``graphql:Schema`` container, classify every shape ``PUBLIC`` / ``PROTECTED``
/ ``EXCLUDED`` (private > public > protected > closed world), demote public
shapes without a supported target, and enforce the closed-world relationship
check. The resulting ``VisibilityMap`` is served post-parse by
``ShapeRegistry`` — visibility is declared by a schema against shapes and
classes, never intrinsic to the shape.

See: https://datashapes.org/graphql
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rdflib import Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from fastshaql.core.kernel.constants import SYNTHETIC_SHAPE_PREFIX
from fastshaql.core.registry import Visibility, VisibilityMap

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from rdflib import Graph

    from fastshaql.core.ir import NodeShapeIR

GRAPHQL = Namespace("http://datashapes.org/graphql#")
GRAPHQL_SCHEMA = GRAPHQL.Schema
GRAPHQL_PUBLIC_SHAPE = GRAPHQL.publicShape
GRAPHQL_PROTECTED_SHAPE = GRAPHQL.protectedShape
GRAPHQL_PRIVATE_SHAPE = GRAPHQL.privateShape
GRAPHQL_PUBLIC_CLASS = GRAPHQL.publicClass
GRAPHQL_PROTECTED_CLASS = GRAPHQL.protectedClass
GRAPHQL_PUBLIC_NAMESPACE = GRAPHQL.publicNamespace

log = logging.getLogger(__name__)


class VisibilityError(Exception):
    """Visibility resolution failed (schema conflict or closed-world violation)."""


@dataclass(frozen=True)
class _SchemaDeclarations:
    """``graphql:Schema`` visibility declarations read from an RDF graph."""

    public_shapes: frozenset[URIRef]
    """Shape IRIs declared ``graphql:publicShape``."""
    protected_shapes: frozenset[URIRef]
    """Shape IRIs declared ``graphql:protectedShape``."""
    private_shapes: frozenset[URIRef]
    """Shape IRIs declared ``graphql:privateShape``."""
    public_classes: frozenset[URIRef]
    """Target classes declared ``graphql:publicClass`` (subclass-expanded)."""
    protected_classes: frozenset[URIRef]
    """Target classes declared ``graphql:protectedClass`` (subclass-expanded)."""


def _expand_subclasses(graph: Graph, classes: set[URIRef]) -> set[URIRef]:
    """Return each class plus all transitive ``rdfs:subClassOf`` descendants.

    ``Graph.transitive_subjects`` yields the start object itself, so the
    declared class lands in the closure without a separate ``add``.
    """
    expanded: set[URIRef] = set()
    for class_iri in classes:
        expanded.update(
            subject
            for subject in graph.transitive_subjects(RDFS.subClassOf, class_iri)
            if isinstance(subject, URIRef)
        )
    return expanded


def _uri_refs(values: Iterable[object]) -> frozenset[URIRef]:
    """Filter *values* to ``URIRef`` instances as a frozenset."""
    return frozenset(v for v in values if isinstance(v, URIRef))


def _expanded_classes(graph: Graph, values: Iterable[object]) -> frozenset[URIRef]:
    """URIRefs from *values* with their ``rdfs:subClassOf`` closures expanded."""
    return frozenset(_expand_subclasses(graph, set(_uri_refs(values))))


def _read_declarations(graph: Graph, schema: URIRef) -> _SchemaDeclarations:
    """Read all ``graphql:Schema`` visibility declarations (expanding class closures)."""
    return _SchemaDeclarations(
        public_shapes=_uri_refs(graph.objects(schema, GRAPHQL_PUBLIC_SHAPE)),
        protected_shapes=_uri_refs(graph.objects(schema, GRAPHQL_PROTECTED_SHAPE)),
        private_shapes=_uri_refs(graph.objects(schema, GRAPHQL_PRIVATE_SHAPE)),
        public_classes=_expanded_classes(
            graph, graph.objects(schema, GRAPHQL_PUBLIC_CLASS)
        ),
        protected_classes=_expanded_classes(
            graph, graph.objects(schema, GRAPHQL_PROTECTED_CLASS)
        ),
    )


def _is_synthetic(iri: URIRef) -> bool:
    """``True`` for parser-generated ``urn:fastshaql:synthetic:*`` shape IRIs."""
    return str(iri).startswith(SYNTHETIC_SHAPE_PREFIX)


def _classify_shapes(
    shapes: Sequence[NodeShapeIR],
    declarations: _SchemaDeclarations,
) -> dict[URIRef, Visibility]:
    """Assign each shape a ``Visibility`` per the declaration table (private > public > protected > closed-world)."""
    result: dict[URIRef, Visibility] = {}
    for shape in shapes:
        if shape.iri in declarations.private_shapes:
            result[shape.iri] = Visibility.EXCLUDED
        elif shape.iri in declarations.public_shapes or (
            shape.indexed_class is not None
            and shape.indexed_class in declarations.public_classes
        ):
            result[shape.iri] = Visibility.PUBLIC
        elif (
            shape.iri in declarations.protected_shapes
            or (
                shape.indexed_class is not None
                and shape.indexed_class in declarations.protected_classes
            )
            or _is_synthetic(shape.iri)
        ):
            result[shape.iri] = Visibility.PROTECTED
        else:
            result[shape.iri] = Visibility.EXCLUDED
    return result


def _demote_untargeted_public_shapes(
    shapes: Sequence[NodeShapeIR],
    result: dict[URIRef, Visibility],
) -> None:
    """Downgrade ``PUBLIC`` shapes without any supported target to ``PROTECTED``
    (with a warning). Classes are one target-derivation path among others — a
    ``sh:targetNode`` shape publishes unchanged (ADR-0008)."""
    for shape in shapes:
        if result[shape.iri] is Visibility.PUBLIC and not shape.has_target:
            log.warning(
                "publicShape %s has no supported target "
                "(sh:targetClass, sh:targetNode, or implicit class target); "
                "treated as protected",
                shape.iri,
            )
            result[shape.iri] = Visibility.PROTECTED


def _enforce_closed_world(
    shapes: Sequence[NodeShapeIR],
    result: dict[URIRef, Visibility],
) -> None:
    """Raise when a non-excluded shape's relationship targets an excluded named shape."""
    for shape in shapes:
        if result[shape.iri] is Visibility.EXCLUDED:
            continue
        for prop in shape.property_shapes.values():
            target = prop.value_shape_iri
            if target is None or _is_synthetic(target):
                continue
            if result.get(target) is Visibility.EXCLUDED:
                raise VisibilityError(
                    f"relationship {shape.graphql_type_name}.{prop.graphql_field_name} "
                    f"targets shape {target}, which the schema does not publish; "
                    f"add graphql:publicShape or graphql:protectedShape for it"
                )


def resolve_visibility(graph: Graph, shapes: Sequence[NodeShapeIR]) -> VisibilityMap:
    """Resolve visibility for every shape in *shapes* from *graph* declarations.

    Args:
        graph: RDF graph containing ``graphql:Schema`` declarations (if any).
        shapes: Parsed node shapes to classify.

    Returns:
        A total map from each shape's resource IRI to its :class:`Visibility`.

    Raises:
        VisibilityError: On multiple schemas or closed-world relationship violations.
    """
    schemas = list(graph.subjects(RDF.type, GRAPHQL_SCHEMA))
    if not schemas:
        return VisibilityMap.all_public([shape.iri for shape in shapes])
    if len(schemas) > 1:
        raise VisibilityError("multiple graphql:Schema resources; single-schema only")

    schema = schemas[0]
    if not isinstance(schema, URIRef):
        raise VisibilityError("graphql:Schema resource must be an IRI")

    declarations = _read_declarations(graph, schema)

    if any(graph.objects(schema, GRAPHQL_PUBLIC_NAMESPACE)):
        log.warning("graphql:publicNamespace not supported; ignored")

    result = _classify_shapes(shapes, declarations)
    _demote_untargeted_public_shapes(shapes, result)
    _enforce_closed_world(shapes, result)
    return VisibilityMap(result)
