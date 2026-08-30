"""Centralized graphql-core type-construction helpers.

graphql-core 3.x annotates its scalar singletons (``GraphQLID`` &
friends) and its ``(input)object/enum`` constructors as the broad
``GraphQLNamedType``, forcing every call-site to ``cast`` to the concrete type.
These helpers absorb that typing wart in one place so the rest of ``schema/``
reads cleanly. If graphql-core ships stricter stubs, this is the only file to
update.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from graphql.type import (
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLFloat,
    GraphQLID,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLString,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

# Concrete scalar singletons (graphql-core types these as GraphQLNamedType).
ID: GraphQLScalarType = cast("GraphQLScalarType", GraphQLID)
BOOLEAN: GraphQLScalarType = cast("GraphQLScalarType", GraphQLBoolean)
INT: GraphQLScalarType = cast("GraphQLScalarType", GraphQLInt)
FLOAT: GraphQLScalarType = cast("GraphQLScalarType", GraphQLFloat)
STRING: GraphQLScalarType = cast("GraphQLScalarType", GraphQLString)


def input_object(
    name: str,
    fields: Callable[[], Mapping[str, object]] | Mapping[str, object],
    *,
    description: str | None = None,
) -> GraphQLInputObjectType:
    """Construct a ``GraphQLInputObjectType`` without the cast noise."""
    return cast(
        "GraphQLInputObjectType",
        GraphQLInputObjectType(name, fields, description=description),
    )


def object_type(
    name: str,
    fields: Callable[[], Mapping[str, object]] | Mapping[str, object],
    *,
    description: str | None = None,
) -> GraphQLObjectType:
    """Construct a ``GraphQLObjectType`` without the cast noise."""
    return cast(
        "GraphQLObjectType",
        GraphQLObjectType(name, fields, description=description),
    )


def enum_type(name: str, values: Mapping[str, object]) -> GraphQLEnumType:
    """Construct a ``GraphQLEnumType`` without the cast noise."""
    return cast("GraphQLEnumType", GraphQLEnumType(name, values))
