"""``sh:in`` parsing — ``core/parser/shacl_in.py``.

Unit tier: homogeneous value lists and fail-loud errors for unsupported
``sh:in`` shapes. Mangled-name collisions are not a parser concern — the
parser is name-agnostic (suffixing lives in ``identifiers.enum_member_names``).

Order: homogeneous value lists → fail-loud errors → duplicate-member warning → relationship-overlay warning.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.errors import UnsupportedShapeError
from fastshaql.core.parser.shacl_in import UnsupportedShaclInError, parse_shacl_in


def _graph_with_in(turtle: str) -> tuple[Graph, URIRef]:
    return load_shapes(turtle), URIRef("http://example.org/prop")


def test_parse_literal_enum_list() -> None:
    graph, prop = _graph_with_in(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:in ("active" "inactive") .
        """
    )
    assert parse_shacl_in(graph, prop) == (Literal("active"), Literal("inactive"))


def test_parse_iri_enum_list() -> None:
    graph, prop = _graph_with_in(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:in ( ex:Pink ex:Purple ) .
        """
    )
    assert parse_shacl_in(graph, prop) == (
        URIRef("http://example.org/Pink"),
        URIRef("http://example.org/Purple"),
    )


def test_mixed_literal_and_iri_raises() -> None:
    graph, prop = _graph_with_in(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:in ( "active" ex:Pink ) .
        """
    )
    with pytest.raises(UnsupportedShaclInError, match="mixes literals and IRIs"):
        parse_shacl_in(graph, prop)


def test_malformed_list_raises() -> None:
    """A cons cell without ``rdf:rest`` is not a well-formed SHACL list —
    the strict walk rejects it instead of silently truncating."""
    graph, prop = _graph_with_in(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        ex:prop a sh:PropertyShape ;
            sh:in [ rdf:first "active" ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match="exactly one rdf:first and one rdf:rest"
    ):
        parse_shacl_in(graph, prop)


def test_blank_node_member_raises() -> None:
    graph, prop = _graph_with_in(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:in ( _:b1 ) .
        _:b1 ex:label "bad" .
        """
    )
    with pytest.raises(UnsupportedShaclInError, match="blank node"):
        parse_shacl_in(graph, prop)


def test_duplicate_sh_in_raises() -> None:
    graph, prop = _graph_with_in(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:in ("a") ;
            sh:in ("b") .
        """
    )
    with pytest.raises(UnsupportedShaclInError, match="more than one sh:in"):
        parse_shacl_in(graph, prop)


def test_mangle_collision_parses() -> None:
    """Members colliding after mangling no longer raise — disambiguated with
    numeric suffixes downstream (``identifiers.enum_member_names``)."""
    graph, prop = _graph_with_in(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:in ("foo-bar" "foo_bar") .
        """
    )
    assert parse_shacl_in(graph, prop) == (
        Literal("foo-bar"),
        Literal("foo_bar"),
    )


def test_duplicate_members_warn_but_parse(caplog: pytest.LogCaptureFixture) -> None:
    """Duplicate terms are SHACL-legal — parse proceeds, one warning per shape."""
    graph, prop = _graph_with_in(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:in ( "<" "<" ) .
        """
    )
    with caplog.at_level("WARNING", logger="fastshaql.core.parser.shacl_in"):
        assert parse_shacl_in(graph, prop) == (Literal("<"), Literal("<"))
    duplicates = [r for r in caplog.records if "Duplicate sh:in" in r.message]
    assert len(duplicates) == 1
    assert '"<"' in duplicates[0].message


def test_relationship_overlay_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    from fastshaql.core.parser import parse_shapes

    graph = Graph()
    graph.parse(
        data="""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:acme a ex:Company .
        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:employer ;
                sh:class ex:Company ;
                sh:in ( ex:acme ) ;
            ] .
        """,
        format="turtle",
    )
    with caplog.at_level("WARNING"):
        parse_shapes(graph)
    overlay = [r for r in caplog.records if "Relationship-overlay sh:in" in r.message]
    assert len(overlay) == 1
    assert "employer" in overlay[0].message


def test_empty_sh_in_list_returns_empty_tuple() -> None:
    """An empty ``sh:in ()`` is a present-but-empty value set — distinct from
    no ``sh:in`` (``None``); the caller excludes such a field."""
    graph, prop = _graph_with_in(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:in () .
        """
    )
    assert parse_shacl_in(graph, prop) == ()
