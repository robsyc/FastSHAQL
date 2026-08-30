"""``sh:prefixes`` resolution and prefix expansion — ``core/parser/node_expr/shacl_prefixes.py``.

Unit tier: ``parse_shacl_prefixes`` (SHACL-SPARQL §2.2.1 ``sh:declare`` → map,
including the ``prefixes-duplicates`` ill-formed rule) and
``expand_sparql_prefixes`` (expand-at-parse, ADR-0015), whose protected-region
guarantee (string literals, IRIREFs, comments never scanned) rests on the
``core/sparql/lex`` token regexes.

Order: parse (resolution + duplicate conflict) → expand (protected regions,
PN_LOCAL [190] shapes, unknown-prefix passthrough).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rdflib import Graph, URIRef

from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.node_expr import UnsupportedShapeError
from fastshaql.core.parser.node_expr.shacl_prefixes import (
    expand_sparql_prefixes,
    parse_shacl_prefixes,
)

if TYPE_CHECKING:
    from rdflib.term import Node

_SH_VALUES = URIRef("http://www.w3.org/ns/shacl#values")
_EX = "http://example.org/"
_DEMO = "http://example.org/demo/"


def _values_node(turtle: str) -> tuple[Graph, Node]:
    graph = load_shapes(turtle)
    prop = URIRef(_EX + "prop")
    node = graph.value(prop, _SH_VALUES)
    assert node is not None
    return graph, node


# --- parse_shacl_prefixes: resolution ---


def test_parse_shacl_prefixes_absent_returns_empty() -> None:
    graph, node = _values_node(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ sh:sparqlExpr "STRLEN(STR($this))" ] .
        """
    )
    assert parse_shacl_prefixes(graph, node) == {}


def test_parse_shacl_prefixes_from_named_iri_target() -> None:
    graph, node = _values_node(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:shapes a sh:ShapesGraph ;
            sh:declare [
                sh:prefix "demo" ;
                sh:namespace "http://example.org/demo/" ;
            ] .
        ex:prop a sh:PropertyShape ;
            sh:values [
                sh:prefixes ex:shapes ;
                sh:sparqlExpr "demo:foo" ;
            ] .
        """
    )
    assert parse_shacl_prefixes(graph, node) == {"demo": _DEMO}


def test_parse_shacl_prefixes_from_multiple_declarations() -> None:
    graph, node = _values_node(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                sh:prefixes [
                    sh:declare [
                        sh:prefix "demo" ;
                        sh:namespace "http://example.org/demo/" ;
                    ] ;
                    sh:declare [
                        sh:prefix "xsd" ;
                        sh:namespace "http://www.w3.org/2001/XMLSchema#" ;
                    ] ;
                ] ;
                sh:sparqlExpr "demo:foo" ;
            ] .
        """
    )
    assert parse_shacl_prefixes(graph, node) == {
        "demo": _DEMO,
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }


def test_parse_shacl_prefixes_identical_redeclaration_ok() -> None:
    graph, node = _values_node(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                sh:prefixes [
                    sh:declare [
                        sh:prefix "demo" ;
                        sh:namespace "http://example.org/demo/" ;
                    ] ;
                    sh:declare [
                        sh:prefix "demo" ;
                        sh:namespace "http://example.org/demo/" ;
                    ] ;
                ] ;
                sh:sparqlExpr "demo:foo" ;
            ] .
        """
    )
    assert parse_shacl_prefixes(graph, node) == {"demo": _DEMO}


def test_parse_shacl_prefixes_skips_incomplete_declaration() -> None:
    # A ``sh:declare`` node missing ``sh:prefix`` or ``sh:namespace`` is not a
    # usable declaration — it contributes nothing instead of poisoning the map.
    graph, node = _values_node(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                sh:prefixes [
                    sh:declare [
                        sh:prefix "demo" ;
                    ] ;
                    sh:declare [
                        sh:prefix "xsd" ;
                        sh:namespace "http://www.w3.org/2001/XMLSchema#" ;
                    ] ;
                ] ;
                sh:sparqlExpr "xsd:foo" ;
            ] .
        """
    )
    assert parse_shacl_prefixes(graph, node) == {
        "xsd": "http://www.w3.org/2001/XMLSchema#"
    }


# --- parse_shacl_prefixes: prefixes-duplicates (SHACL-SPARQL §2.2.1) ---


def test_parse_shacl_prefixes_conflicting_namespaces_raises() -> None:
    graph, node = _values_node(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                sh:prefixes [
                    sh:declare [
                        sh:prefix "demo" ;
                        sh:namespace "http://example.org/a/" ;
                    ] ;
                    sh:declare [
                        sh:prefix "demo" ;
                        sh:namespace "http://example.org/b/" ;
                    ] ;
                ] ;
                sh:sparqlExpr "demo:foo" ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="conflicting namespaces"):
        parse_shacl_prefixes(graph, node)


# --- expand_sparql_prefixes: protected regions (never scanned) ---


def test_expand_sparql_prefixes_leaves_unknown_prefix() -> None:
    text = "EXISTS { $this unknown:foo ?g }"
    assert expand_sparql_prefixes(text, {"demo": _DEMO}) == text


def test_expand_sparql_prefixes_leaves_double_quoted_string_literal() -> None:
    # SPARQL 1.2 [177] STRING_LITERAL2 — the prefix-looking span is a literal value.
    text = 'BIND( "demo:foo" AS ?x )'
    assert expand_sparql_prefixes(text, {"demo": _DEMO}) == text


def test_expand_sparql_prefixes_leaves_single_quoted_string_literal() -> None:
    # SPARQL 1.2 [176] STRING_LITERAL1.
    text = "BIND( 'demo:foo' AS ?x )"
    assert expand_sparql_prefixes(text, {"demo": _DEMO}) == text


def test_expand_sparql_prefixes_leaves_long_string_literal() -> None:
    # SPARQL 1.2 [179] STRING_LITERAL_LONG2 — also exercises long-before-short order.
    text = 'BIND( """demo:foo""" AS ?x )'
    assert expand_sparql_prefixes(text, {"demo": _DEMO}) == text


def test_expand_sparql_prefixes_leaves_iriref() -> None:
    # SPARQL 1.2 [159] IRIREF — a prefix-looking span inside <...> must not be
    # re-expanded into a nested <...<...>...>.
    text = "BIND( <http://example.org/demo:bar> AS ?x )"
    assert expand_sparql_prefixes(text, {"demo": _DEMO}) == text


def test_expand_sparql_prefixes_leaves_comment() -> None:
    # SPARQL 1.2 §19.4 — '#' to end of line is inert; the code-position prefix
    # before it is still expanded.
    text = "demo:foo # remember demo:bar\n"
    assert expand_sparql_prefixes(text, {"demo": _DEMO}) == (
        "<http://example.org/demo/foo> # remember demo:bar\n"
    )


def test_expand_sparql_prefixes_protects_regions_but_expands_code() -> None:
    # Integration: protected regions are skipped while a bare code-position
    # prefixed name is expanded. The IRIREF is protected, so its internal
    # ``demo:also_skip`` passes through unchanged (cf. leaves_iriref).
    text = 'BIND( "demo:skip" AS ?x ) demo:keep <http://example.org/demo:also_skip>'
    expected = (
        'BIND( "demo:skip" AS ?x ) '
        "<http://example.org/demo/keep> "
        "<http://example.org/demo:also_skip>"
    )
    assert expand_sparql_prefixes(text, {"demo": _DEMO}) == expected


# --- expand_sparql_prefixes: PN_LOCAL [190] shapes ---


def test_expand_sparql_prefixes_dot_in_local_part() -> None:
    # [190] PN_LOCAL permits internal ``.`` — a single prefixed name
    # ``ex:foo.bar`` must expand to one IRI, not be split at the dot.
    assert (
        expand_sparql_prefixes("$this ex:foo.bar ?v", {"ex": _EX})
        == "$this <http://example.org/foo.bar> ?v"
    )


def test_expand_sparql_prefixes_chained_dots_in_local_part() -> None:
    assert (
        expand_sparql_prefixes("ex:a.b.c", {"ex": _EX}) == "<http://example.org/a.b.c>"
    )


def test_expand_sparql_prefixes_colon_in_local_part() -> None:
    # [190] PN_LOCAL also permits internal ``:``.
    assert (
        expand_sparql_prefixes("ex:foo:bar", {"ex": _EX})
        == "<http://example.org/foo:bar>"
    )


def test_expand_sparql_prefixes_percent_escape_in_local_part() -> None:
    # [190] PN_LOCAL admits PLX (``%XX``). Without the PLX arm the local name is
    # truncated at ``%`` and the residue corrupts the IRI (``<…a>%2Fb``). ``%``
    # is valid IRI percent-encoding, so it is preserved verbatim.
    assert (
        expand_sparql_prefixes("ex:a%2Fb", {"ex": _EX}) == "<http://example.org/a%2Fb>"
    )


def test_expand_sparql_prefixes_non_ascii_local_part() -> None:
    # ``\w`` is Unicode, so non-ASCII PN_CHARS_BASE letters expand whole. A miss
    # would leave a bare prefixed name — and the emitted query has no PREFIX
    # block (ADR-0015 expand-at-parse), so the store could not resolve it.
    assert expand_sparql_prefixes("ex:café", {"ex": _EX}) == "<http://example.org/café>"


def test_expand_sparql_prefixes_trailing_dot_not_consumed() -> None:
    # [190] forbids a trailing ``.`` — it is the statement terminator, not part
    # of the local name, so expansion stops before it.
    assert (
        expand_sparql_prefixes("?this ex:foo. ?x", {"ex": _EX})
        == "?this <http://example.org/foo>. ?x"
    )
