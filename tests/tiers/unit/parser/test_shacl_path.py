"""``sh:path`` parsing — ``core/parser/shacl_path.py``.

Unit tier: predicate path extraction, composite path parsing, and fail-loud
errors for unsupported modifiers, missing ``sh:codeIdentifier``, and §4
well-formedness violations (empty/single-member lists, cycles, multiple
``sh:path`` values).

Order: predicate path → composite forms → missing path → unsupported modifiers → well-formedness rejections.
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
from fastshaql.core.parser.errors import UnsupportedShapeError
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
    """§4.3: an alternative list carries at least two members — the empty list rejects."""
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path [ sh:alternativePath () ] .
        """
    )
    with pytest.raises(UnsupportedShaclPathError, match="at least two members"):
        parse_shacl_path(graph, prop)


def test_empty_sequence_path_raises() -> None:
    """``sh:path ()`` is ``rdf:nil``, an IRI — without the dedicated check the
    predicate branch would win and silently parse a ``nil`` field."""
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path () .
        """
    )
    with pytest.raises(UnsupportedShaclPathError, match="Empty sh:path"):
        parse_shacl_path(graph, prop)


@pytest.mark.parametrize(
    "path_object",
    ["( ex:spouse )", "[ sh:alternativePath ( ex:spouse ) ]"],
    ids=["sequence", "alternative"],
)
def test_single_member_path_list_raises(path_object: str) -> None:
    """§4.2/§4.3: sequence and alternative lists carry at least two members —
    the degenerate single-member form is not a valid path."""
    graph, prop = _graph_with_path(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path {path_object} .
        """
    )
    with pytest.raises(UnsupportedShaclPathError, match="at least two members"):
        parse_shacl_path(graph, prop)


def test_multiple_sh_path_values_raise() -> None:
    """§3.3: a shape has at most one ``sh:path`` — an arbitrary pick would be
    a nondeterminism source."""
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path ex:label , ex:name .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="Multiple sh:path values"):
        parse_shacl_path(graph, prop)


@pytest.mark.parametrize(
    "turtle",
    [
        # An alternative host referenced from its own member list.
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path _:cycle .
        _:cycle sh:alternativePath ( _:cycle ex:a ) .
        """,
        # An inverse path whose operand is its own host.
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path _:cycle .
        _:cycle sh:inversePath _:cycle .
        """,
    ],
    ids=["alternative_member", "inverse_operand"],
)
def test_cyclic_path_raises(turtle: str) -> None:
    """§4: a blank-node path referencing itself is ill-formed — rejects here
    instead of recursing to a ``RecursionError``."""
    graph, prop = _graph_with_path(turtle)
    with pytest.raises(UnsupportedShaclPathError, match="Cyclic property path"):
        parse_shacl_path(graph, prop)


def test_multiple_path_predicates_on_node_raise() -> None:
    """§4: a path node satisfies exactly one syntax rule — no check-order pick."""
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path [ sh:inversePath ex:a ; sh:alternativePath ( ex:b ex:c ) ] .
        """
    )
    with pytest.raises(UnsupportedShaclPathError, match="exactly one syntax rule"):
        parse_shacl_path(graph, prop)


def test_multiple_inverse_path_values_raise() -> None:
    """§4.4: a wrapper node is the subject of exactly one triple."""
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:path [ sh:inversePath ex:a , ex:b ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="Multiple sh:inversePath"):
        parse_shacl_path(graph, prop)


def test_malformed_sequence_list_raises() -> None:
    """A cons cell without ``rdf:rest`` is not a well-formed SHACL list — the
    strict walk rejects it (the lenient walk would silently return one
    member)."""
    graph, prop = _graph_with_path(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        ex:prop a sh:PropertyShape ;
            sh:path [ rdf:first ex:a ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match="exactly one rdf:first and one rdf:rest"
    ):
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
