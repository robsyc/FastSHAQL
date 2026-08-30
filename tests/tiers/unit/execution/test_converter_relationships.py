"""Converter relationship nesting — ``core/execution/converter.py``.

Unit tier: recursive row grouping for relationship fields. Scalar/list tests
live in ``test_converter_scalars.py``.

Order: single-level nesting → multi-level nesting → var_map bridge.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import parse as gql_parse
from graphql.language.ast import FieldNode
from graphql.language.parser import OperationDefinitionNode
from rdflib import Literal

from fastshaql.core.execution.converter import convert_rows
from fastshaql.core.registry import ShapeRegistry
from fastshaql.core.translation import translate_query
from support.builders import EX, node_shape, relationship_property, scalar_property
from support.converter_helpers import (
    ACME,
    ALICE,
    AMSTERDAM,
    BERLIN,
    BOB,
    CAROL,
    GLOBEX,
    nested_converter_case,
)

if TYPE_CHECKING:
    from fastshaql.core.execution.store import SparqlRow

# --- Single-level nesting ---


def test_convert_rows_required_relationship_one_child(
    relationship_registry: ShapeRegistry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    var_map = nested_converter_case(relationship="employer")
    rows: list[SparqlRow] = [
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "employer_iri": ACME,
            "employer_name": Literal("Acme"),
        },
    ]
    result = convert_rows(rows, person, var_map, relationship_registry)
    assert result == [{"name": "Alice", "employer": {"name": "Acme"}}]


def test_convert_rows_multi_valued_relationship(
    relationship_registry: ShapeRegistry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    var_map = nested_converter_case(relationship="knows")
    rows: list[SparqlRow] = [
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "knows_iri": BOB,
            "knows_name": Literal("Bob"),
        },
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "knows_iri": CAROL,
            "knows_name": Literal("Carol"),
        },
    ]
    result = convert_rows(rows, person, var_map, relationship_registry)
    assert result == [
        {"name": "Alice", "knows": [{"name": "Bob"}, {"name": "Carol"}]},
    ]


def test_convert_rows_optional_relationship_absent(
    relationship_registry: ShapeRegistry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    var_map = nested_converter_case(relationship="employer")
    rows: list[SparqlRow] = [{"iri": CAROL, "name": Literal("Carol")}]
    result = convert_rows(rows, person, var_map, relationship_registry)
    assert result == [{"name": "Carol"}]
    assert "employer" not in result[0]


# --- Multi-level nesting ---


def test_convert_rows_two_level_nesting(
    relationship_registry: ShapeRegistry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    var_map = nested_converter_case(relationship="employer", nested="locatedIn")
    rows: list[SparqlRow] = [
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "employer_iri": ACME,
            "employer_name": Literal("Acme"),
            "employer_locatedIn_iri": AMSTERDAM,
            "employer_locatedIn_name": Literal("Amsterdam"),
        },
        {
            "iri": BOB,
            "name": Literal("Bob"),
            "employer_iri": GLOBEX,
            "employer_name": Literal("Globex"),
            "employer_locatedIn_iri": BERLIN,
            "employer_locatedIn_name": Literal("Berlin"),
        },
    ]
    result = convert_rows(rows, person, var_map, relationship_registry)
    assert result == [
        {
            "name": "Alice",
            "employer": {"name": "Acme", "locatedIn": {"name": "Amsterdam"}},
        },
        {
            "name": "Bob",
            "employer": {"name": "Globex", "locatedIn": {"name": "Berlin"}},
        },
    ]


def test_convert_rows_recursive_relationship_two_levels(
    relationship_registry: ShapeRegistry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    var_map = nested_converter_case(relationship="knows", nested="knows")
    rows: list[SparqlRow] = [
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "knows_iri": BOB,
            "knows_name": Literal("Bob"),
            "knows_knows_iri": CAROL,
            "knows_knows_name": Literal("Carol"),
        },
    ]
    result = convert_rows(rows, person, var_map, relationship_registry)
    assert result == [
        {"name": "Alice", "knows": [{"name": "Bob", "knows": [{"name": "Carol"}]}]},
    ]


def test_convert_rows_two_entities_with_different_children(
    relationship_registry: ShapeRegistry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    var_map = nested_converter_case(relationship="employer")
    rows: list[SparqlRow] = [
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "employer_iri": ACME,
            "employer_name": Literal("Acme"),
        },
        {
            "iri": BOB,
            "name": Literal("Bob"),
            "employer_iri": GLOBEX,
            "employer_name": Literal("Globex"),
        },
    ]
    result = convert_rows(rows, person, var_map, relationship_registry)
    assert result == [
        {"name": "Alice", "employer": {"name": "Acme"}},
        {"name": "Bob", "employer": {"name": "Globex"}},
    ]


def test_convert_rows_relationship_with_multi_valued_child_scalar() -> None:
    company = node_shape(
        "Company",
        property_shapes={
            "name": scalar_property("name", min_count=1, max_count=1),
            "tag": scalar_property("tag", min_count=0, max_count=None),
        },
    )
    company_iri = EX + "CompanyShape"
    person = node_shape(
        "Person",
        property_shapes={
            "name": scalar_property("name", min_count=1, max_count=1),
            "employer": relationship_property(
                "employer",
                company_iri,
                min_count=0,
                max_count=1,
                value_class=EX + "Company",
            ),
        },
    )
    registry = ShapeRegistry([person, company])
    var_map = nested_converter_case(
        relationship="employer", child_fields=("name", "tag")
    )
    rows: list[SparqlRow] = [
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "employer_iri": ACME,
            "employer_name": Literal("Acme"),
            "employer_tag": Literal("tech"),
        },
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "employer_iri": ACME,
            "employer_name": Literal("Acme"),
            "employer_tag": Literal("corp"),
        },
    ]
    result = convert_rows(rows, person, var_map, registry)
    assert result == [
        {"name": "Alice", "employer": {"name": "Acme", "tag": ["tech", "corp"]}},
    ]


# --- Var_map bridge ---


def test_convert_rows_var_map_from_translation_matches_manual(
    relationship_registry: ShapeRegistry,
) -> None:
    doc = gql_parse("{ persons { name employer { name locatedIn { name } } } }")
    op = doc.definitions[0]
    assert isinstance(op, OperationDefinitionNode)
    field_node = op.selection_set.selections[0]
    assert isinstance(field_node, FieldNode)

    person = relationship_registry.by_type_name["Person"]
    translation = translate_query(person, field_node, relationship_registry)
    rows: list[SparqlRow] = [
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "employer_iri": ACME,
            "employer_name": Literal("Acme"),
            "employer_locatedIn_iri": AMSTERDAM,
            "employer_locatedIn_name": Literal("Amsterdam"),
        },
    ]
    converted = convert_rows(rows, person, translation.var_map, relationship_registry)
    assert converted == [
        {
            "name": "Alice",
            "employer": {"name": "Acme", "locatedIn": {"name": "Amsterdam"}},
        },
    ]


# --- List-relationship dedup ---


def test_convert_rows_list_relationship_dedups_child_iri(
    relationship_registry: ShapeRegistry,
) -> None:
    """A list relationship entity appearing in multiple cartesian-product rows
    is emitted only once in the nested list."""
    person = relationship_registry.by_type_name["Person"]
    var_map = nested_converter_case(relationship="knows", child_fields=("iri", "name"))
    rows: list[SparqlRow] = [
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "knows_iri": BOB,
            "knows_name": Literal("Bob"),
        },
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "knows_iri": BOB,
            "knows_name": Literal("Bob"),
        },
        {
            "iri": ALICE,
            "name": Literal("Alice"),
            "knows_iri": CAROL,
            "knows_name": Literal("Carol"),
        },
    ]
    result = convert_rows(rows, person, var_map, relationship_registry)
    assert result == [
        {
            "name": "Alice",
            "knows": [
                {"iri": str(BOB), "name": "Bob"},
                {"iri": str(CAROL), "name": "Carol"},
            ],
        },
    ]
