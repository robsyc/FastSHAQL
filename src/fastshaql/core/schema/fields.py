"""GraphQL field construction from property shapes.

See:
- https://www.w3.org/TR/shacl12-core/#property-shapes
- https://spec.graphql.org/October2021/#sec-Non-Null
- https://spec.graphql.org/October2021/#sec-List
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from graphql.type import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLOutputType,
)

from fastshaql.core.ir import FieldKind, PropertyShapeIR, ValueType
from fastshaql.core.kernel.identifiers import enum_type_name

from .scalars import scalar_type_for_space

if TYPE_CHECKING:
    from graphql.type.definition import GraphQLNullableType

    from fastshaql.core.registry import ShapeRegistry


def wrap_field_type(base: GraphQLNullableType, kind: FieldKind) -> GraphQLOutputType:
    """Apply GraphQL list and non-null wrapping for a ``FieldKind``.

    NOTE: Inner non-null on list elements (``[Type!]``) applies to both scalar
    and relationship fields — SPARQL triple patterns produce actual values (literals
    or resource IRIs), never nulls. For relationships, each list element is a
    non-null object with at least an ``iri`` field. This matches the scalar
    convention and avoids partial-result nullification.
    """
    if kind.is_list:
        inner: GraphQLOutputType = GraphQLList(GraphQLNonNull(base))
        return GraphQLNonNull(inner) if kind.is_required else inner
    return GraphQLNonNull(base) if kind.is_required else cast("GraphQLOutputType", base)


def build_field(
    prop: PropertyShapeIR,
    types: dict[str, GraphQLObjectType],
    registry: ShapeRegistry,
    *,
    parent_graphql_type_name: str,
    enum_types: dict[str, GraphQLEnumType],
) -> GraphQLField:
    """Build a GraphQL field from a property shape (scalar, enum, or relationship).

    Args:
        prop: The property shape to build a field for.
        types: GraphQL object types indexed by ``graphql_type_name``.
        registry: Shape registry for dereferencing ``value_shape_iri``.
        parent_graphql_type_name: GraphQL type name of the enclosing node shape.
        enum_types: Shared enum types indexed by GraphQL enum type name.

    Returns:
        A graphql-core ``GraphQLField`` with appropriate type wrapping.
    """
    match prop.value_type:
        case ValueType.RELATIONSHIP:
            target = registry.resolve_relationship_target(prop)
            base = types[target.graphql_type_name]
        case ValueType.ENUM:
            type_name = enum_type_name(
                parent_graphql_type_name=parent_graphql_type_name,
                graphql_field_name=prop.graphql_field_name,
            )
            base = enum_types[type_name]
        case (
            ValueType.SCALAR
        ):  # pragma: no branch — closed ValueType union: no fall-through
            base = scalar_type_for_space(prop)
    return GraphQLField(
        wrap_field_type(
            base, prop.kind
        ),  # non-null synthesis for defaulted fields lives in kind (SD-6)
        description=prop.description,
    )
