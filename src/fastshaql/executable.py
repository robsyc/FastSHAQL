"""Executable schema assembly — wires schema building to the execution layer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from graphql.language.ast import FieldNode

from fastshaql.core.execution.query import execute_query
from fastshaql.core.execution.store import ResolverContext
from fastshaql.core.schema.build import build_schema

if TYPE_CHECKING:
    from graphql import GraphQLSchema
    from graphql.type.definition import GraphQLResolveInfo

    from fastshaql.core.ir.node_shape import NodeShapeIR
    from fastshaql.core.registry import ShapeRegistry

ResolverDispatch = Callable[[FieldNode, ResolverContext], Awaitable[Any]]


def build_executable_schema(registry: ShapeRegistry) -> GraphQLSchema:
    """Build a GraphQL schema with root resolvers that execute SPARQL queries.

    Wires :func:`build_schema` with resolvers that delegate each root field to
    the execution layer against a :class:`ResolverContext` store. Use this for
    serving; use ``build_schema`` directly for introspection-only schemas.

    Args:
        registry: Parsed shapes indexed for schema building and translation.

    Returns:
        Executable graphql-core schema ready for ``graphql()``.
    """

    def query_factory(
        shape: NodeShapeIR, registry: ShapeRegistry
    ) -> Callable[..., Any]:
        return _make_resolver(lambda fn, ctx: execute_query(shape, fn, registry, ctx))

    return build_schema(registry, resolver_factory=query_factory)


def _resolver_context(info: GraphQLResolveInfo) -> ResolverContext:
    """Extract and type-check :class:`ResolverContext` from graphql-core info."""
    context = info.context
    if not isinstance(context, ResolverContext):
        raise TypeError("ResolverContext with a store is required as context_value")
    return context


def _make_resolver(dispatch: ResolverDispatch) -> Callable[..., Any]:
    """Build a graphql-core resolver that delegates to *dispatch*."""

    async def resolve(
        _obj: object,
        info: GraphQLResolveInfo,
        **_kwargs: object,
    ) -> Any:
        return await dispatch(info.field_nodes[0], _resolver_context(info))

    return resolve
