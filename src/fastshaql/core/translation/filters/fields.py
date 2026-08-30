"""Walk GraphQL ``where`` object fields into SPARQL patterns and expressions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.language.ast import NullValueNode, ObjectFieldNode, ObjectValueNode

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR, ValueType
from fastshaql.core.sparql import (
    ExistsExpr,
    Expression,
    FilterPattern,
    GroupPattern,
    NotExpr,
    Pattern,
)

from .operators import (
    combine_and,
    combine_or,
    translate_iri_filter,
    translate_scalar_ops,
)
from .walk import iter_combinator_objects, walk_where

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastshaql.core.registry import ShapeRegistry

    from .strategy import FilterContext


def _branch_to_expression(
    patterns: list[Pattern],
    expr: Expression | None,
) -> Expression | None:
    """Turn one filter branch into a composable expression for AND/OR/NOT.

    Branches with neither patterns nor an expression are no-ops (e.g. empty
    relationship filters ``{ employer: {} }`` — join binding is handled by
    promotion at the root filter level, ADR-0009).
    """
    if expr is None:
        return None
    if not patterns:
        return expr
    children: list[Pattern] = [*patterns, FilterPattern(expr)]
    return ExistsExpr(GroupPattern(tuple(children)))


class _FieldTranslator:
    """Accumulates patterns and expressions while walking a ``where`` object."""

    __slots__ = ("ctx", "exprs", "patterns", "registry", "shape")

    def __init__(
        self,
        shape: NodeShapeIR,
        ctx: FilterContext,
        registry: ShapeRegistry,
    ) -> None:
        self.shape = shape
        self.ctx = ctx
        self.registry = registry
        self.patterns: list[Pattern] = []
        self.exprs: list[Expression] = []

    def on_combinator(
        self, name: str, field: ObjectFieldNode, shape: NodeShapeIR
    ) -> None:
        pats, expr = _COMBINATOR_HANDLERS[name](field, shape, self.ctx, self.registry)
        self.patterns.extend(pats)
        if expr is not None:
            self.exprs.append(expr)

    def on_iri(self, field: ObjectFieldNode) -> None:
        expr = translate_iri_filter(field.value, self.ctx.subject)
        if expr is not None:
            self.exprs.append(expr)

    def on_property(
        self, name: str, prop: PropertyShapeIR, field: ObjectFieldNode
    ) -> None:
        match prop.value_type:
            case ValueType.RELATIONSHIP:
                if isinstance(field.value, NullValueNode):
                    return
                if not isinstance(field.value, ObjectValueNode):
                    raise TypeError(
                        f"Relationship filter {name!r} requires an object value"
                    )  # pragma: no cover — validated upstream by graphql-core
                pats, expr = self.ctx.translate_relationship(
                    name, field.value, prop, self.registry
                )
            # ``case`` fall-through below the last arm is unreachable: the
            # ValueType union is closed (no wildcard arm).
            case ValueType.ENUM | ValueType.SCALAR:  # pragma: no branch — closed union
                var, scalar_patterns = self.ctx.scalar_var(name, prop)
                pats = scalar_patterns
                expr = translate_scalar_ops(field.value, prop, var)
        self.patterns.extend(pats)
        if expr is not None:
            self.exprs.append(expr)


def translate_fields(
    node: ObjectValueNode,
    shape: NodeShapeIR,
    ctx: FilterContext,
    registry: ShapeRegistry,
) -> tuple[list[Pattern], Expression | None]:
    """Walk *node*'s fields, returning ``(patterns, expression)``."""
    translator = _FieldTranslator(shape, ctx, registry)
    walk_where(node, shape, translator)
    return translator.patterns, combine_and(translator.exprs)


def _translate_branch_objects(
    items: list[ObjectValueNode],
    shape: NodeShapeIR,
    ctx: FilterContext,
    registry: ShapeRegistry,
    combine: Callable[[list[Expression]], Expression | None],
) -> tuple[list[Pattern], Expression | None]:
    exprs: list[Expression] = []
    for item in items:
        pats, expr = translate_fields(item, shape, ctx, registry)
        branch_expr = _branch_to_expression(pats, expr)
        if branch_expr is not None:
            exprs.append(branch_expr)
    return [], combine(exprs)


def _translate_not_combinator(
    field: ObjectFieldNode,
    shape: NodeShapeIR,
    ctx: FilterContext,
    registry: ShapeRegistry,
) -> tuple[list[Pattern], Expression | None]:
    items = iter_combinator_objects(field)
    if not items:
        return [], None
    pats, expr = translate_fields(items[0], shape, ctx, registry)
    branch_expr = _branch_to_expression(pats, expr)
    if branch_expr is None:
        return [], None
    return [], NotExpr(branch_expr)


_COMBINATOR_HANDLERS: dict[
    str,
    Callable[
        [ObjectFieldNode, NodeShapeIR, FilterContext, ShapeRegistry],
        tuple[list[Pattern], Expression | None],
    ],
] = {
    "AND": lambda f, s, c, r: _translate_branch_objects(
        iter_combinator_objects(f), s, c, r, combine_and
    ),
    "OR": lambda f, s, c, r: _translate_branch_objects(
        iter_combinator_objects(f), s, c, r, combine_or
    ),
    "NOT": _translate_not_combinator,
}
