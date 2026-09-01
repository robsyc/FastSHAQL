"""Graph read helpers — ``core/parser/util/graph_reads.py``.

Unit tier: the language-preference chain behind description selection —
RFC 4647 basic filtering (preferred tag, subtag ranges, untagged, foreign
fallback) and subject scoping of predicate reads.

Order: language selection matrix → default language → subject scoping.
"""

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


# --- Language-selection precedence and determinism ---


def test_first_localized_str_preferred_language_beats_untagged() -> None:
    """RFC 4647: the preferred tag outranks the untagged fallback — with an
    ``en`` and a plain literal present, ``lang="en"`` selects the ``en`` one."""
    graph = _graph_with_comment(Literal("Plain"), Literal("English", lang="en"))
    assert first_localized_str(graph, SUBJECT, RDFS.comment, lang="en") == "English"


def test_first_localized_str_subtag_range_beats_foreign_fallback() -> None:
    """A basic-range match (``en`` → ``en-US``) wins before the any-language
    fallback fires — otherwise a lower-ordered foreign tag would answer."""
    graph = _graph_with_comment(
        Literal("German", lang="de"),
        Literal("US English", lang="en-US"),
    )
    assert first_localized_str(graph, SUBJECT, RDFS.comment, lang="en") == "US English"


def test_first_localized_str_same_language_lexical_tiebreak() -> None:
    """Within one language the lexical order is the documented determinism —
    not the graph's insertion order."""
    graph = _graph_with_comment(
        Literal("banana", lang="en"),
        Literal("apple", lang="en"),
    )
    assert first_localized_str(graph, SUBJECT, RDFS.comment, lang="en") == "apple"


# --- Default language ---


def test_first_localized_str_default_language_is_english() -> None:
    """The default preferred language is ``en`` — an ``en`` literal beats a
    lower-ordered ``de`` one without passing ``lang=``."""
    graph = _graph_with_comment(
        Literal("Hallo", lang="de"),
        Literal("Hello", lang="en"),
    )
    assert first_localized_str(graph, SUBJECT, RDFS.comment) == "Hello"


# --- Subject scoping ---


def test_first_localized_str_reads_only_the_given_subject() -> None:
    """Predicate reads are scoped to *subject* — a comment on another
    resource never leaks into this one's description."""
    graph = _graph_with_comment(Literal("Other subject", lang="en"))
    assert first_localized_str(graph, EX + "SilentShape", RDFS.comment) is None
