"""``sh:select`` body scanner — ``core/parser/node_expr/select_scan.py``.

Unit tier: projection extraction, brace matching, modifier rejection,
Appendix A pre-binding validation (ADR-0015).

Naming: ``test_parse_select_*`` exercises :func:`parse_shacl_select`;
``test_select_*`` exercises :func:`validate_select_prebinding`.
"""

from __future__ import annotations

import pytest

from fastshaql.core.parser.errors import UnsupportedShapeError
from fastshaql.core.parser.node_expr.select_scan import (
    parse_shacl_select,
    validate_select_prebinding,
)

# --- parse: extraction + projection ---


def test_parse_select_minimal() -> None:
    body, var = parse_shacl_select("SELECT ?n WHERE { $this ex:name ?n }")
    assert var == "n"
    assert body == "$this ex:name ?n"


def test_parse_select_strips_author_indentation() -> None:
    """Multi-line bodies are dedented so emitted SPARQL stays tidy regardless
    of how the author indented the ``sh:select`` block in the shapes graph."""
    text = """
        SELECT ?label
        WHERE {
            $this ex:name ?label .
        }
    """
    body, var = parse_shacl_select(text)
    assert var == "label"
    assert body == "$this ex:name ?label ."


def test_parse_select_concat_bind() -> None:
    text = """
        SELECT ?label
        WHERE {
            $this ex:givenName ?given .
            $this ex:familyName ?family .
            BIND(CONCAT(?given, " ", ?family) AS ?label)
        }
    """
    body, var = parse_shacl_select(text)
    assert var == "label"
    assert "BIND(CONCAT(?given" in body
    assert "ex:familyName" in body


def test_parse_select_head_expression_raises() -> None:
    # A SELECT-head expression (EXPR AS ?var) cannot dissolve into the merged
    # WHERE body — reject it loudly, consistent with the aggregate/top-N
    # deferral (ADR-0015). Authors must move the computation into a BIND.
    text = 'SELECT (CONCAT(?a, " ", ?b) AS ?label) WHERE { $this ex:a ?a . }'
    with pytest.raises(UnsupportedShapeError, match="SELECT-head expression"):
        parse_shacl_select(text)


# --- parse: protected regions inside strings ---


def test_parse_select_open_brace_in_string_ignored() -> None:
    text = 'SELECT ?x WHERE { BIND("{ not a brace" AS ?x) }'
    body, var = parse_shacl_select(text)
    assert var == "x"
    assert 'BIND("{ not a brace" AS ?x)' in body


def test_parse_select_close_brace_in_string_ignored() -> None:
    # A ``}`` inside a string literal must not prematurely close the WHERE block.
    body, var = parse_shacl_select('SELECT ?x WHERE { BIND("}" AS ?x) }')
    assert var == "x"
    assert 'BIND("}" AS ?x)' in body


# --- parse: allowed constructs ---


def test_parse_select_nested_subselect_with_group_by_ok() -> None:
    # Top-level modifiers are rejected, but a nested sub-SELECT may use them.
    text = """
        SELECT ?x WHERE {
            {
                SELECT ?y WHERE { ?y ex:p ?z } GROUP BY ?y
            }
        }
    """
    body, var = parse_shacl_select(text)
    assert var == "x"
    assert "GROUP BY" in body


def test_parse_select_service_allowed() -> None:
    text = "SELECT ?x WHERE { SERVICE <http://example.org/sparql> { ?s ?p ?o } }"
    body, var = parse_shacl_select(text)
    assert var == "x"
    assert "SERVICE" in body


# --- parse: projection + head-modifier rejection ---


@pytest.mark.parametrize(
    "select",
    [
        "SELECT WHERE { }",
        "SELECT ?a ?b WHERE { }",
        "SELECT * WHERE { $this ex:p ?o }",
    ],
    ids=["zero", "two_vars", "star"],
)
def test_parse_select_projection_count_raises(select: str) -> None:
    """The SELECT head must name exactly one variable — zero, two, and ``*``
    (which projects every variable in scope) cannot dissolve into the
    enclosing projection."""
    with pytest.raises(UnsupportedShapeError, match="exactly one variable"):
        parse_shacl_select(select)


@pytest.mark.parametrize("modifier", ["DISTINCT", "REDUCED"])
def test_parse_select_head_modifier_raises(modifier: str) -> None:
    with pytest.raises(UnsupportedShapeError, match=modifier):
        parse_shacl_select(f"SELECT {modifier} ?v WHERE {{ }}")


# --- parse: top-level modifier rejection (merge-ability) ---


@pytest.mark.parametrize(
    ("suffix", "keyword"),
    [
        ("GROUP BY ?v", "GROUP BY"),
        ("ORDER BY ?v", "ORDER BY"),
        ("LIMIT 10", "LIMIT"),
        ("OFFSET 0", "OFFSET"),
        ("HAVING (?v > 0)", "HAVING"),
    ],
)
def test_parse_select_top_level_modifier_suffix_raises(
    suffix: str, keyword: str
) -> None:
    with pytest.raises(UnsupportedShapeError, match=keyword):
        parse_shacl_select(f"SELECT ?v WHERE {{ }} {suffix}")


@pytest.mark.parametrize(
    "query",
    [
        "SELECT ?v WHERE { $this ex:p ?v } VALUES ?this { <http://example.org/a> }",
        "SELECT ?v WHERE { } VALUES ?x { 1 }",
    ],
    ids=["binds_this", "binds_other_var"],
)
def test_parse_select_trailing_values_raises(query: str) -> None:
    with pytest.raises(UnsupportedShapeError, match="trailing SPARQL"):
        parse_shacl_select(query)


def test_parse_select_trailing_comment_only_ok() -> None:
    body, var = parse_shacl_select("SELECT ?v WHERE { $this ex:p ?v } # GROUP BY ?v")
    assert var == "v"
    assert body == "$this ex:p ?v"


# --- parse: structural rejection ---


def test_parse_select_missing_select_keyword_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="must start with SELECT"):
        parse_shacl_select("?v WHERE { ?v ex:p ?o }")


def test_parse_select_no_where_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="WHERE"):
        parse_shacl_select("SELECT ?v { }")


def test_parse_select_where_without_block_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="graph pattern block"):
        parse_shacl_select("SELECT ?v WHERE ?v ex:p ?o")


def test_parse_select_unbalanced_braces_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="unbalanced"):
        parse_shacl_select("SELECT ?v WHERE { ?a ex:p ?b ")


# --- prebinding validation: Appendix A MUST-fails (this only) ---


def test_select_minus_in_body_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="MINUS"):
        validate_select_prebinding("?a ex:p ?b . MINUS { ?a ex:q ?c }")


def test_select_as_this_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="AS \\?this"):
        validate_select_prebinding("BIND(?x AS $this)")


def test_select_as_uppercase_this_allowed() -> None:
    # SPARQL variables are case-sensitive: ``?THIS`` is a distinct variable from
    # the pre-bound ``?this`` (only keywords like AS are case-insensitive), so
    # binding ``?THIS`` is not an Appendix-A ``this``-binding violation.
    validate_select_prebinding("BIND(?x AS ?THIS)")


def test_select_values_this_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="VALUES"):
        validate_select_prebinding("VALUES ?this { ex:a }")


def test_select_values_group_binds_this_raises() -> None:
    # The grouped form ``VALUES (?this ?x) { ... }`` also binds ``this``.
    with pytest.raises(UnsupportedShapeError, match="VALUES"):
        validate_select_prebinding("VALUES (?this ?x) { (1 2) }")


# --- prebinding validation: false-positive guards (allowed) ---


def test_select_as_this_label_allowed() -> None:
    validate_select_prebinding("BIND(?x AS ?thisLabel)")


def test_select_minus_in_comment_allowed() -> None:
    validate_select_prebinding("# MINUS is forbidden\n?a ex:p ?b .")


def test_select_values_this_in_string_allowed() -> None:
    validate_select_prebinding('BIND("VALUES ?this" AS ?x)')


def test_select_keyword_named_variable_minus_allowed() -> None:
    # A variable named ``?minus`` is not the MINUS keyword (SPARQL [163]/[164]
    # var names may shadow reserved words). The word boundary must respect the
    # ``?`` sigil, otherwise the Appendix-A scan false-fires.
    validate_select_prebinding("?minus ex:p ?q .")


def test_select_keyword_named_variable_values_allowed() -> None:
    validate_select_prebinding("$this ex:p ?values .")


def test_select_values_with_unrelated_focus_use_allowed() -> None:
    # VALUES binds ?x; the later $this is a legitimate focus-node reference
    # (the normal case in sh:select). Appendix A only forbids VALUES *binding*
    # ``this`` itself, not referencing it elsewhere.
    validate_select_prebinding("VALUES ?x { 1 2 } $this ex:p ?x .")


def test_select_values_without_data_block_allowed() -> None:
    # A VALUES clause with no ``{`` data block is malformed SPARQL, not an
    # Appendix-A ``this``-binding violation — the triple store rejects the
    # query at execution time, so the scanner defers.
    validate_select_prebinding("?this ex:p ?x . VALUES ?x")


# --- scanner edges (mutation-hardening batch) ---


def test_parse_select_where_at_end_of_text_raises() -> None:
    # WHERE as the last token: no ``{`` follows — a clean UnsupportedShapeError,
    # never an IndexError off the end of the text.
    with pytest.raises(UnsupportedShapeError):
        parse_shacl_select("SELECT ?x WHERE")


def test_select_values_this_after_braced_group_raises() -> None:
    # A preceding braced group (OPTIONAL/BIND block) must not become the
    # data-block anchor: the var-list span is between this VALUES and *its
    # own* ``{`` — binding ?this there is still an Appendix-A violation.
    with pytest.raises(UnsupportedShapeError, match="VALUES"):
        validate_select_prebinding(
            "OPTIONAL { ?a ex:p ?b } VALUES ?this { <http://example.org/a> }"
        )


def test_select_values_this_without_data_block_defers() -> None:
    # Malformed VALUES binding-shaped var list (?this, no ``{`` at all):
    # deferred to the store — a real violation needs a data block to bind.
    validate_select_prebinding("?s ?p ?o . VALUES ?this")
    # With a second var after ?this: still deferred. The var list must not
    # be scanned at all when the data block is absent (?this not being the
    # span's final character makes the defer observable).
    validate_select_prebinding("?s ?p ?o . VALUES ?this ?x")


# --- scanner anchoring edges (mutation-hardening batch) ---


def test_select_where_search_is_anchored_after_the_select_head() -> None:
    # Leading code (dropped by the merge) may itself contain WHERE — the
    # scan for the real WHERE starts after the SELECT head, never at 0.
    body, projection = parse_shacl_select(
        "?this WHERE ?s ?p ?o . SELECT ?x WHERE { ?x ex:p ?x }"
    )
    assert body == "?x ex:p ?x"
    assert projection == "x"


def test_malformed_values_does_not_mask_a_later_minus() -> None:
    # A VALUES without its data block defers to the store for THAT span —
    # later code spans are still scanned for Appendix A violations.
    with pytest.raises(UnsupportedShapeError, match="MINUS"):
        validate_select_prebinding('VALUES ?x "lit" ?s ?p ?o . MINUS { ?a ?b ?c }')


def test_values_this_referenced_outside_its_data_block_stays_legal() -> None:
    # The Appendix A rule binds ?this only between VALUES and its data
    # block's opening brace — a ?this reference after the block is a plain
    # variable read (UNDEF data values keep this a single code span).
    validate_select_prebinding(
        "VALUES ?x { UNDEF } ?this ex:p ?o . OPTIONAL { ?z ex:q ?w }"
    )


def test_whitespace_between_trailing_literals_does_not_mask_junk() -> None:
    # A whitespace-only span between two string literals must not end the
    # suffix scan — later trailing content still rejects.
    with pytest.raises(UnsupportedShapeError, match="trailing"):
        parse_shacl_select('SELECT ?x WHERE { ?x ex:p ?x } "a"  "b" trailing')
