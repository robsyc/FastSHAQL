"""GraphQL enum types from ``sh:in`` property shapes (ADR-0006).

See:
- https://www.w3.org/TR/shacl12-core/#InConstraintComponent
- https://spec.graphql.org/October2021/#sec-Enums
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.type import (
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLList,
    GraphQLNonNull,
)

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR, ValueType
from fastshaql.core.kernel.identifiers import (
    enum_filter_type_name,
    enum_type_name,
)
from fastshaql.core.kernel.operators import EQUALITY_OPS, MEMBERSHIP_OPS

from ._gql import enum_type, input_object

if TYPE_CHECKING:
    from collections.abc import Sequence


def build_enum_type(
    prop: PropertyShapeIR,
    *,
    parent_graphql_type_name: str,
) -> GraphQLEnumType:
    """Build a per-property ``GraphQLEnumType`` from ``sh:in`` values."""
    type_name = enum_type_name(
        parent_graphql_type_name=parent_graphql_type_name,
        graphql_field_name=prop.graphql_field_name,
    )
    values = {
        name: GraphQLEnumValue(value=str(term))
        for name, term in prop.enum_term_by_name.items()
    }
    return enum_type(type_name, values)


def build_enum_filter_type(enum_type: GraphQLEnumType) -> GraphQLInputObjectType:
    """Build a per-enum filter input with eq/neq/in/notIn only."""
    name = enum_filter_type_name(enum_type.name)
    scalar_field = GraphQLInputField(enum_type)
    list_field = GraphQLInputField(GraphQLList(GraphQLNonNull(enum_type)))
    fields = dict.fromkeys(EQUALITY_OPS, scalar_field)
    fields.update(dict.fromkeys(MEMBERSHIP_OPS, list_field))
    return input_object(name, fields)


def collect_enum_types(
    registry_shapes: Sequence[NodeShapeIR],
) -> dict[str, GraphQLEnumType]:
    """Walk *registry_shapes* and build every enum output type, keyed by name.

    Enum type names embed the consuming shape (``enum_type_name``), so an
    inherited enum field (ADR-0005) intentionally produces one type per child
    shape — correct nominal typing, not duplication. Do not dedupe by
    ``PropertyShapeIR.iri``; that would collapse distinct GraphQL types.
    """
    result: dict[str, GraphQLEnumType] = {}
    for shape in registry_shapes:
        for prop in shape.property_shapes.values():
            if prop.value_type is ValueType.ENUM:
                enum_type = build_enum_type(
                    prop, parent_graphql_type_name=shape.graphql_type_name
                )
                result[enum_type.name] = enum_type
    return result


def collect_enum_filter_types(
    enum_types: dict[str, GraphQLEnumType],
) -> dict[str, GraphQLInputObjectType]:
    """Build filter input types for each enum output type."""
    return {
        enum_filter_type_name(name): build_enum_filter_type(enum_type)
        for name, enum_type in enum_types.items()
    }
