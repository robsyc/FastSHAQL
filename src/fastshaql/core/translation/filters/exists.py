"""FILTER EXISTS construction for relationship filters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import Variable

from fastshaql.core.sparql import (
    ExistsExpr,
    Expression,
    FilterPattern,
    GroupPattern,
    Pattern,
)

from ..joins import relationship_join_patterns, relationship_type_patterns
from .fields import translate_fields
from .naming import exists_join_var_name

if TYPE_CHECKING:
    from graphql.language.ast import ObjectValueNode

    from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR
    from fastshaql.core.registry import ShapeRegistry

    from .context import ExistsContext


def build_exists_expr(
    node: ObjectValueNode,
    shape: NodeShapeIR,
    relationship_prop: PropertyShapeIR,
    registry: ShapeRegistry,
    scope: ExistsContext,
) -> ExistsExpr:
    """Build an ``EXISTS { ... }`` expression for a relationship filter."""
    inner = exists_inner_patterns(node, shape, relationship_prop, registry, scope)
    return ExistsExpr(GroupPattern(tuple(inner)))


def exists_inner_patterns(
    node: ObjectValueNode,
    shape: NodeShapeIR,
    relationship_prop: PropertyShapeIR,
    registry: ShapeRegistry,
    scope: ExistsContext,
) -> list[Pattern]:
    """Build pattern list inside an ``EXISTS { ... }`` block."""
    child_patterns, child_expr = translate_fields(node, shape, scope, registry)

    patterns: list[Pattern] = []
    patterns.extend(relationship_type_patterns(scope.subject, relationship_prop))
    patterns.extend(child_patterns)
    if child_expr is not None:
        patterns.append(FilterPattern(child_expr))
    return patterns


def translate_exists_relationship(
    ctx: ExistsContext,
    field_name: str,
    node: ObjectValueNode,
    prop: PropertyShapeIR,
    child_shape: NodeShapeIR,
    registry: ShapeRegistry,
) -> tuple[list[Pattern], Expression | None]:
    """Translate a nested relationship filter inside an EXISTS block."""
    child_subject = Variable(exists_join_var_name(ctx.rf_prefix, field_name))
    join_patterns = relationship_join_patterns(
        ctx.subject, child_subject, prop, emit_type_triple=False
    )
    child_scope = ctx.child_scope(child_subject, field_name)
    exists_expr = build_exists_expr(node, child_shape, prop, registry, child_scope)
    return join_patterns, exists_expr
