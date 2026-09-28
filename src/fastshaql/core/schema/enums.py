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
    filter_input_name,
    first_free_name,
    property_type_name,
)
from fastshaql.core.kernel.operators import EQUALITY_OPS, MEMBERSHIP_OPS

from ._gql import enum_type, input_object

if TYPE_CHECKING:
    from collections.abc import Sequence


def build_enum_type(prop: PropertyShapeIR, *, name: str) -> GraphQLEnumType:
    """Build a per-property ``GraphQLEnumType`` under an allocated *name*."""
    values = {
        member: GraphQLEnumValue(value=str(term))
        for member, term in prop.enum_term_by_name.items()
    }
    return enum_type(name, values)


def build_enum_filter_type(
    enum_type: GraphQLEnumType, *, name: str
) -> GraphQLInputObjectType:
    """Build a per-enum filter input with eq/neq/in/notIn only."""
    scalar_field = GraphQLInputField(enum_type)
    list_field = GraphQLInputField(GraphQLList(GraphQLNonNull(enum_type)))
    fields = dict.fromkeys(EQUALITY_OPS, scalar_field)
    fields.update(dict.fromkeys(MEMBERSHIP_OPS, list_field))
    return input_object(name, fields)


def collect_enum_types(
    registry_shapes: Sequence[NodeShapeIR],
    taken: set[str],
) -> dict[tuple[str, str], GraphQLEnumType]:
    """Walk *registry_shapes* and build every enum output type, keyed by
    ``(parent type name, field name)`` — stable while the type names
    themselves may suffix.

    Names are ``{TypeName}{FieldName}`` allocated through *taken* (numeric
    suffix on collision, ADR-0006); an inherited enum field (ADR-0005)
    intentionally produces one type per child shape — correct nominal
    typing, not duplication. Do not dedupe by ``PropertyShapeIR.iri``;
    that would collapse distinct GraphQL types.
    """
    result: dict[tuple[str, str], GraphQLEnumType] = {}
    for shape in registry_shapes:
        for prop in shape.property_shapes.values():
            if prop.value_type is ValueType.ENUM:
                base = property_type_name(
                    parent_graphql_type_name=shape.graphql_type_name,
                    graphql_field_name=prop.graphql_field_name,
                )
                result[(shape.graphql_type_name, prop.graphql_field_name)] = (
                    build_enum_type(prop, name=first_free_name(base, taken))
                )
    return result


def collect_enum_filter_types(
    enum_types: dict[tuple[str, str], GraphQLEnumType],
    taken: set[str],
) -> dict[tuple[str, str], GraphQLInputObjectType]:
    """Build filter input types for each enum output type, keyed by the
    same ``(parent type name, field name)``."""
    return {
        key: build_enum_filter_type(
            enum_type,
            name=first_free_name(filter_input_name(enum_type.name), taken),
        )
        for key, enum_type in enum_types.items()
    }
