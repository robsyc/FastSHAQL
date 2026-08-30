"""SPARQL lexical helpers — ``core/sparql/lex.py``.

Unit tier: the protected-region primitives shared by prefix expansion, select
surgery, and focus-node substitution. The protected-region guarantee (string
literals, IRIREFs, and comments are never scanned for keywords or braces) is
the textual-safety premise of ADR-0017, so it is pinned directly here rather
than only through its consumers.

Order: find_keyword → code_spans → extract_braced_body → skip_ws_and_comments.
"""

from __future__ import annotations

import pytest

from fastshaql.core.sparql.lex import (
    code_spans,
    extract_braced_body,
    find_keyword,
    skip_ws_and_comments,
)

# --- find_keyword ---


def test_find_keyword_locates_code_position() -> None:
    assert find_keyword("SELECT ?x WHERE {}", "WHERE") == 10


def test_find_keyword_is_case_insensitive() -> None:
    # SPARQL keywords are case-insensitive (§19.1 terminal symbols).
    assert find_keyword("select ?x where {}", "WHERE") == 10


def test_find_keyword_absent_returns_none() -> None:
    assert find_keyword("?x :p ?y .", "WHERE") is None


def test_find_keyword_respects_start_parameter() -> None:
    # ``start`` must skip an earlier occurrence of the same token.
    assert find_keyword("WHERE ?x . SELECT", "WHERE", start=5) is None
    assert find_keyword("?x . WHERE { }", "WHERE", start=4) == 5


def test_find_keyword_skips_keyword_inside_string_literal() -> None:
    assert find_keyword('?x :p "WHERE" .', "WHERE") is None


def test_find_keyword_skips_keyword_inside_iriref() -> None:
    assert find_keyword("?x <http://example.org/WHERE> .", "WHERE") is None


def test_find_keyword_skips_keyword_inside_comment() -> None:
    assert find_keyword("?x :p . # WHERE\n", "WHERE") is None


def test_find_keyword_start_beyond_early_code_span() -> None:
    # A code span that ends before ``start`` (here: the short span ahead of an
    # IRIREF) is skipped wholesale — the search resumes in the next span.
    text = "?s <urn:p> SELECT"
    assert find_keyword(text, "SELECT", start=4) == 11


# --- code_spans ---


def test_code_spans_whole_text_when_no_protected_region() -> None:
    assert code_spans("?x :p ?y .") == [(0, 10)]


def test_code_spans_splits_around_protected_regions() -> None:
    assert code_spans('?x :p "s" ?y') == [(0, 6), (9, 12)]


def test_code_spans_empty_text() -> None:
    assert code_spans("") == []


def test_code_spans_fully_protected_text() -> None:
    assert code_spans('"only a string"') == []


# --- extract_braced_body ---


def test_extract_braced_body_flat() -> None:
    assert extract_braced_body("{ a }", 0) == (" a ", 5)


def test_extract_braced_body_nested() -> None:
    assert extract_braced_body("{ { b } }", 0) == (" { b } ", 9)


def test_extract_braced_body_ignores_braces_in_strings() -> None:
    assert extract_braced_body('{ "}" }', 0) == (' "}" ', 7)


def test_extract_braced_body_unbalanced_raises() -> None:
    with pytest.raises(ValueError, match="unbalanced"):
        extract_braced_body("{ a", 0)


def test_extract_braced_body_missing_opener_raises() -> None:
    with pytest.raises(ValueError, match="opening brace"):
        extract_braced_body("a", 0)


# --- skip_ws_and_comments ---


def test_skip_ws_and_comments_advances_past_ws_and_comment() -> None:
    text = "  \n # comment\n x"
    assert skip_ws_and_comments(text, 0) == len(text) - 1


def test_skip_ws_and_comments_stops_at_code() -> None:
    assert skip_ws_and_comments("no ws", 0) == 0


def test_skip_ws_and_comments_stops_at_string_literal() -> None:
    # A string is not whitespace and not a comment — the scanner must stop at
    # the opening quote, never reach into the literal.
    assert skip_ws_and_comments('  "s"', 0) == 2


def test_skip_ws_and_comments_exhausts_at_end_of_text() -> None:
    # Trailing whitespace with no code after it — the walk runs off the end
    # of the text instead of stopping at a code character.
    assert skip_ws_and_comments("SELECT ?v  ", 9) == len("SELECT ?v  ")
