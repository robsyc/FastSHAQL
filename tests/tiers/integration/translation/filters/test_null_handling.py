"""Null-handling policy for filter translation — ``core/translation/filters/``.

Integration tier: the null-means-absent policy. ``null`` on any nullable
argument, field, or operator operand is a no-op — no ``FILTER`` clause is
emitted and the :class:`NullValueNode` flows through gracefully.

Order: argument-level null → field/operator null → combinator null →
combinator edge cases (empty OR, single OR, empty NOT) → empty relationship.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fastshaql.core.translation import translate_query
from support.graphql_utils import root_field_node
from support.sparql_goldens import PERSON_NAME_ONLY_SPARQL

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry

# ---------------------------------------------------------------------------
# Argument-level null — the whole ``where`` / ``limit`` / ``offset`` is null.
# ---------------------------------------------------------------------------


def test_where_argument_null_equals_baseline(
    filter_person_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``where: null`` is absent — identical to no ``where`` argument."""
    query = "{ persons(where: null) { name } }"
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    assert result.query.render() == PERSON_NAME_ONLY_SPARQL


def test_limit_offset_null_produces_no_pagination(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    """``limit: null`` and ``offset: null`` are absent — no pagination."""
    query = "{ persons(limit: null, offset: null) { name } }"
    result = translate_query(
        person_shape, root_field_node(query), relationship_registry
    )
    rendered = result.query.render()
    assert rendered == PERSON_NAME_ONLY_SPARQL
    assert "LIMIT" not in rendered
    assert "OFFSET" not in rendered


# ---------------------------------------------------------------------------
# Field / operator null — null scalar field, null operator operand, null IRI.
# Each produces no FILTER and matches the unfiltered baseline.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "where_fragment",
    [
        "name: null",
        "name: { eq: null }",
        "name: { in: null }",
        "iri: null",
        "iri: { eq: null }",
    ],
    ids=[
        "scalar_null",
        "operator_eq_null",
        "membership_in_null",
        "iri_null",
        "iri_eq_null",
    ],
)
def test_null_field_or_operator_produces_no_filter(
    filter_person_shape,
    filters_registry: ShapeRegistry,
    where_fragment: str,
) -> None:
    """A null scalar field, operator operand, or IRI filter is a no-op."""
    query = f"{{ persons(where: {{ {where_fragment} }}) {{ name }} }}"
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    rendered = result.query.render()
    assert "FILTER" not in rendered
    assert rendered == PERSON_NAME_ONLY_SPARQL


def test_null_relationship_field_produces_no_filter(
    filter_person_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``employer: null`` emits no FILTER (relationship null is absent)."""
    query = "{ persons(where: { employer: null }) { name } }"
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    assert "FILTER" not in result.query.render()


# ---------------------------------------------------------------------------
# Combinator null — ``AND``/``OR``/``NOT`` carrying a null value.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "combinator",
    ["AND", "OR", "NOT"],
)
def test_null_combinator_produces_no_filter(
    filter_person_shape,
    filters_registry: ShapeRegistry,
    combinator: str,
) -> None:
    """A null combinator value (``AND: null`` etc.) is a no-op."""
    query = f"{{ persons(where: {{ {combinator}: null }}) {{ name }} }}"
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    assert "FILTER" not in result.query.render()


# ---------------------------------------------------------------------------
# Combinator edge cases — empty OR list, single-element OR, empty NOT.
# ---------------------------------------------------------------------------


def test_empty_or_list_is_no_op(
    filter_person_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``OR: []`` has no branches — no FILTER, matches baseline."""
    query = "{ persons(where: { OR: [] }) { name } }"
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    assert result.query.render() == PERSON_NAME_ONLY_SPARQL


def test_single_element_or_unwraps_to_single_filter(
    filter_person_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """A single OR branch is not wrapped in ``||`` — emits the bare filter."""
    query = '{ persons(where: { OR: [{ name: { eq: "Alice" } }] }) { name } }'
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    rendered = result.query.render()
    assert 'FILTER(?name = "Alice")' in rendered
    assert "||" not in rendered


def test_not_empty_object_is_no_op(
    filter_person_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``NOT: {}`` negates nothing — no FILTER, matches baseline."""
    query = "{ persons(where: { NOT: {} }) { name } }"
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    assert result.query.render() == PERSON_NAME_ONLY_SPARQL


def test_not_empty_nested_relationship_produces_no_filter(
    filter_person_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``NOT: { employer: {} }`` — empty inner expression, no FILTER."""
    query = "{ persons(where: { NOT: { employer: {} } }) { name } }"
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    assert "FILTER" not in result.query.render()


# ---------------------------------------------------------------------------
# Null on enum properties — NullValueNode flows through enum-specific paths.
# ---------------------------------------------------------------------------


def test_null_enum_compare_operator_produces_no_filter(
    enums_registry: ShapeRegistry,
) -> None:
    """``status: { eq: null }`` on an enum drops the operator."""
    shape = enums_registry.by_type_name["Observation"]
    query = "{ observations(where: { status: { eq: null } }) { status } }"
    result = translate_query(shape, root_field_node(query), enums_registry)
    assert "FILTER" not in result.query.render()


def test_null_enum_membership_produces_no_filter(
    enums_registry: ShapeRegistry,
) -> None:
    """``status: { in: null }`` on an enum drops the membership."""
    shape = enums_registry.by_type_name["Observation"]
    query = "{ observations(where: { status: { in: null } }) { status } }"
    result = translate_query(shape, root_field_node(query), enums_registry)
    assert "FILTER" not in result.query.render()


# ---------------------------------------------------------------------------
# Null string-function operand — NullValueNode reaches value_to_literal.
# ---------------------------------------------------------------------------


def test_null_string_function_operand_produces_no_filter(
    filter_person_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``name: { startsWith: null }`` drops the string function."""
    query = "{ persons(where: { name: { startsWith: null } }) { name } }"
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    assert "FILTER" not in result.query.render()


# ---------------------------------------------------------------------------
# Empty nested relationship inside EXISTS — ExistsContext short-circuits.
# ---------------------------------------------------------------------------


def test_empty_nested_relationship_in_exists_produces_no_inner_filter(
    filter_person_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``employer: { locatedIn: {} }`` — empty nested rel inside EXISTS."""
    query = "{ persons(where: { employer: { locatedIn: {} } }) { name } }"
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    rendered = result.query.render()
    assert "FILTER(EXISTS" in rendered
    inner = rendered.split("EXISTS", 1)[1] if "EXISTS" in rendered else ""
    assert "FILTER" not in inner


# ---------------------------------------------------------------------------
# AND branch with relationship filter — ExistsExpr wrapping patterns + expr.
# ---------------------------------------------------------------------------


def test_and_branch_with_relationship_filter_wraps_in_exists(
    filter_person_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """Paginated AND branch with a relationship filter produces ExistsExpr wrapping."""
    query = '{ persons(limit: 10, where: { AND: [{ employer: { name: { eq: "Acme" } } }] }) { name employer { name } } }'
    result = translate_query(
        filter_person_shape, root_field_node(query), filters_registry
    )
    rendered = result.query.render()
    assert "FILTER" in rendered
    assert "EXISTS" in rendered
