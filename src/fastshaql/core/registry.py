"""Shape registry — the frozen lookup returned by ``parse_shapes``.

``ShapeRegistry`` is a pure post-parse lookup: it indexes shapes by GraphQL
type name, shape resource IRI, and target class, and serves the visibility
data (``Visibility`` / ``VisibilityMap``) resolved at parse time by
:mod:`~fastshaql.core.parser.visibility` from ``graphql:Schema``
declarations (ADR-0008, https://datashapes.org/graphql).

See: https://www.w3.org/TR/shacl12-core/#shapes
"""

from __future__ import annotations

import dataclasses
import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rdflib import URIRef


# ---------------------------------------------------------------------------
# Visibility (ADR-0008)
# ---------------------------------------------------------------------------


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

    def resolve_relationship_target(self, prop: PropertyShapeIR) -> NodeShapeIR:
        """Dereference a relationship property's target node shape.

        Args:
            prop: Relationship property shape with ``value_shape_iri`` set.

        Raises:
            ValueError: When ``value_shape_iri`` is missing or unknown.
        """
        label = prop.graphql_field_name
        if prop.value_shape_iri is None:
            raise ValueError(f"Relationship {label!r} has no resolved value_shape_iri")
        try:
            return self.by_iri[prop.value_shape_iri]
        except KeyError as exc:
            raise ValueError(
                f"Relationship {label!r} references unknown shape"
                f" {prop.value_shape_iri}"
            ) from exc
