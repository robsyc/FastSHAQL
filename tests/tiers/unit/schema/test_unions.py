"""Union artifacts in the built schema — ``core/schema/unions.py``
(ADR-0026).

Union-name allocation suffixes against every synthesized type name —
shapes, enums, and earlier unions; the union carries the property's
description; both declaration forms build equivalent unions; polymorphic
fields stay absent from filter inputs until the filter slice.

Order: name allocation → description → members & filter boundary.
"""

from __future__ import annotations

from graphql.type import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLObjectType,
    GraphQLUnionType,
)

from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser import parse_shapes
from fastshaql.core.schema.build import build_schema
from support.builders import POLY_ARTICLE_SHAPES
from support.cases import registry_for


def test_union_name_collision_gets_numeric_suffix() -> None:
    """``{ParentType}{FieldName}`` colliding with a real shape name suffixes
    numerically (the ADR-0006 precedent); the union is introspectable."""
    registry = parse_shapes(
        load_shapes(
            POLY_ARTICLE_SHAPES
            + """
            ex:ArticleBlock a sh:NodeShape ; sh:codeIdentifier "ArticleBlock" ;
                sh:targetClass ex:Block ;
                sh:property [ sh:path ex:label ; sh:datatype xsd:string ] .
            """
        )
    )
    schema = build_schema(registry)
    object_type = schema.get_type("ArticleBlock")
    union = schema.get_type("ArticleBlock2")
    assert isinstance(object_type, GraphQLObjectType)
    assert isinstance(union, GraphQLUnionType)
    assert [t.name for t in union.types] == ["Paragraph", "Image"]


def test_union_name_collision_with_enum_name_gets_numeric_suffix() -> None:
    """An enum type name seeds the taken-set too (``Event.seriesKind`` →
    ``EventSeriesKind`` beside ``EventSeries.kind`` → ``EventSeriesKind``):
    the union suffixes and the schema builds — without enum names in the
    taken-set, two identically named types reach ``GraphQLSchema`` and
    construction crashes."""
    registry = parse_shapes(
        load_shapes(
            POLY_ARTICLE_SHAPES
            + """
            ex:EventSeriesShape a sh:NodeShape ; sh:codeIdentifier "EventSeries" ;
                sh:targetClass ex:EventSeries ;
                sh:property [ sh:path ex:kind ; sh:in ( ex:monthly ex:weekly ) ] .
            ex:EventShape a sh:NodeShape ; sh:codeIdentifier "Event" ;
                sh:targetClass ex:Event ;
                sh:property [ sh:path ex:seriesKind ;
                    sh:or ( [ sh:class ex:Paragraph ] [ sh:class ex:Image ] ) ] .
            """
        )
    )
    schema = build_schema(registry)
    enum_type = schema.get_type("EventSeriesKind")
    union = schema.get_type("EventSeriesKind2")
    assert isinstance(enum_type, GraphQLEnumType)
    assert isinstance(union, GraphQLUnionType)
    assert [t.name for t in union.types] == ["Paragraph", "Image"]


def test_union_vs_union_name_collision_gets_numeric_suffix() -> None:
    """An allocated union name stays taken — a later union whose base name
    collides with an *earlier union's suffixed name* allocates around it
    (the suffix rule re-bases: ``TeamPlayers2`` → ``TeamPlayers22``);
    without the bookkeeping two unions share one name and schema
    construction crashes."""
    registry = parse_shapes(
        load_shapes(
            POLY_ARTICLE_SHAPES
            + """
            ex:TeamPlayersShape a sh:NodeShape ; sh:codeIdentifier "TeamPlayers" ;
                sh:targetClass ex:TeamPlayers ;
                sh:property [ sh:path ex:label ; sh:datatype xsd:string ] .
            ex:TeamShape a sh:NodeShape ; sh:codeIdentifier "Team" ;
                sh:targetClass ex:Team ;
                sh:property [ sh:path ex:players ;
                    sh:or ( [ sh:class ex:Paragraph ] [ sh:class ex:Image ] ) ] ;
                sh:property [ sh:path ex:players2 ;
                    sh:or ( [ sh:class ex:Paragraph ] [ sh:class ex:Image ] ) ] .
            """
        )
    )
    schema = build_schema(registry)
    first = schema.get_type("TeamPlayers2")  # players: base collides with the shape
    second = schema.get_type("TeamPlayers22")  # players2: base collides with first
    assert isinstance(first, GraphQLUnionType)
    assert isinstance(second, GraphQLUnionType)


def test_union_type_carries_the_property_description() -> None:
    """The union's description is the property's ``sh:description`` —
    introspection-visible, like every other synthesized type."""
    registry = parse_shapes(
        load_shapes(
            POLY_ARTICLE_SHAPES
            + """
            ex:TeamShape a sh:NodeShape ; sh:codeIdentifier "Team" ;
                sh:targetClass ex:Team ;
                sh:property [ sh:path ex:players ; sh:description "The players." ;
                    sh:or ( [ sh:class ex:Paragraph ] [ sh:class ex:Image ] ) ] .
            """
        )
    )
    union = build_schema(registry).get_type("TeamPlayers")
    assert isinstance(union, GraphQLUnionType)
    assert union.description == "The players."


def test_filter_inputs_omit_polymorphic_fields() -> None:
    """Polymorphic fields are absent from ``{TypeName}Filter`` until the
    filter slice — the binding union (single-target) stays filterable."""
    registry = registry_for("polymorphic_relationships")
    article_filter = build_schema(registry).get_type("ArticleFilter")
    assert isinstance(article_filter, GraphQLInputObjectType)
    filter_fields = set(article_filter.fields)
    assert {"block", "chunk", "related"}.isdisjoint(filter_fields)
    assert "asset" in filter_fields


def test_both_declaration_forms_build_equivalent_unions() -> None:
    """The ``sh:or`` form (``block``) and the list form (``chunk``) expose
    identical member object types — the equivalence the e2e golden shows in
    values, asserted here at the schema level."""
    registry = registry_for("polymorphic_relationships")
    schema = build_schema(registry)
    block_union = schema.get_type("ArticleBlock")
    chunk_union = schema.get_type("ArticleChunk")
    assert isinstance(block_union, GraphQLUnionType)
    assert isinstance(chunk_union, GraphQLUnionType)
    block_members = [t.name for t in block_union.types]
    chunk_members = [t.name for t in chunk_union.types]
    assert block_members == chunk_members == ["Paragraph", "Image"]
