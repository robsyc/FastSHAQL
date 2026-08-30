"""Graph read helpers — ``core/parser/util/graph_reads.py``."""

from __future__ import annotations

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDFS

from fastshaql.core.parser.util.graph_reads import first_localized_str

EX = URIRef("http://example.org/")
SUBJECT = EX + "ThingShape"


def _graph_with_comment(*literals: Literal) -> Graph:
    graph = Graph()
    for lit in literals:
        graph.add((SUBJECT, RDFS.comment, lit))
    return graph


def test_first_localized_str_prefers_language() -> None:
    graph = _graph_with_comment(
        Literal("French", lang="fr"),
        Literal("English", lang="en"),
    )
    assert first_localized_str(graph, SUBJECT, RDFS.comment, lang="en") == "English"


def test_first_localized_str_untagged_before_other_language() -> None:
    graph = _graph_with_comment(
        Literal("Plain"),
        Literal("French", lang="fr"),
    )
    assert first_localized_str(graph, SUBJECT, RDFS.comment, lang="en") == "Plain"


def test_first_localized_str_any_language_fallback() -> None:
    graph = _graph_with_comment(Literal("Bonjour", lang="fr"))
    assert first_localized_str(graph, SUBJECT, RDFS.comment, lang="en") == "Bonjour"


def test_first_localized_str_rfc4647_en_us_matches_en() -> None:
    graph = _graph_with_comment(Literal("US English", lang="en-US"))
    assert first_localized_str(graph, SUBJECT, RDFS.comment, lang="en") == "US English"


def test_first_localized_str_predicate_fallback() -> None:
    graph = Graph()
    graph.add((SUBJECT, RDFS.label, Literal("Label", lang="en")))
    assert (
        first_localized_str(graph, SUBJECT, RDFS.comment, RDFS.label, lang="en")
        == "Label"
    )


def test_first_localized_str_returns_none_when_absent() -> None:
    graph = Graph()
    assert first_localized_str(graph, SUBJECT, RDFS.comment, RDFS.label) is None
