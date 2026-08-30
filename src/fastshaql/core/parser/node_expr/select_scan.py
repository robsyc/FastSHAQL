"""Parse ``sh:select`` bodies for merge-able emission (ADR-0015).

Light textual surgery on trusted author SPARQL — projection-var scan, WHERE
body extraction by brace-matching, top-level modifier detection, and Appendix A
pre-binding validation. No full SPARQL parser.
"""

from __future__ import annotations

import re
import textwrap

from ...sparql.lex import (
    SPARQL_VAR,
    THIS_REF,
    code_spans,
    extract_braced_body,
    find_keyword,
    skip_ws_and_comments,
    word_bounded,
    word_bounded_any,
)
from ..errors import UnsupportedShapeError

_TOP_LEVEL_MODIFIERS = ("GROUP BY", "ORDER BY", "LIMIT", "OFFSET", "HAVING")
_HEAD_MODIFIERS = ("DISTINCT", "REDUCED")
# SPARQL keywords (AS, MINUS, VALUES) are case-insensitive, but the variable
# ``this`` is case-sensitive — ``?THIS`` is a distinct variable, not the
# pre-bound focus var. So the keyword arm carries the ``(?i:...)`` flag while
# ``this`` is matched case-sensitively via ``THIS_REF.pattern``; otherwise
# ``AS ?THIS`` is a false-positive Appendix-A violation.
_AS_THIS = re.compile(r"(?i:" + word_bounded("AS") + r")\s+" + THIS_REF.pattern)
_MINUS = re.compile(word_bounded("MINUS"), re.IGNORECASE)
_VALUES = re.compile(word_bounded("VALUES"), re.IGNORECASE)
_HEAD_MODIFIERS_RE = re.compile(word_bounded_any(_HEAD_MODIFIERS), re.IGNORECASE)
_TOP_LEVEL_MODIFIERS_RE = re.compile(
    word_bounded_any(_TOP_LEVEL_MODIFIERS), re.IGNORECASE
)


def parse_shacl_select(text: str) -> tuple[str, str]:
    """Extract merge-able WHERE body and single projection variable from *text*.

    Args:
        text: Full ``sh:select`` string with prefixes already expanded.

    Returns:
        ``(body, projection_var)`` where *body* is the inner WHERE content
        (without braces) and *projection_var* is the local name without ``?``.

    Raises:
        UnsupportedShapeError: On ill-formed or unsupported SELECT forms —
            missing SELECT/WHERE, head modifiers (DISTINCT/REDUCED), a SELECT-head
            expression, top-level GROUP BY/ORDER BY/LIMIT/OFFSET/HAVING, any
            trailing SPARQL after the WHERE block, or an Appendix A pre-binding
            violation (MINUS / AS ?this / VALUES binding this).
    """
    select_pos = find_keyword(text, "SELECT")
    if select_pos is None:
        raise UnsupportedShapeError("sh:select must start with SELECT")

    head_start = skip_ws_and_comments(text, select_pos + len("SELECT"))
    if m := _HEAD_MODIFIERS_RE.match(text, head_start):
        raise UnsupportedShapeError(
            f"sh:select with top-level {m.group(0)} is not supported"
        )

    where_pos = find_keyword(text, "WHERE", head_start)
    if where_pos is None:
        raise UnsupportedShapeError("sh:select must contain WHERE")

    projection_text = text[head_start:where_pos].strip()
    projection_var = _extract_projection_var(projection_text)

    brace_pos = skip_ws_and_comments(text, where_pos + len("WHERE"))
    if brace_pos >= len(text) or text[brace_pos] != "{":
        raise UnsupportedShapeError(
            "sh:select WHERE must be followed by a graph pattern block"
        )

    try:
        body, after_body = extract_braced_body(text, brace_pos)
    except ValueError as exc:
        raise UnsupportedShapeError(str(exc)) from exc

    body = textwrap.dedent(body).strip()
    _reject_trailing_suffix(text[after_body:])
    validate_select_prebinding(body)
    return body, projection_var


def _extract_projection_var(projection_text: str) -> str:
    if not projection_text:
        raise UnsupportedShapeError("sh:select must project exactly one variable")
    # A SELECT-head expression ``(EXPR AS ?var)`` (SPARQL §16.1.2) cannot dissolve
    # into the merged WHERE body — the head computation has nowhere to live once
    # the SELECT clause is dropped. Reject it loudly, consistent with the
    # aggregate/top-N deferral (ADR-0015); authors move the computation into a
    # ``BIND`` inside WHERE (as the spec's own examples do).
    if projection_text.startswith("("):
        raise UnsupportedShapeError(
            "sh:select SELECT-head expression (e.g. (EXPR AS ?var)) is not supported; "
            "move the computation into the WHERE body via BIND"
        )
    vars_found = [m.group("name") for m in SPARQL_VAR.finditer(projection_text)]
    if len(vars_found) == 1:
        return vars_found[0]
    if not vars_found:
        raise UnsupportedShapeError("sh:select must project exactly one variable")
    raise UnsupportedShapeError(
        f"sh:select must project exactly one variable, found {len(vars_found)}"
    )


def _reject_trailing_suffix(suffix: str) -> None:
    """Reject any SPARQL after the closing WHERE ``}``.

    The merge drops the SELECT clause, so nothing after the WHERE block survives
    — group/order/limit clauses cannot dissolve into the enclosing body. A
    top-level modifier is named in the message as a diagnostic; any other
    trailing content falls through to the generic message.
    """
    for start, end in code_spans(suffix):
        if not suffix[start:end].strip():
            continue
        if m := _TOP_LEVEL_MODIFIERS_RE.search(suffix, start, end):
            raise UnsupportedShapeError(
                f"sh:select with top-level {m.group(0)} is not supported"
            )
        raise UnsupportedShapeError(
            "sh:select must not contain trailing SPARQL after the WHERE block"
        )


def validate_select_prebinding(body: str) -> None:
    """Reject Appendix A MUST-fail constructs in a ``sh:select`` body (§A).

    Appendix A rule 1 forbids ``MINUS`` *unconditionally*; the ``AS ?this`` and
    ``VALUES`` rules are variable-conditional (they fire only when binding the
    pre-bound ``this``). Scope is ``this`` only — the sole pre-bound variable
    for ``sh:select`` node expressions.
    """
    for start, end in code_spans(body):
        segment = body[start:end]
        if _MINUS.search(segment):
            raise UnsupportedShapeError(
                "sh:select body must not contain MINUS (SHACL-SPARQL Appendix A)"
            )
        if _AS_THIS.search(segment):
            raise UnsupportedShapeError(
                "sh:select body must not bind AS ?this or AS $this (SHACL-SPARQL Appendix A)"
            )
        for values_match in _VALUES.finditer(segment):
            # Appendix A forbids VALUES *binding* the pre-bound focus var. The
            # variable list sits between VALUES and the ``{`` data block
            # (SPARQL 1.2 [65] InlineData, [67]/[68]); referencing $this
            # elsewhere stays legal. Scoping the check to that span is
            # sufficient because [69] DataBlockValue admits no Var
            # (iri | RDFLiteral | NumericLiteral | BooleanLiteral | 'UNDEF'
            # | TripleTermData) — a variable can appear only in the var list.
            data_block_start = segment.find("{", values_match.end())
            if data_block_start == -1:
                continue  # malformed VALUES — defer to the triple store
            if THIS_REF.search(segment[values_match.end() : data_block_start]):
                raise UnsupportedShapeError(
                    "sh:select body must not bind ?this/$this via VALUES (SHACL-SPARQL Appendix A)"
                )
