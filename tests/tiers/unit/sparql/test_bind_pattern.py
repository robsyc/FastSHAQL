"""BIND and raw trusted-text SPARQL nodes — ``core/sparql/patterns.py`` / ``expressions.py``.

Unit tier: ``BindPattern``, ``RawGraphPattern``, and ``RawSparqlExpr`` render goldens
(ADR-0015 / ADR-0017 trusted-author escape tier).

Order: BindPattern → RawSparqlExpr → RawGraphPattern.
"""

from __future__ import annotations

from rdflib import Literal, Variable
from rdflib.namespace import XSD

from fastshaql.core.sparql import (
    BindPattern,
    GroupPattern,
    RawGraphPattern,
    RawSparqlExpr,
    TermExpr,
)


def test_bind_pattern_renders_term_expr() -> None:
    bind = BindPattern(
        TermExpr(Literal("FastshaqlEMR", datatype=XSD.string)),
        Variable("recordSource"),
    )
    assert (
        bind.render()
        == 'BIND("FastshaqlEMR"^^<http://www.w3.org/2001/XMLSchema#string> AS ?recordSource)'
    )


def test_bind_pattern_renders_indented_in_group() -> None:
    bind = BindPattern(
        TermExpr(Literal("FastshaqlEMR")),
        Variable("recordSource"),
    )
    group = GroupPattern(children=(bind,))
    assert (
        group.render()
        == """{
  BIND("FastshaqlEMR" AS ?recordSource)
}"""
    )


def test_raw_sparql_expr_renders_verbatim() -> None:
    expr = RawSparqlExpr("STRLEN(STR(?iri))")
    assert expr.render() == "STRLEN(STR(?iri))"


def test_raw_graph_pattern_renders_indented_lines() -> None:
    body = RawGraphPattern(
        "?iri <http://example.org/firstName> ?firstName .\n"
        "?iri <http://example.org/lastName> ?lastName ."
    )
    group = GroupPattern(children=(body,))
    expected = """{
  ?iri <http://example.org/firstName> ?firstName .
  ?iri <http://example.org/lastName> ?lastName .
}"""
    assert group.render() == expected


def test_raw_graph_pattern_empty_renders_empty() -> None:
    assert RawGraphPattern("").render() == ""
    assert RawGraphPattern("").render(indent=2) == ""
