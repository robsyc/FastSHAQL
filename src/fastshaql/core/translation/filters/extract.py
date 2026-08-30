"""Where-argument extraction and filter promotion pre-scan (ADR-0009)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.language.ast import (
    FieldNode,
    IntValueNode,
    NullValueNode,
    ObjectValueNode,
)

from .walk import PromotionCollector, walk_where

if TYPE_CHECKING:
    from fastshaql.core.ir import NodeShapeIR


def _extract_int_argument(field_node: FieldNode, name: str) -> int | None:
    """Return a named ``Int`` field argument value, or ``None`` if absent."""
    if not field_node.arguments:
        return None
    for arg in field_node.arguments:
        if arg.name.value != name:
            continue
        if isinstance(arg.value, NullValueNode):
            return None
        if not isinstance(arg.value, IntValueNode):
            raise TypeError(
                f"{name!r} argument must be an integer"
            )  # pragma: no cover — graphql-core types limit/offset as Int; NullValueNode handled above
        return int(arg.value.value)
    return None


def extract_pagination_arguments(
    field_node: FieldNode,
) -> tuple[int | None, int | None]:
    """Return ``(limit, offset)`` from root field arguments."""
    return (
        _extract_int_argument(field_node, "limit"),
        _extract_int_argument(field_node, "offset"),
    )


def extract_where_argument(field_node: FieldNode) -> ObjectValueNode | None:
    """Return the ``where`` argument value, or ``None`` if absent."""
    if not field_node.arguments:
        return None
    for arg in field_node.arguments:
        if arg.name.value == "where":
            if isinstance(arg.value, NullValueNode):
                return None
            if not isinstance(arg.value, ObjectValueNode):
                raise ValueError(
                    "where argument must be an object value"
                )  # pragma: no cover — graphql-core types where as input object; NullValueNode handled above
            return arg.value
    return None


def compute_promoted_fields(
    where: ObjectValueNode | None,
    shape: NodeShapeIR,
) -> frozenset[str]:
    """Pre-scan *where* for optional fields that must be bound triples.

    Only direct property names at the root filter level are promoted.
    Nested relationship filter fields are handled inside ``FILTER EXISTS``.
    """
    if where is None:
        return frozenset()
    collector = PromotionCollector()
    walk_where(where, shape, collector)
    return frozenset(collector.promoted)
