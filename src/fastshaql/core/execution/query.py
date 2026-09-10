"""Translate, execute, and convert a single root query field.

Combines the translate → SPARQL render → store → convert pipeline into
a single call, usable directly or from a graphql-core resolver closure.

See: ADR-0013, ADR-0002, ADR-0014
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastshaql.core.translation import translate_query

from .converter import convert_rows
from .store import ResolverContext, timed

if TYPE_CHECKING:
    from graphql.language.ast import FieldNode

    from fastshaql.core.ir.node_shape import NodeShapeIR
    from fastshaql.core.registry import ShapeRegistry


async def execute_query(
    shape: NodeShapeIR,
    field_node: FieldNode,
    registry: ShapeRegistry,
    context: ResolverContext,
) -> list[dict[str, object]]:
    """Translate, execute, and convert a single root query field.

    Args:
        shape: The Shape for this query field's GraphQL type.
        field_node: The root ``FieldNode`` including its ``selection_set``.
        registry: Shape lookup for nested relationship traversal.
        context: Per-request context wrapping the SPARQL store.

    Returns:
        One dict per entity with coerced scalar, list, and nested values.
    """
    metrics = context.metrics

    with timed(metrics, "execute_ms"):
        with timed(metrics, "translate_ms"):
            result = translate_query(
                shape,
                field_node,
                registry,
                query_context=context.query_context,
            )
            # Render counts as translation: AST → SPARQL string.
            sparql = result.query.render()
        with timed(metrics, "store_ms"):
            # Metrics arg passed only on profiling runs: stores with a one-arg
            # ``query`` signature keep working in production.
            if metrics is None:
                rows = await context.store.query(sparql)
            else:
                rows = await context.store.query(sparql, metrics=metrics)
        with timed(metrics, "convert_ms"):
            return convert_rows(rows, shape, result.var_map, registry)
