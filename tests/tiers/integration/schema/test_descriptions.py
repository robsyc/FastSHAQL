"""Schema descriptions — SHACL §8 text wired to graphql-core ``description``.

Integration tier: ``build_schema`` propagates IR ``description`` to object types,
property fields, and root query fields only (synthetics stay ``None``).
"""

from __future__ import annotations

from rdflib import Graph

from fastshaql.core.parser import parse_shapes
from fastshaql.core.schema import build_schema
from support.schema_helpers import object_type


def test_build_schema_shape_description_from_rdfs_comment() -> None:
    """Node-shape ``rdfs:comment`` appears on the GraphQL object type."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "A thing." .
        """,
        format="turtle",
    )
    schema = build_schema(parse_shapes(graph))
    thing = object_type(schema, "Thing")
    assert thing.description == "A thing."


def test_build_schema_property_description_from_sh_description() -> None:
    """Property-shape ``sh:description`` appears on the GraphQL field."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:description "Human-readable label."
            ] .
        """,
        format="turtle",
    )
    schema = build_schema(parse_shapes(graph))
    thing = object_type(schema, "Thing")
    assert thing.fields["label"].description == "Human-readable label."


def test_build_schema_root_field_description() -> None:
    """Root query field carries the shape description."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "A thing." .
        """,
        format="turtle",
    )
    schema = build_schema(parse_shapes(graph))
    query = schema.query_type
    assert query is not None
    assert query.fields["thing"].description == "A thing."


def test_build_schema_absent_description_is_none() -> None:
    """Shapes and fields without SHACL description text stay ``None``."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1
            ] .
        """,
        format="turtle",
    )
    schema = build_schema(parse_shapes(graph))
    query = schema.query_type
    assert query is not None
    thing = object_type(schema, "Thing")

    assert thing.description is None
    assert thing.fields["label"].description is None
    assert thing.fields["iri"].description is None
    assert query.fields["thing"].description is None


def test_build_schema_description_end_to_end_with_language_tag() -> None:
    """Language-selected IR description flows through to GraphQL ``description``."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "Une chose."@fr , "A thing."@en ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:description "Étiquette"@fr , "Label"@en
            ] .
        """,
        format="turtle",
    )
    schema = build_schema(parse_shapes(graph))
    query = schema.query_type
    assert query is not None
    thing = object_type(schema, "Thing")

    assert thing.description == "A thing."
    assert thing.fields["label"].description == "Label"
    assert query.fields["thing"].description == "A thing."


def test_build_schema_description_language_parameter_end_to_end() -> None:
    """``parse_shapes(description_language=)`` flows through to GraphQL ``description``."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "A thing."@en , "Une chose."@fr .
        """,
        format="turtle",
    )
    schema = build_schema(parse_shapes(graph, description_language="fr"))
    thing = object_type(schema, "Thing")
    query = schema.query_type
    assert query is not None

    assert thing.description == "Une chose."
    assert query.fields["thing"].description == "Une chose."
