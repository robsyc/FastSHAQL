"""Filter input types — ``core/schema/filters.py``.

Integration tier: ``{TypeName}Filter`` fields — datatype-mapped scalar filters, combinators, iri, relationships, recursion.

Order: datatype mapping → combinators → iri → relationship → recursion → synthetic minimal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rdflib.namespace import RDF, XSD

from fastshaql.core.registry import ShapeRegistry
from fastshaql.core.schema import build_schema
from support.builders import (
    EX,
    node_shape,
    relationship_property,
    scalar_property,
    shape_with,
)
from support.schema_helpers import field_shape, input_field_base, input_type

if TYPE_CHECKING:
    from rdflib import URIRef

# --- Datatype → scalar filter mapping ---


@pytest.mark.parametrize(
    ("datatype", "expected_filter"),
    [
        (XSD.string, "StringFilter"),
        (XSD.integer, "IntFilter"),
        (XSD.boolean, "BooleanFilter"),
        (XSD.decimal, "FloatFilter"),
    ],
    ids=["string", "integer", "boolean", "decimal"],
)
def test_build_schema_scalar_property_filter_field(
    datatype: URIRef,
    expected_filter: str,
) -> None:
    """A scalar property's ``sh:datatype`` maps its filter field to the matching ``*Filter``."""
    shape = node_shape(
        "Sample",
        property_shapes={
            "value": scalar_property(
                "value", min_count=1, max_count=1, datatype=datatype
            ),
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    sample_filter = input_type(schema, "SampleFilter")

    assert input_field_base(sample_filter.fields["value"].type) == expected_filter


@pytest.mark.parametrize(
    "datatypes",
    [
        (XSD.string,),
        (RDF.langString,),
        (XSD.string, RDF.langString),
    ],
    ids=["plain", "language", "union"],
)
def test_build_schema_string_family_spaces_take_string_filter(
    datatypes: tuple,
) -> None:
    """All three string-family literal spaces yield ``StringFilter`` — the
    union by explicit space dispatch (valid across both lexical forms)."""
    shape = node_shape(
        "Sample",
        property_shapes={
            "value": scalar_property(
                "value", min_count=1, max_count=1, datatype=None, datatypes=datatypes
            ),
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    sample_filter = input_type(schema, "SampleFilter")

    assert input_field_base(sample_filter.fields["value"].type) == "StringFilter"


# --- Combinators ---


def test_build_schema_filter_combinators() -> None:
    shape = node_shape(
        "Person",
        property_shapes={
            "name": scalar_property("name", min_count=1, max_count=1),
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    person_filter = input_type(schema, "PersonFilter")

    assert set(person_filter.fields) >= {"AND", "OR", "NOT"}
    assert input_field_base(person_filter.fields["AND"].type) == "PersonFilter"
    assert input_field_base(person_filter.fields["OR"].type) == "PersonFilter"
    assert input_field_base(person_filter.fields["NOT"].type) == "PersonFilter"
    _, and_is_list, _ = field_shape(person_filter.fields["AND"].type)
    _, or_is_list, _ = field_shape(person_filter.fields["OR"].type)
    assert and_is_list is True
    assert or_is_list is True


# --- IRI ---


def test_build_schema_filter_iri_field() -> None:
    shape = node_shape(
        "Person",
        property_shapes={
            "name": scalar_property("name", min_count=1, max_count=1),
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    person_filter = input_type(schema, "PersonFilter")

    assert input_field_base(person_filter.fields["iri"].type) == "IriFilter"


def test_build_schema_iri_filter_string_pattern_fields() -> None:
    schema = build_schema(ShapeRegistry([node_shape("Person", property_shapes={})]))
    iri_filter = input_type(schema, "IriFilter")

    assert {"contains", "startsWith", "endsWith", "regex"} <= set(iri_filter.fields)


# --- Relationship ---


def test_build_schema_relationship_filter_field() -> None:
    company = node_shape("Company", property_shapes={})
    person = node_shape(
        "Person",
        property_shapes={
            "employer": relationship_property(
                "employer",
                value_shape_iri=company.iri,
                value_class=EX + "Company",
                min_count=0,
                max_count=1,
            ),
        },
    )
    schema = build_schema(ShapeRegistry([person, company]))
    person_filter = input_type(schema, "PersonFilter")

    assert input_field_base(person_filter.fields["employer"].type) == "CompanyFilter"


# --- Recursion ---


def test_build_schema_recursive_filter_type() -> None:
    person = node_shape("Person", property_shapes={})
    friend = relationship_property(
        "friend",
        value_shape_iri=person.iri,
        value_class=EX + "Person",
        min_count=0,
        max_count=1,
    )
    person = shape_with(person, friend=friend)
    schema = build_schema(ShapeRegistry([person]))
    person_filter = input_type(schema, "PersonFilter")

    assert input_field_base(person_filter.fields["friend"].type) == "PersonFilter"


# --- Synthetic minimal ---


def test_build_schema_synthetic_shape_minimal_filter() -> None:
    department = node_shape("Department", target_class=None, property_shapes={})
    schema = build_schema(ShapeRegistry([department]))
    department_filter = input_type(schema, "DepartmentFilter")

    assert set(department_filter.fields) == {"iri", "AND", "OR", "NOT"}
    assert input_field_base(department_filter.fields["iri"].type) == "IriFilter"
