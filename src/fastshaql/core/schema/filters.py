"""GraphQL filter input types for composable ``where`` arguments (ADR-0009).

Operator sets are defined in :mod:`fastshaql.core.operators` and mirrored here
as graphql-core input types. See SPARQL 1.2 §17.3 and GraphQL input objects.

See:
- https://www.w3.org/TR/sparql12-query/#operatorMapping
- https://spec.graphql.org/October2021/#sec-Input-Objects
"""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from graphql.type import (
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInputType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLScalarType,
)

from fastshaql.core.ir import NodeShapeIR, ValueType
from fastshaql.core.kernel.identifiers import enum_filter_type_name, enum_type_name
from fastshaql.core.kernel.operators import (
    EQUALITY_OPS,
    MEMBERSHIP_OPS,
    OPERATOR_INPUT_SPECS,
    ORDERING_OPS,
    STRING_PATTERN_OPS,
    OperatorInputSpec,
    operator_field_names,
)

from ._gql import input_object
from .scalars import (
    filter_category_for_space,
    filter_operator_for_category,
    graphql_scalar_for_filter,
)

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry

_STRING = graphql_scalar_for_filter("StringFilter")


def _input_field(field_type: GraphQLInputType) -> GraphQLInputField:
    """Nullable input field — all filter operators are optional."""
    return GraphQLInputField(field_type)


def _list_field(scalar: GraphQLScalarType) -> GraphQLInputField:
    return _input_field(GraphQLList(GraphQLNonNull(scalar)))


def _graphql_fields_for_spec(spec: OperatorInputSpec) -> dict[str, GraphQLInputField]:
    """Build GraphQL input fields from a shared operator spec.

    ``operator_field_names`` is the single source of truth for *which* ops a
    spec exposes; this function only decides the field *type* per op category.
    """
    scalar = graphql_scalar_for_filter(spec.graphql_name)
    field_type_by_op: dict[str, GraphQLInputField] = {
        **dict.fromkeys(EQUALITY_OPS + ORDERING_OPS, _input_field(scalar)),
        **dict.fromkeys(MEMBERSHIP_OPS, _list_field(scalar)),
        **dict.fromkeys(STRING_PATTERN_OPS, _input_field(_STRING)),
    }
    return {op: field_type_by_op[op] for op in operator_field_names(spec)}


_OPERATOR_FIELD_SPECS: dict[str, dict[str, GraphQLInputField]] = {
    spec.graphql_name: _graphql_fields_for_spec(spec)
    for spec in OPERATOR_INPUT_SPECS.values()
}


def filter_input_name(graphql_type_name: str) -> str:
    """Filter input type name for a node shape."""
    return f"{graphql_type_name}Filter"


def _combinator_fields(
    self_type: GraphQLInputObjectType,
) -> dict[str, GraphQLInputField]:
    return {
        "AND": _input_field(GraphQLList(GraphQLNonNull(self_type))),
        "OR": _input_field(GraphQLList(GraphQLNonNull(self_type))),
        "NOT": _input_field(self_type),
    }


@cache
def build_operator_inputs() -> dict[str, GraphQLInputObjectType]:
    """Return singleton operator input types keyed by GraphQL type name."""
    return {
        name: input_object(name, fields)
        for name, fields in _OPERATOR_FIELD_SPECS.items()
    }


def build_filter_type(
    shape: NodeShapeIR,
    filter_types: dict[str, GraphQLInputObjectType],
    operator_inputs: dict[str, GraphQLInputObjectType],
    registry: ShapeRegistry,
    *,
    enum_filter_types: dict[str, GraphQLInputObjectType],
) -> GraphQLInputObjectType:
    """Build a per-shape filter input with thunked fields for recursion."""
    type_name = filter_input_name(shape.graphql_type_name)

    def fields() -> dict[str, GraphQLInputField]:
        self_type = filter_types[shape.graphql_type_name]
        result: dict[str, GraphQLInputField] = {}
        for name, prop in shape.property_shapes.items():
            match prop.value_type:
                case ValueType.RELATIONSHIP:
                    target = registry.resolve_relationship_target(prop, field_name=name)
                    result[name] = _input_field(filter_types[target.graphql_type_name])
                case ValueType.ENUM:
                    type_name = enum_type_name(
                        parent_graphql_type_name=shape.graphql_type_name,
                        graphql_field_name=prop.graphql_field_name,
                    )
                    result[name] = _input_field(
                        enum_filter_types[enum_filter_type_name(type_name)]
                    )
                # ``case`` fall-through below the last arm is unreachable:
                # the ValueType union is closed (no wildcard arm).
                case ValueType.SCALAR:  # pragma: no branch — closed union
                    operator_name = filter_operator_for_category(
                        filter_category_for_space(prop)
                    )
                    result[name] = _input_field(operator_inputs[operator_name])
        result["iri"] = _input_field(operator_inputs["IriFilter"])
        result.update(_combinator_fields(self_type))
        return result

    return input_object(type_name, fields)
