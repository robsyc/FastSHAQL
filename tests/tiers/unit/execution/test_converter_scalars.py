"""Converter scalar and list grouping — ``core/execution/converter.py``.

Unit tier: flat field grouping, list dedup, optional field semantics, iri projection.
Relationship nesting tests live in ``test_converter_relationships.py``.

Order: flat scalars → list grouping → optional fields → iri projection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import Literal, URIRef, Variable

from fastshaql.core.execution.converter import convert_rows
from fastshaql.core.translation.variables import VariableMap
from support.builders import node_shape, scalar_property
from support.converter_helpers import ALICE, empty_registry, flat_var_map

if TYPE_CHECKING:
    from fastshaql.core.execution.store import SparqlRow
    from fastshaql.core.registry import ShapeRegistry


def test_convert_rows_groups_required_list_values() -> None:
    shape = node_shape(
        "Thing",
        property_shapes={"tag": scalar_property("tag", min_count=1, max_count=None)},
    )
    iri = URIRef("http://example.org/thing-1")
    rows: list[SparqlRow] = [
        {"iri": iri, "tag": Literal("red")},
        {"iri": iri, "tag": Literal("blue")},
    ]
    result = convert_rows(rows, shape, flat_var_map(tag="tag"), empty_registry())
    assert result == [{"tag": ["red", "blue"]}]


def test_convert_rows_dedupes_cartesian_product_lists() -> None:
    shape = node_shape(
        "Thing",
        property_shapes={
            "tag": scalar_property("tag", min_count=1, max_count=None),
            "altLabel": scalar_property("altLabel", min_count=0, max_count=None),
        },
    )
    iri = URIRef("http://example.org/thing-1")
    rows: list[SparqlRow] = [
        {"iri": iri, "tag": Literal("red"), "altLabel": Literal("A")},
        {"iri": iri, "tag": Literal("red"), "altLabel": Literal("B")},
        {"iri": iri, "tag": Literal("blue"), "altLabel": Literal("A")},
        {"iri": iri, "tag": Literal("blue"), "altLabel": Literal("B")},
    ]
    var_map = flat_var_map(tag="tag", altLabel="altLabel")
    result = convert_rows(rows, shape, var_map, empty_registry())
    assert result == [{"tag": ["red", "blue"], "altLabel": ["A", "B"]}]


def test_convert_rows_initializes_absent_optional_list_as_empty() -> None:
    shape = node_shape(
        "Thing",
        property_shapes={
            "label": scalar_property("label", min_count=1, max_count=1),
            "altLabel": scalar_property("altLabel", min_count=0, max_count=None),
        },
    )
    iri = URIRef("http://example.org/thing-2")
    rows: list[SparqlRow] = [{"iri": iri, "label": Literal("Beta")}]
    var_map = flat_var_map(label="label", altLabel="altLabel")
    result = convert_rows(rows, shape, var_map, empty_registry())
    assert result == [{"label": "Beta", "altLabel": []}]


def test_convert_rows_omits_absent_optional_scalar_key() -> None:
    shape = node_shape(
        "Thing",
        property_shapes={
            "label": scalar_property("label", min_count=1, max_count=1),
            "subtitle": scalar_property("subtitle", min_count=0, max_count=1),
        },
    )
    iri = URIRef("http://example.org/thing-2")
    rows: list[SparqlRow] = [{"iri": iri, "label": Literal("Beta")}]
    var_map = flat_var_map(label="label", subtitle="subtitle")
    result = convert_rows(rows, shape, var_map, empty_registry())
    assert result == [{"label": "Beta"}]
    assert "subtitle" not in result[0]


def test_convert_rows_groups_multiple_entities_independently() -> None:
    shape = node_shape(
        "Thing",
        property_shapes={
            "label": scalar_property("label", min_count=1, max_count=1),
            "tag": scalar_property("tag", min_count=1, max_count=None),
        },
    )
    rows: list[SparqlRow] = [
        {
            "iri": URIRef("http://example.org/thing-1"),
            "label": Literal("Alpha"),
            "tag": Literal("red"),
        },
        {
            "iri": URIRef("http://example.org/thing-1"),
            "label": Literal("Alpha"),
            "tag": Literal("blue"),
        },
        {
            "iri": URIRef("http://example.org/thing-2"),
            "label": Literal("Beta"),
            "tag": Literal("green"),
        },
    ]
    var_map = flat_var_map(label="label", tag="tag")
    result = convert_rows(rows, shape, var_map, empty_registry())
    assert result == [
        {"label": "Alpha", "tag": ["red", "blue"]},
        {"label": "Beta", "tag": ["green"]},
    ]


def test_convert_rows_omits_iri_when_not_in_var_map(
    relationship_registry: ShapeRegistry,
) -> None:
    shape = relationship_registry.by_type_name["Person"]
    rows: list[SparqlRow] = [{"iri": ALICE, "name": Literal("Alice")}]
    var_map = VariableMap(
        subject_var=Variable("iri"),
        fields={"name": Variable("name")},
        relationships={},
    )
    result = convert_rows(rows, shape, var_map, relationship_registry)
    assert result == [{"name": "Alice"}]
    assert "iri" not in result[0]


def test_convert_rows_includes_iri_when_in_var_map(
    relationship_registry: ShapeRegistry,
) -> None:
    shape = relationship_registry.by_type_name["Person"]
    rows: list[SparqlRow] = [{"iri": ALICE, "name": Literal("Alice")}]
    var_map = VariableMap(
        subject_var=Variable("iri"),
        fields={"iri": Variable("iri"), "name": Variable("name")},
        relationships={},
    )
    result = convert_rows(rows, shape, var_map, relationship_registry)
    assert result == [{"iri": str(ALICE), "name": "Alice"}]
