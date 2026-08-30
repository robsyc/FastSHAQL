"""Shape registry and visibility resolution — shared lookup for schema
builder and translation.

The registry is constructed by :func:`~fastshaql.core.parser.parse_shapes`,
which also performs cross-reference resolution before returning it. Visibility
(``Visibility`` / ``VisibilityMap``) is parse-time resolution from
``graphql:Schema`` declarations (ADR-0008, https://datashapes.org/graphql).

See: https://www.w3.org/TR/shacl12-core/#shapes
"""

from __future__ import annotations

import dataclasses
import enum
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR
from fastshaql.core.kernel.constants import SYNTHETIC_SHAPE_PREFIX

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

GRAPHQL = Namespace("http://datashapes.org/graphql#")
GRAPHQL_SCHEMA = GRAPHQL.Schema
GRAPHQL_PUBLIC_SHAPE = GRAPHQL.publicShape
GRAPHQL_PROTECTED_SHAPE = GRAPHQL.protectedShape
GRAPHQL_PRIVATE_SHAPE = GRAPHQL.privateShape
GRAPHQL_PUBLIC_CLASS = GRAPHQL.publicClass
GRAPHQL_PROTECTED_CLASS = GRAPHQL.protectedClass
GRAPHQL_PUBLIC_NAMESPACE = GRAPHQL.publicNamespace

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Visibility (ADR-0008)
# ---------------------------------------------------------------------------


class VisibilityError(Exception):
    """Visibility resolution failed (schema conflict or closed-world violation)."""


class Visibility(enum.Enum):
    """Shape exposure for a single ``graphql:Schema`` API view."""

    PUBLIC = enum.auto()
    PROTECTED = enum.auto()
    EXCLUDED = enum.auto()


@dataclass(frozen=True)
class VisibilityMap:
    """Total map from shape resource IRI to :class:`Visibility`."""

    _by_iri: Mapping[URIRef, Visibility]
    """Shape resource IRI → resolved visibility."""

    @classmethod
    def all_public(cls, shape_iris: Sequence[URIRef]) -> VisibilityMap:
        """Build a map where every shape is ``PUBLIC`` (no-schema backward compat)."""
        return cls(dict.fromkeys(shape_iris, Visibility.PUBLIC))

    def of(self, shape: NodeShapeIR | URIRef) -> Visibility:
        """Return visibility for *shape* or its resource IRI.

        Raises:
            KeyError: When *shape* is not in this map (caller bug).
        """
        iri = shape.iri if isinstance(shape, NodeShapeIR) else shape
        try:
            return self._by_iri[iri]
        except KeyError as exc:
            raise KeyError(f"Shape {iri} not in visibility map") from exc


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
    """Return each class plus all transitive ``rdfs:subClassOf`` descendants."""
    expanded: set[URIRef] = set()
    for class_iri in classes:
        expanded.add(class_iri)
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


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def index_by_target_class(
    shapes: Sequence[NodeShapeIR],
) -> dict[URIRef, NodeShapeIR]:
    """Build the class → shape index, rejecting duplicate class targets.

    Keys come from :attr:`NodeShapeIR.indexed_class` — the ``sh:targetClass``
    value, or the shape's own IRI for implicit class targets (Core §3.1.3.3),
    where the shape *is* the class."""
    by_target_class: dict[URIRef, NodeShapeIR] = {}
    for shape in shapes:
        if shape.indexed_class is None:
            continue
        if shape.indexed_class in by_target_class:
            existing = by_target_class[shape.indexed_class]
            raise ValueError(
                f"Duplicate class target {shape.indexed_class}: "
                f"{existing.graphql_type_name!r} and "
                f"{shape.graphql_type_name!r}"
            )
        by_target_class[shape.indexed_class] = shape
    return by_target_class


@dataclasses.dataclass(frozen=True)
class ShapeRegistry:
    """Frozen lookup produced by :func:`~fastshaql.core.parser.parse_shapes`.

    Indexes shapes by GraphQL type name, target class, and shape resource IRI.
    Shared by the schema builder and translation.
    """

    shapes: tuple[NodeShapeIR, ...] = dataclasses.field(init=False)
    """Parsed node shapes."""

    _visibility: VisibilityMap = dataclasses.field(init=False)
    """Resolved visibility (internal — use ``visibility_of`` / ``visible_shapes`` / ``public_root_shapes``)."""

    by_type_name: dict[str, NodeShapeIR] = dataclasses.field(init=False)
    """``graphql_type_name`` → :class:`NodeShapeIR`."""

    by_target_class: dict[URIRef, NodeShapeIR] = dataclasses.field(init=False)
    """Indexed class → :class:`NodeShapeIR` (``indexed_class`` keys: the
    ``sh:targetClass`` value, or the shape's own IRI for implicit class
    targets — derived-target shapes are not class-indexed, ADR-0016)."""

    by_iri: dict[URIRef, NodeShapeIR] = dataclasses.field(init=False)
    """Shape resource IRI → :class:`NodeShapeIR`."""

    def __init__(
        self,
        shapes: Sequence[NodeShapeIR],
        visibility: VisibilityMap | None = None,
    ) -> None:
        shape_tuple = tuple(shapes)
        object.__setattr__(
            self,
            "_visibility",
            visibility
            if visibility is not None
            else VisibilityMap.all_public([s.iri for s in shape_tuple]),
        )
        object.__setattr__(self, "shapes", shape_tuple)
        object.__setattr__(
            self,
            "by_type_name",
            {s.graphql_type_name: s for s in shape_tuple},
        )
        object.__setattr__(
            self,
            "by_target_class",
            index_by_target_class(shape_tuple),
        )
        object.__setattr__(
            self,
            "by_iri",
            {s.iri: s for s in shape_tuple},
        )

    def visible_shapes(self) -> tuple[NodeShapeIR, ...]:
        """Shapes with ``PUBLIC`` or ``PROTECTED`` visibility (non-``EXCLUDED``)."""
        return tuple(
            shape
            for shape in self.shapes
            if self._visibility.of(shape) is not Visibility.EXCLUDED
        )

    def public_root_shapes(self) -> tuple[NodeShapeIR, ...]:
        """``PUBLIC`` shapes with a supported target — root query field candidates.

        A target is ``sh:targetClass`` or a ``sh:targetNode`` expression
        (ADR-0016): derived-target shapes publish via their shape IRI like
        class-targeted ones."""
        return tuple(
            shape
            for shape in self.shapes
            if self._visibility.of(shape) is Visibility.PUBLIC and shape.has_target
        )

    def visibility_of(self, shape: NodeShapeIR | URIRef) -> Visibility:
        """Visibility of *shape* or its resource IRI (PUBLIC, PROTECTED, EXCLUDED)."""
        return self._visibility.of(shape)

    def resolve_relationship_target(
        self,
        prop: PropertyShapeIR,
        *,
        field_name: str | None = None,
    ) -> NodeShapeIR:
        """Dereference a relationship property's target node shape.

        Args:
            prop: Relationship property shape with ``value_shape_iri`` set.
            field_name: GraphQL field name for error messages; defaults to
                ``prop.graphql_field_name``.

        Raises:
            ValueError: When ``value_shape_iri`` is missing or unknown.
        """
        label = field_name if field_name is not None else prop.graphql_field_name
        if prop.value_shape_iri is None:
            raise ValueError(f"Relationship {label!r} has no resolved value_shape_iri")
        try:
            return self.by_iri[prop.value_shape_iri]
        except KeyError as exc:
            raise ValueError(
                f"Relationship {label!r} references unknown shape"
                f" {prop.value_shape_iri}"
            ) from exc
