"""Schema construction — ``core/schema/build.py``.

Integration tier: ``build_schema`` output — types, fields, nullability, root-field arguments.

Order: minimal baseline → cardinality → errors → enums → relationships → arguments → default resolver.
"""

from __future__ import annotations

import pytest
from graphql import GraphQLEnumType, Undefined
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from fastshaql.core.ir.node_expr import ConstantNodeExpr
from fastshaql.core.parser import parse_shapes
from fastshaql.core.registry import ShapeRegistry
from fastshaql.core.schema import build_schema
from fastshaql.core.schema.build import DuplicateRootFieldError
from support.builders import (
    EX,
    defaulted_property,
    node_shape,
    relationship_property,
    scalar_property,
    shape_with,
)
from support.schema_helpers import field_shape, input_field_base, object_type

# --- Minimal fixture baseline ---


def test_build_schema_from_minimal_fixture(minimal_registry: ShapeRegistry) -> None:
    """Real shapes graph produces a valid schema with correct types."""
    schema = build_schema(minimal_registry)
    query = schema.query_type
    assert query is not None

    thing = query.fields["thing"]
    required, is_list, base = field_shape(thing.type)
    assert (required, is_list, base) == (True, True, "Thing")

    thing = object_type(schema, "Thing")
    assert field_shape(thing.fields["iri"].type) == (True, False, "ID")
    assert field_shape(thing.fields["label"].type) == (True, False, "String")


# --- Cardinality ---


@pytest.mark.parametrize(
    ("min_count", "max_count", "expected"),
    [
        (1, 1, (True, False, "String")),
        (0, 1, (False, False, "String")),
        (1, None, (True, True, "String")),
        (0, None, (False, True, "String")),
    ],
    ids=["required_scalar", "optional_scalar", "required_list", "optional_list"],
)
def test_build_schema_nullability_by_cardinality(
    min_count: int | None,
    max_count: int | None,
    expected: tuple[bool, bool, str],
) -> None:
    """SHACL cardinality determines GraphQL nullability and list wrapping."""
    shape = node_shape(
        "Card",
        property_shapes={
            "value": scalar_property("value", min_count=min_count, max_count=max_count)
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    card = object_type(schema, "Card")
    assert field_shape(card.fields["value"].type) == expected


@pytest.mark.parametrize(
    "datatype",
    [EX + "customType", None],
    ids=["unknown_datatype", "no_datatype"],
)
def test_build_schema_datatype_fallback_to_string(datatype: URIRef | None) -> None:
    """An unrecognised or absent ``sh:datatype`` maps to ``String``."""
    shape = node_shape(
        "Custom",
        property_shapes={
            "code": scalar_property(
                "code", min_count=1, max_count=1, datatype=datatype
            ),
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    custom = object_type(schema, "Custom")
    assert field_shape(custom.fields["code"].type) == (True, False, "String")


@pytest.mark.parametrize(
    "datatypes",
    [
        (XSD.string,),
        (RDF.langString,),
        (XSD.string, RDF.langString),
    ],
    ids=["plain", "language", "union"],
)
def test_build_schema_string_family_spaces_are_string_output(
    datatypes: tuple,
) -> None:
    """All three string-family literal spaces yield ``String`` output — the
    union by explicit space dispatch, not by a ``datatype=None`` accident."""
    shape = node_shape(
        "Note",
        property_shapes={
            "note": scalar_property(
                "note", min_count=0, max_count=1, datatype=None, datatypes=datatypes
            ),
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    note = object_type(schema, "Note")
    assert field_shape(note.fields["note"].type) == (False, False, "String")


@pytest.mark.parametrize("min_count", [0, 1], ids=["mincount_0", "mincount_1"])
def test_build_schema_defaulted_field_is_non_nullable(min_count: int) -> None:
    """A defaulted field is non-nullable regardless of ``sh:minCount`` — the
    COALESCE always binds a value (SD-6)."""
    shape = node_shape(
        "Fb",
        property_shapes={
            "source": defaulted_property(
                "source",
                default_expr=ConstantNodeExpr(Literal("FSQ-REG")),
                min_count=min_count,
                max_count=1,
            )
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    fb = object_type(schema, "Fb")
    non_null, _, _ = field_shape(fb.fields["source"].type)
    assert non_null is True


# --- Error cases ---


def test_build_schema_root_fields_skip_shapes_without_target_class() -> None:
    """Only shapes with ``sh:targetClass`` get root query fields; all types still registered."""
    schema = build_schema(
        ShapeRegistry(
            [
                node_shape("Thing", target_class=EX + "Thing"),
                node_shape("Orphan", target_class=None),
                node_shape("Person", target_class=EX + "Person"),
            ]
        )
    )
    query = schema.query_type
    assert query is not None
    assert set(query.fields) == {"thing", "person"}
    assert schema.get_type("Orphan") is not None


def test_build_schema_duplicate_root_field_names_raise() -> None:
    """Two type names decapitalizing to one root field (``Foo``/``foo``)
    collide loudly, not last-shape-wins."""
    with pytest.raises(
        DuplicateRootFieldError,
        match=r"Duplicate root field 'foo': types 'Foo' and 'foo'",
    ):
        build_schema(ShapeRegistry([node_shape("Foo"), node_shape("foo")]))


def test_build_schema_empty_registry() -> None:
    """An empty registry produces a schema with a Query type and no fields."""
    schema = build_schema(ShapeRegistry([]))
    query = schema.query_type
    assert query is not None
    assert query.fields == {}


# --- Enums ---


def test_build_schema_enum_mangle_collision_disambiguates(
    enums_registry: ShapeRegistry,
) -> None:
    """FHIR Quantity comparators (all mangle to ``_``) build with ``_2``/``_3``/
    ``_4`` suffixes; the reverse map recovers each distinct rdflib term."""
    schema = build_schema(enums_registry)

    comparator = schema.get_type("QuantityComparator")
    assert isinstance(comparator, GraphQLEnumType)
    assert list(comparator.values) == ["_", "_2", "_3", "_4"]
    assert [value.value for value in comparator.values.values()] == [
        "<",
        "<=",
        ">=",
        ">",
    ]

    prop = enums_registry.by_type_name["Quantity"].property_shapes["comparator"]
    assert prop.enum_term_by_name == {
        "_": Literal("<"),
        "_2": Literal("<="),
        "_3": Literal(">="),
        "_4": Literal(">"),
    }


# --- Relationships ---


def test_build_schema_relationship_field_type(
    relationship_shapes_graph: Graph,
) -> None:
    """``sh:class`` and ``sh:node`` properties map to ``GraphQLObjectType``, not scalars."""
    schema = build_schema(parse_shapes(relationship_shapes_graph))
    person = object_type(schema, "Person")
    company = object_type(schema, "Company")

    assert field_shape(person.fields["employer"].type) == (False, False, "Company")
    assert field_shape(person.fields["address"].type) == (False, False, "Address")
    assert field_shape(company.fields["name"].type) == (True, False, "String")


def test_build_schema_synthetic_shape_iri_only(
    relationship_shapes_graph: Graph,
) -> None:
    """Untargeted ``sh:class`` produces a minimal type with only ``iri`` and no root field."""
    schema = build_schema(parse_shapes(relationship_shapes_graph))
    department = object_type(schema, "Department")

    assert set(department.fields) == {"iri"}
    assert field_shape(department.fields["iri"].type) == (True, False, "ID")

    query = schema.query_type
    assert query is not None
    assert "department" not in query.fields
    assert "person" in query.fields
    assert "company" in query.fields


def test_build_schema_recursive_relationship_type() -> None:
    """Self-referencing relationship types build without error via thunked fields."""
    person = node_shape("Person", property_shapes={})
    knows = relationship_property(
        "knows",
        value_shape_iri=person.iri,
        value_class=EX + "Person",
        min_count=0,
        max_count=None,
    )
    person = shape_with(person, knows=knows)
    schema = build_schema(ShapeRegistry([person]))
    person_type = object_type(schema, "Person")

    assert field_shape(person_type.fields["knows"].type) == (False, True, "Person")


# --- Where argument ---


def test_build_schema_root_field_where_argument() -> None:
    shape = node_shape(
        "Person",
        property_shapes={
            "name": scalar_property("name", min_count=1, max_count=1),
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    query = schema.query_type
    assert query is not None

    person = query.fields["person"]
    assert "where" in person.args
    assert input_field_base(person.args["where"].type) == "PersonFilter"


def test_build_schema_root_field_pagination_arguments() -> None:
    """Root fields expose nullable ``limit`` / ``offset`` with no default (ADR-0010)."""
    shape = node_shape(
        "Person",
        property_shapes={
            "name": scalar_property("name", min_count=1, max_count=1),
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    query = schema.query_type
    assert query is not None

    person = query.fields["person"]
    assert set(person.args) >= {"where", "limit", "offset"}
    assert person.args["limit"].default_value is Undefined
    assert person.args["offset"].default_value is Undefined
    assert person.args["limit"].type.name == "Int"
    assert person.args["offset"].type.name == "Int"


# --- Default resolver ---


async def test_build_schema_default_resolver_returns_empty_list() -> None:
    """The default ``_introspection_resolver`` returns an empty list for root fields."""
    from graphql import graphql

    shape = node_shape(
        "Thing",
        property_shapes={
            "label": scalar_property("label", min_count=1, max_count=1),
        },
    )
    schema = build_schema(ShapeRegistry([shape]))
    result = await graphql(schema, "{ thing { label } }")
    assert result.errors is None
    assert result.data == {"thing": []}
