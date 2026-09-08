"""Operator input field construction — ``core/schema/filters.py``.

Unit tier: the operator → field-type mapping behind every ``{TypeName}Filter``
input — which operator fields a spec exposes and the GraphQL type each
category carries. The spec table (``_OPERATOR_FIELD_SPECS``) is computed once
at import time, so these contract assertions call the field builder directly;
the built schema only ever sees the cached result.

Order: ordering+membership spec (Int) → pattern spec (String).
"""

from __future__ import annotations

from graphql.type import GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLString

from fastshaql.core.kernel.operators import OPERATOR_INPUT_SPECS
from fastshaql.core.schema.filters import _graphql_fields_for_spec


def test_int_filter_fields_map_operator_categories() -> None:
    fields = _graphql_fields_for_spec(OPERATOR_INPUT_SPECS["IntFilter"])

    assert set(fields) == {"eq", "neq", "gt", "gte", "lt", "lte", "in", "notIn"}
    assert fields["eq"].type is GraphQLInt
    assert fields["lte"].type is GraphQLInt
    membership = fields["in"].type
    assert isinstance(membership, GraphQLList)
    assert isinstance(membership.of_type, GraphQLNonNull)
    assert membership.of_type.of_type is GraphQLInt


def test_string_filter_fields_map_operator_categories() -> None:
    fields = _graphql_fields_for_spec(OPERATOR_INPUT_SPECS["StringFilter"])

    assert set(fields) == {
        "eq",
        "neq",
        "in",
        "notIn",
        "contains",
        "startsWith",
        "endsWith",
        "regex",
    }
    assert fields["eq"].type is GraphQLString
    assert fields["contains"].type is GraphQLString
    assert fields["regex"].type is GraphQLString
