"""GraphQL union types from polymorphic relationship properties (ADR-0026).

See: https://spec.graphql.org/October2021/#sec-Unions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastshaql.core.kernel.identifiers import first_free_name, property_type_name

from ._gql import union_type

if TYPE_CHECKING:
    from collections.abc import Sequence

    from graphql.type import GraphQLObjectType, GraphQLUnionType

    from fastshaql.core.ir import NodeShapeIR
    from fastshaql.core.registry import ShapeRegistry


def build_union_types(
    shapes: Sequence[NodeShapeIR],
    object_types: dict[str, GraphQLObjectType],
    registry: ShapeRegistry,
    *,
    taken: set[str],
) -> dict[tuple[str, str], GraphQLUnionType]:
    """Union types for every polymorphic property, keyed by
    ``(parent type name, field name)`` — one per pair, no cross-field
    dedupe by member-set (ADR-0026).

    Names are ``{ParentType}{FieldName}`` (``Article.block`` →
    ``ArticleBlock``), numeric-suffixed on collision with anything in
    *taken* — shape names, their filter inputs, enums, and earlier
    unions (the ADR-0006 precedent). Allocation walks shapes
    then properties in registry order, so it is deterministic. Call
    after the object types exist — member types are looked up by name,
    and members are distinct and published by parse-time enforcement
    (ADR-0026).
    """
    unions: dict[tuple[str, str], GraphQLUnionType] = {}
    for shape in shapes:
        for prop in shape.property_shapes.values():
            if not prop.is_polymorphic:
                continue
            field_name = prop.graphql_field_name
            name = first_free_name(
                property_type_name(
                    parent_graphql_type_name=shape.graphql_type_name,
                    graphql_field_name=field_name,
                ),
                taken,
            )
            member_types = tuple(
                object_types[registry.member_shape(member).graphql_type_name]
                for member in prop.union_members
            )
            unions[(shape.graphql_type_name, field_name)] = union_type(
                name, member_types, description=prop.description
            )
    return unions
