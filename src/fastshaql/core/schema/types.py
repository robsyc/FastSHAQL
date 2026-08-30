"""GraphQL object types from node shapes.

See:
- https://www.w3.org/TR/shacl12-core/#node-shapes
- https://spec.graphql.org/October2021/#sec-ID
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.type import (
    GraphQLField,
    GraphQLNonNull,
    GraphQLObjectType,
)

from fastshaql.core.kernel.constants import IRI_FIELD

from ._gql import ID, object_type
from .fields import build_field

if TYPE_CHECKING:
    from graphql.type.definition import GraphQLEnumType

    from fastshaql.core.ir import NodeShapeIR
    from fastshaql.core.registry import ShapeRegistry


def build_object_type(
    shape: NodeShapeIR,
    types: dict[str, GraphQLObjectType],
    registry: ShapeRegistry,
    *,
    enum_types: dict[str, GraphQLEnumType],
) -> GraphQLObjectType:
    """Build a GraphQL object type with ``iri: ID!`` plus property shape fields.

    Uses a thunked ``fields`` callable so recursive relationship types (e.g.
    ``Person.friend → Person``) resolve after all types are registered.

    Args:
        shape: The node shape to build a type for.
        types: GraphQL object types indexed by ``graphql_type_name``.
        registry: Shape registry for dereferencing ``value_shape_iri``.

    Returns:
        A graphql-core ``GraphQLObjectType``.
    """

    def fields() -> dict[str, GraphQLField]:
        return {
            IRI_FIELD: GraphQLField(
                GraphQLNonNull(ID),
            ),
            **{
                name: build_field(
                    prop,
                    types,
                    registry,
                    parent_graphql_type_name=shape.graphql_type_name,
                    enum_types=enum_types,
                )
                for name, prop in shape.property_shapes.items()
            },
        }

    return object_type(
        shape.graphql_type_name,
        fields,
        description=shape.description,
    )
