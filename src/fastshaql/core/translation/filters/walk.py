"""Shared walk over GraphQL ``where`` object ASTs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from graphql.language.ast import ListValueNode, ObjectFieldNode, ObjectValueNode

if TYPE_CHECKING:
    from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR

COMBINATOR_NAMES = frozenset({"AND", "OR", "NOT"})


def resolve_where_property(name: str, shape: NodeShapeIR) -> PropertyShapeIR:
    """Return the Property for a filter field name."""
    prop = shape.property_shapes.get(name)
    if prop is None:
        raise ValueError(
            f"Unknown filter field {name!r} on shape {shape.graphql_type_name!r}"
        )
    return prop


def iter_combinator_objects(field: ObjectFieldNode) -> list[ObjectValueNode]:
    """Return nested filter objects for a combinator field."""
    if field.name.value == "NOT":
        if isinstance(field.value, ObjectValueNode):
            return [field.value]
        return []
    if isinstance(field.value, ListValueNode):
        return [
            item for item in field.value.values if isinstance(item, ObjectValueNode)
        ]
    return []


class WhereVisitor(Protocol):
    """Visitor protocol for :func:`walk_where`."""

    def on_combinator(
        self, name: str, field: ObjectFieldNode, shape: NodeShapeIR
    ) -> None: ...  # pragma: no cover — Protocol stub

    def on_iri(
        self, field: ObjectFieldNode
    ) -> None: ...  # pragma: no cover — Protocol stub

    def on_property(
        self, name: str, prop: PropertyShapeIR, field: ObjectFieldNode
    ) -> None: ...  # pragma: no cover — Protocol stub


def walk_where(
    node: ObjectValueNode,
    shape: NodeShapeIR,
    visitor: WhereVisitor,
) -> None:
    """Walk *node*'s fields, dispatching to *visitor*."""
    for field in node.fields:
        name = field.name.value
        if name in COMBINATOR_NAMES:
            visitor.on_combinator(name, field, shape)
        elif name == "iri":
            visitor.on_iri(field)
        else:
            visitor.on_property(
                name,
                resolve_where_property(name, shape),
                field,
            )


class PromotionCollector:
    """Collect direct property names referenced at the root filter level."""

    __slots__ = ("promoted",)

    def __init__(self) -> None:
        self.promoted: set[str] = set()

    def on_combinator(
        self, name: str, field: ObjectFieldNode, shape: NodeShapeIR
    ) -> None:
        del name
        for item in iter_combinator_objects(field):
            walk_where(item, shape, self)

    def on_iri(self, field: ObjectFieldNode) -> None:
        del field

    def on_property(
        self, name: str, prop: PropertyShapeIR, field: ObjectFieldNode
    ) -> None:
        del prop, field
        self.promoted.add(name)
