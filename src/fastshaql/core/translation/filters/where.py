"""Where-object pipeline: shared walk, argument extraction, field dispatch.

One module for the ``where`` argument's route into SPARQL (ADR-0009): the
shared :func:`walk_where` walk (feeding both the promotion pre-scan and
filter translation), argument extraction, the combinator/property field
translator, and the top-level :func:`translate_where_filter` dispatch entry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from graphql.language.ast import (
    FieldNode,
    IntValueNode,
    ListValueNode,
    NullValueNode,
    ObjectFieldNode,
    ObjectValueNode,
)

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

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastshaql.core.registry import ShapeRegistry

    from .exists_scope import FilterContext

# --- Shared walk over ``where`` object ASTs ---


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


# --- Where-argument extraction and the promotion pre-scan ---


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


# --- ``where`` object field walking into patterns and expressions ---


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


# --- Top-level ``where`` argument dispatch ---


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
