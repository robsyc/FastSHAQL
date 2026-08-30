"""Assemble a graphql-core ``GraphQLSchema`` from a shape registry.

See:
- https://spec.graphql.org/October2021/#sec-Schema
- https://spec.graphql.org/October2021/#sec-Root-Operation-Types
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from graphql import GraphQLSchema
from graphql.type import (
    GraphQLArgument,
    GraphQLField,
    GraphQLInputObjectType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
)

from fastshaql.core.ir.node_shape import NodeShapeIR
from fastshaql.core.registry import ShapeRegistry

from ._gql import INT, object_type
from .enums import collect_enum_filter_types, collect_enum_types
from .filters import build_filter_type, build_operator_inputs
from .types import build_object_type

RootResolverFactory = Callable[[NodeShapeIR, ShapeRegistry], Callable[..., Any]]


def _introspection_resolver(
    _shape: NodeShapeIR,
    _registry: ShapeRegistry,
) -> Callable[..., Any]:
    """No-op resolver for schema introspection tests."""

    def resolve(*_args: object, **_kwargs: object) -> list[object]:
        return []

    return resolve


def root_field_name(graphql_type_name: str) -> str:
    """Root query field name: ``graphql_type_name.lower() + 's'``."""
    return graphql_type_name.lower() + "s"


def build_schema(
    registry: ShapeRegistry,
    *,
    resolver_factory: RootResolverFactory = _introspection_resolver,
) -> GraphQLSchema:
    """Build a GraphQL schema from parsed SHACL shapes.

    Registers object types for shapes visible in the active ``graphql:Schema``
    (``PUBLIC`` and ``PROTECTED``). Root list fields are emitted only for
    ``PUBLIC`` shapes with a ``sh:targetClass``. Defaults to a no-op resolver
    for introspection-only use; pass :func:`~fastshaql.build_executable_schema`
    for execution.

    Args:
        registry: Parsed shapes indexed for schema and translation.
        resolver_factory: Factory for root field resolvers.

    Returns:
        A graphql-core schema ready for introspection or execution.
    """

    visible_shapes = registry.visible_shapes()
    public_root_shapes = registry.public_root_shapes()

    object_types: dict[str, GraphQLObjectType] = {}
    enum_types = collect_enum_types(visible_shapes)
    for shape in visible_shapes:
        object_types[shape.graphql_type_name] = build_object_type(
            shape, object_types, registry, enum_types=enum_types
        )
    operator_inputs = build_operator_inputs()
    enum_filter_types = collect_enum_filter_types(enum_types)
    filter_types: dict[str, GraphQLInputObjectType] = {}
    for shape in visible_shapes:
        filter_types[shape.graphql_type_name] = build_filter_type(
            shape,
            filter_types,
            operator_inputs,
            registry,
            enum_filter_types=enum_filter_types,
        )
    query_fields = {
        root_field_name(shape.graphql_type_name): GraphQLField(
            GraphQLNonNull(
                GraphQLList(GraphQLNonNull(object_types[shape.graphql_type_name]))
            ),
            args={
                "where": GraphQLArgument(
                    filter_types[shape.graphql_type_name],
                ),
                "limit": GraphQLArgument(INT),
                "offset": GraphQLArgument(INT),
            },
            resolve=resolver_factory(shape, registry),
            description=shape.description,
        )
        for shape in public_root_shapes
    }
    query_type = object_type("Query", query_fields)
    all_types = [
        *object_types.values(),
        *operator_inputs.values(),
        *filter_types.values(),
    ]
    return GraphQLSchema(query_type, types=all_types)
