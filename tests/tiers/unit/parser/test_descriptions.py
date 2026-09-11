"""Shape and property descriptions — rdfs:comment/rdfs:label language selection.

Tests parse node-shape descriptions (``rdfs:comment`` with ``rdfs:label``
fallback) and property-shape descriptions (``sh:description`` with
``sh:name`` fallback), plus the ``description_language`` preference and its
default-English contract (ADR-0007).

Order: node descriptions → language selection → property descriptions → description_language wiring and defaults.
"""

from __future__ import annotations

import pytest
from rdflib import Graph

from fastshaql.core.parser import parse_shapes
from fastshaql.core.parser.node_shape import parse_node_shape
from fastshaql.core.parser.property_shape import parse_property_shape
from support.builders import EX


def _shapes_graph(turtle: str) -> Graph:
    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    return graph


# --- rdfs:comment / rdfs:label description ---


def test_node_shape_description_from_rdfs_comment() -> None:
    """``rdfs:comment`` on a node shape populates ``description``."""
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
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.description == "A thing."


def test_node_shape_description_falls_back_to_rdfs_label() -> None:
    """``rdfs:label`` is used when ``rdfs:comment`` is absent."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:label "ThingLabel" .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.description == "ThingLabel"


@pytest.mark.parametrize(
    ("turtle_extra", "expected"),
    [
        ('rdfs:comment "Une chose."@fr , "A thing."@en', "A thing."),
        ('rdfs:comment "Plain text." , "Autre"@fr', "Plain text."),
        ('rdfs:comment "Bonjour"@fr', "Bonjour"),
        ('rdfs:comment "US English"@en-US', "US English"),
        ('rdfs:label "Thing label"@en', "Thing label"),
    ],
    ids=[
        "preferred_lang",
        "untagged_over_foreign",
        "any_lang_fallback",
        "rfc4647_basic",
        "predicate_fallback",
    ],
)
def test_node_shape_description_language_selection_wired(
    turtle_extra: str,
    expected: str,
) -> None:
    """Language selection flows through ``parse_shapes`` (matrix in ``test_graph_reads``)."""
    graph = Graph()
    graph.parse(
        data=f"""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            {turtle_extra} .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.description == expected


def test_parse_shapes_description_language_parameter() -> None:
    """``description_language`` selects a non-default preferred language."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "A thing."@en , "Ein Ding."@de .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph, description_language="de")
    thing = registry.by_type_name["Thing"]
    assert thing.description == "Ein Ding."


def test_property_shape_description_language_selection() -> None:
    """Property shapes apply the same language preference to ``sh:description``."""
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
                sh:description "Étiquette"@fr , "Label"@en
            ] .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.property_shapes["label"].description == "Label"


def test_property_shape_description_falls_back_to_sh_name() -> None:
    """``sh:name`` supplies the property description when ``sh:description`` is absent."""
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
                sh:name "Display name"@en
            ] .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.property_shapes["label"].description == "Display name"


def test_node_shape_description_predicate_priority_over_language() -> None:
    """A foreign-language ``rdfs:comment`` beats a preferred-language ``rdfs:label``."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "Commentaire"@fr ;
            rdfs:label "English label"@en .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.description == "Commentaire"


# --- description_language wiring and defaults ---


def test_description_language_reaches_property_shapes() -> None:
    """``description_language`` flows through the node shape into every
    property shape's own description read (ADR-0007)."""
    graph = _shapes_graph(
        """
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:property [
                sh:path ex:note ;
                sh:datatype xsd:string ;
                sh:description "A label."@en , "Ein Etikett."@de ;
            ] .
        """
    )
    note = parse_shapes(graph, description_language="de").by_type_name["Thing"]
    assert note.property_shapes["note"].description == "Ein Etikett."


def test_node_description_defaults_to_english() -> None:
    """The ``description_language`` default (``"en"``) is contract: without an
    override, a shape with ``de``/``en`` descriptions reads the English one
    (ADR-0007) — the lexical fallback would pick ``de``."""
    graph = _shapes_graph(
        """
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "Hello"@en , "Hallo"@de .
        """
    )
    shape = parse_node_shape(graph, EX + "ThingShape")
    assert shape.description == "Hello"


def test_property_description_defaults_to_english() -> None:
    """Same default at the property level: a directly parsed property shape
    without a language override reads the English description."""
    graph = _shapes_graph(
        """
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

        ex:noteShape a sh:PropertyShape ;
            sh:path ex:note ;
            sh:datatype xsd:string ;
            sh:description "A label."@en , "Ein Etikett."@de .
        """
    )
    parsed = parse_property_shape(
        graph, EX + "noteShape", parent_graphql_type_name="Thing"
    )
    assert parsed is not None
    assert parsed.description == "A label."


def test_parse_shapes_description_language_default_is_english() -> None:
    """The facade-level default (``"en"``) is contract, matching the
    node/property-level defaults: ``parse_shapes`` without an override reads
    the English description (ADR-0007) — the lexical fallback would pick
    ``de``."""
    graph = _shapes_graph(
        """
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "Hello"@en , "Hallo"@de .
        """
    )
    registry = parse_shapes(graph)
    assert registry.by_type_name["Thing"].description == "Hello"
