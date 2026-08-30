"""GraphQL-schema introspection helpers for build_schema integration tests.

Thin assertions over a built ``graphql-core`` schema: look up named types and
peel ``NonNull``/``List`` wrapping to a ``(required, is_list, base_name)`` tuple.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.type import (
    GraphQLInputObjectType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
)

if TYPE_CHECKING:
    from graphql import GraphQLSchema


def object_type(schema: GraphQLSchema, name: str) -> GraphQLObjectType:
    """Look up a named type in the schema, asserting it is an object type."""
    gql_type = schema.get_type(name)
    assert isinstance(gql_type, GraphQLObjectType)
    return gql_type


def input_type(schema: GraphQLSchema, name: str) -> GraphQLInputObjectType:
    """Look up a named input type in the schema."""
    gql_type = schema.get_type(name)
    assert isinstance(gql_type, GraphQLInputObjectType)
    return gql_type


def input_field_base(gql_type) -> str:
    """Peel back GraphQL wrapping to the base type name."""
    current = gql_type
    if isinstance(current, GraphQLNonNull):
        current = current.of_type
    if isinstance(current, GraphQLList):
        inner = current.of_type
        assert isinstance(inner, GraphQLNonNull)
        current = inner.of_type
    return current.name


def field_shape(gql_type) -> tuple[bool, bool, str]:
    """Peel back GraphQL wrapping to ``(required, is_list, base_name)``."""
    required = is_list = False
    current = gql_type
    if isinstance(current, GraphQLNonNull):
        required = True
        current = current.of_type
    if isinstance(current, GraphQLList):
        is_list = True
        inner = current.of_type
        assert isinstance(inner, GraphQLNonNull)
        current = inner.of_type
    return required, is_list, current.name
