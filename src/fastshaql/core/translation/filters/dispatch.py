"""Top-level ``where`` argument translation into SPARQL graph patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastshaql.core.sparql import FilterPattern, Pattern

from .fields import translate_fields

if TYPE_CHECKING:
    from graphql.language.ast import ObjectValueNode

    from fastshaql.core.ir import NodeShapeIR
    from fastshaql.core.registry import ShapeRegistry

    from .strategy import FilterContext


def translate_where_filter(
    where: ObjectValueNode | None,
    ctx: FilterContext,
    shape: NodeShapeIR,
    registry: ShapeRegistry,
) -> list[Pattern]:
    """Translate a ``where`` object into graph patterns."""
    if where is None or not where.fields:
        return []
    patterns, expr = translate_fields(where, shape, ctx, registry)
    if expr is not None:
        patterns = [*patterns, FilterPattern(expr)]
    return patterns
