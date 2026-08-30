"""``sh:path`` parsing — ``core/parser/shacl_path.py``.

Unit tier: predicate path extraction, composite path parsing, and fail-loud
errors for unsupported modifiers and missing ``sh:codeIdentifier``.

Order: predicate path → composite forms → missing path → unsupported modifiers.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef

from fastshaql.core.ir.shacl_path import (
    AlternativePath,
    InversePath,
    OneOrMorePath,
    PredicatePath,
    SequencePath,
    ZeroOrMorePath,
    ZeroOrOnePath,
)
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.shacl_path import (
    MissingShaclPathError,
    UnsupportedShaclPathError,
    parse_shacl_path,
)
from support.builders import EX


def _graph_with_path(turtle: str) -> tuple[Graph, URIRef]:
    return load_shapes(turtle), URIRef("http://example.org/prop")


# --- Predicate path ---


def test_parse_predicate_path() -> None:
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path ex:label .
        """
    )
    path = parse_shacl_path(graph, prop)
    assert isinstance(path, PredicatePath)
    assert path.iri == EX + "label"


# --- Composite forms ---


def test_parse_inverse_path() -> None:
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path [ sh:inversePath ex:parent ] .
        """
    )
    path = parse_shacl_path(graph, prop)
    assert isinstance(path, InversePath)
    assert isinstance(path.path, PredicatePath)
    assert path.path.iri == EX + "parent"


def test_parse_sequence_path() -> None:
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path ( ex:employer ex:locatedIn ) .
        """
    )
    path = parse_shacl_path(graph, prop)
    assert isinstance(path, SequencePath)
    assert len(path.elements) == 2
    first, second = path.elements
    assert isinstance(first, PredicatePath)
    assert isinstance(second, PredicatePath)
    assert first.iri == EX + "employer"
    assert second.iri == EX + "locatedIn"


def test_parse_alternative_path() -> None:
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path [ sh:alternativePath ( ex:spouse ex:partner ) ] .
        """
    )
    path = parse_shacl_path(graph, prop)
    assert isinstance(path, AlternativePath)
    assert len(path.alternatives) == 2
    spouse, partner = path.alternatives
    assert isinstance(spouse, PredicatePath)
    assert isinstance(partner, PredicatePath)
    assert spouse.iri == EX + "spouse"
    assert partner.iri == EX + "partner"


def test_parse_deeply_nested_path() -> None:
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path [
                sh:inversePath [
                    sh:alternativePath ( ex:a ex:b )
                ]
            ] .
        """
    )
    path = parse_shacl_path(graph, prop)
    assert isinstance(path, InversePath)
    assert isinstance(path.path, AlternativePath)


# --- Missing path ---


def test_missing_path_raises() -> None:
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape .
        """
    )
    with pytest.raises(MissingShaclPathError, match="no sh:path"):
        parse_shacl_path(graph, prop)


# --- Cardinality modifiers (sh:zeroOrMorePath / sh:oneOrMorePath / sh:zeroOrOnePath) ---


@pytest.mark.parametrize(
    ("turtle", "expected_type"),
    [
        (
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            ex:prop a sh:PropertyShape ;
                sh:path [ sh:zeroOrMorePath ex:parent ] .
            """,
            ZeroOrMorePath,
        ),
        (
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            ex:prop a sh:PropertyShape ;
                sh:path [ sh:oneOrMorePath ex:parent ] .
            """,
            OneOrMorePath,
        ),
        (
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            ex:prop a sh:PropertyShape ;
                sh:path [ sh:zeroOrOnePath ex:parent ] .
            """,
            ZeroOrOnePath,
        ),
    ],
)
def test_parse_modifier_path(turtle: str, expected_type: type) -> None:
    graph, prop = _graph_with_path(turtle)
    path = parse_shacl_path(graph, prop)
    assert isinstance(path, expected_type)
    # Narrow to the modifier union (all share ``.path``) so the operand is reachable.
    assert isinstance(path, (ZeroOrMorePath, OneOrMorePath, ZeroOrOnePath))
    assert isinstance(path.path, PredicatePath)
    assert path.path.iri == EX + "parent"


def test_parse_modifier_wraps_composite_child() -> None:
    # sh:oneOrMorePath over an inverse path — recurses through the modifier.
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path [ sh:zeroOrMorePath [ sh:inversePath ex:parent ] ] .
        """
    )
    path = parse_shacl_path(graph, prop)
    assert isinstance(path, ZeroOrMorePath)
    assert isinstance(path.path, InversePath)
    assert isinstance(path.path.path, PredicatePath)


def test_composite_path_requires_code_identifier() -> None:
    from fastshaql.core.parser import parse_shapes
    from fastshaql.core.parser.util import MissingCompositePathCodeIdentifierError

    graph = Graph()
    graph.parse(
        data="""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:ThingShape a sh:NodeShape ;
            sh:targetClass ex:Thing ;
            sh:property [
                a sh:PropertyShape ;
                sh:path ( ex:a ex:b ) ;
                sh:datatype <http://www.w3.org/2001/XMLSchema#string> ;
                sh:minCount 1 ;
            ] .
        """,
        format="turtle",
    )
    with pytest.raises(
        MissingCompositePathCodeIdentifierError, match="sh:codeIdentifier"
    ):
        parse_shapes(graph)


def test_composite_path_parses_with_code_identifier() -> None:
    from fastshaql.core.parser import parse_shapes

    graph = Graph()
    graph.parse(
        data="""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:property [
                a sh:PropertyShape ;
                sh:codeIdentifier "abPath" ;
                sh:path ( ex:a ex:b ) ;
                sh:datatype <http://www.w3.org/2001/XMLSchema#string> ;
                sh:minCount 1 ;
            ] .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    shape = registry.by_type_name["Thing"]
    prop = shape.property_shapes["abPath"]
    assert isinstance(prop.path, SequencePath)


# --- Empty / malformed composite paths ---


def test_empty_alternative_path_raises() -> None:
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path [ sh:alternativePath () ] .
        """
    )
    with pytest.raises(UnsupportedShaclPathError, match="Empty"):
        parse_shacl_path(graph, prop)


def test_unrecognized_path_structure_raises() -> None:
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path [ ex:unknown "value" ] .
        """
    )
    with pytest.raises(UnsupportedShaclPathError, match="Unrecognized"):
        parse_shacl_path(graph, prop)
