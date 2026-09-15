"""Enum type-name allocation in the built schema — the ADR-0006 suffix rule
applied to ``{ParentType}{FieldName}`` collisions.

Enum-lane collisions across the name-allocation taken-set's load-bearing
seeds: two synthesized names agreeing across (parent, field) pairs, a
synthesized name landing on a shape's type name, on a shape's
``{Type}Filter`` input name, or an enum *filter* input landing on an
operator input name — one side suffixes, both resolve, the schema builds.
(The ``Query`` seed entry is unreachable by any synthesized name — see
docs/mutation-triage.md.)

Order: enum-vs-enum → enum-vs-shape → enum-vs-filter-input →
enum-filter-vs-operator-input.
"""

from __future__ import annotations

from graphql.type import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLObjectType,
)

from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser import parse_shapes
from fastshaql.core.schema.build import build_schema
from support.builders import POLY_ARTICLE_SHAPES


def test_enum_name_collision_with_enum_name_gets_numeric_suffix() -> None:
    """Two ``{ParentType}{FieldName}`` concatenations agreeing across
    (parent, field) pairs (``EventSeries.kind`` vs ``Event.seriesKind``)
    collide within the enum lane itself: one suffixes instead of silently
    shadowing — both fields resolve to their own type, the schema builds.
    Which one suffixes follows registry order (deterministic per shapes
    graph); the assertion is pairing-based, not order-based."""
    registry = parse_shapes(
        load_shapes(
            POLY_ARTICLE_SHAPES
            + """
            ex:EventSeriesShape a sh:NodeShape ; sh:codeIdentifier "EventSeries" ;
                sh:targetClass ex:EventSeries ;
                sh:property [ sh:path ex:kind ; sh:in ( ex:monthly ex:weekly ) ] .
            ex:EventShape a sh:NodeShape ; sh:codeIdentifier "Event" ;
                sh:targetClass ex:Event ;
                sh:property [ sh:path ex:seriesKind ; sh:in ( ex:main ex:fringe ) ] .
            """
        )
    )
    schema = build_schema(registry)
    base = schema.get_type("EventSeriesKind")
    suffixed = schema.get_type("EventSeriesKind2")
    series = schema.get_type("EventSeries")
    event = schema.get_type("Event")
    assert isinstance(base, GraphQLEnumType)
    assert isinstance(suffixed, GraphQLEnumType)
    assert isinstance(series, GraphQLObjectType)
    assert isinstance(event, GraphQLObjectType)
    by_values = {tuple(t.values): t for t in (base, suffixed)}
    assert (
        series.fields["kind"].type.of_type.of_type is by_values[("MONTHLY", "WEEKLY")]
    )
    assert (
        event.fields["seriesKind"].type.of_type.of_type is by_values[("MAIN", "FRINGE")]
    )


def test_enum_name_collision_with_shape_name_gets_numeric_suffix() -> None:
    """An enum whose synthesized name equals a shape's type name suffixes —
    the shape keeps its name, the enum allocates around it."""
    registry = parse_shapes(
        load_shapes(
            POLY_ARTICLE_SHAPES
            + """
            ex:EventSeriesKindShape a sh:NodeShape ; sh:codeIdentifier "EventSeriesKind" ;
                sh:targetClass ex:EventSeriesKind ;
                sh:property [ sh:path ex:label ;
                    sh:datatype xsd:string ] .
            ex:EventSeriesShape a sh:NodeShape ; sh:codeIdentifier "EventSeries" ;
                sh:targetClass ex:EventSeries ;
                sh:property [ sh:path ex:kind ; sh:in ( ex:monthly ex:weekly ) ] .
            """
        )
    )
    schema = build_schema(registry)
    shape_type = schema.get_type("EventSeriesKind")
    enum_type = schema.get_type("EventSeriesKind2")
    assert isinstance(shape_type, GraphQLObjectType)
    assert isinstance(enum_type, GraphQLEnumType)
    assert list(enum_type.values) == ["MONTHLY", "WEEKLY"]


def test_enum_name_collision_with_filter_input_name_gets_numeric_suffix() -> None:
    """Every shape's ``{Type}Filter`` input name seeds the taken-set — an
    enum landing on its own shape's filter input allocates around it."""
    registry = parse_shapes(
        load_shapes(
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            ex:PersonShape a sh:NodeShape ; sh:codeIdentifier "Person" ;
                sh:targetClass ex:Person ;
                sh:property [ sh:path ex:filter ; sh:in ( ex:a ex:b ) ] ;
                sh:property [ sh:path ex:name ; sh:datatype xsd:string ] .
            """
        )
    )
    schema = build_schema(registry)
    filter_input = schema.get_type("PersonFilter")
    enum_type = schema.get_type("PersonFilter2")
    assert isinstance(filter_input, GraphQLInputObjectType)
    assert isinstance(enum_type, GraphQLEnumType)
    assert list(enum_type.values) == ["A", "B"]


def test_enum_filter_name_collision_with_operator_input_name_gets_numeric_suffix() -> (
    None
):
    """An enum *filter* input landing on an operator input name
    (``Date.time`` → enum ``DateTime`` → ``DateTimeFilter``) allocates
    around it — the operator inputs seed the taken-set too."""
    registry = parse_shapes(
        load_shapes(
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            ex:DateShape a sh:NodeShape ; sh:codeIdentifier "Date" ;
                sh:targetClass ex:Date ;
                sh:property [ sh:path ex:time ; sh:in ( ex:morning ex:evening ) ] .
            """
        )
    )
    schema = build_schema(registry)
    operator_input = schema.get_type("DateTimeFilter")
    enum_filter = schema.get_type("DateTimeFilter2")
    assert isinstance(operator_input, GraphQLInputObjectType)
    assert isinstance(enum_filter, GraphQLInputObjectType)
    # The right side keeps the base name: the scalar's operator input owns
    # the range operators, the enum's filter is equality-only.
    assert {"gt", "gte", "lt", "lte"} <= set(operator_input.fields)
    assert not {"gt", "gte", "lt", "lte"} & set(enum_filter.fields)
