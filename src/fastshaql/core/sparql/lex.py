"""SPARQL 1.2 lexical helpers for trusted author text (§19).

Consumed by prefix expansion (``core.parser.node_expr.shacl_prefixes``),
``sh:select`` body extraction (``core.parser.node_expr.select_scan``), and
focus-node substitution (``core.translation.node_expr``). Protected regions - string literals,
IRIREFs, comments - are never scanned for keywords or brace depth.

Lives under ``core/sparql`` (not ``core/parser``) because it is SPARQL
lexing, shared by both the parser and the translator; both already depend on
``core/sparql``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# SPARQL 1.2 §19 grammar fragments (docs/references/sparql12/query.html).
# ECHAR [180]: '\' then one of  t b n r f " ' \. Spec-exact: the ``\\`` arm in
# the class *is* backslash — a member of [180], which is what legalises escaped
# backslash (``"\\"``) inside strings. Do not drop it: without it, ``\\`` stops
# being protected and a string literal containing an escaped backslash could be
# mis-tokenised, undermining the protected-region guarantee (ADR-0017).
_ECHAR = r"\\[tbnrf\"'\\]"
_UCHAR = r"\\u[0-9A-Fa-f]{4}|\\U[0-9A-Fa-f]{8}"
_STRING_LITERAL_LONG1 = (
    r"'''(?:(?:'|'')?(?:[^'\\]|" + _ECHAR + r"|" + _UCHAR + r"))*'''"
)
_STRING_LITERAL_LONG2 = (
    r'"""(?:(?:"|"")?(?:[^"\\]|' + _ECHAR + r"|" + _UCHAR + r'))*"""'
)
_STRING_LITERAL1 = r"'(?:[^'\\\r\n]|" + _ECHAR + r"|" + _UCHAR + r")*'"
_STRING_LITERAL2 = r'"(?:[^"\\\r\n]|' + _ECHAR + r"|" + _UCHAR + r')*"'
_IRIREF = r"<(?:[^<>\"{}|^`\\\x00-\x20]|" + _UCHAR + r")*>"
_COMMENT = r"#[^\r\n]*"
# PN_LOCAL [190]: leading ``PN_CHARS_U | digit | ':'``  then
# ``(PN_CHARS | '.' | ':' | PLX)*`` not ending in ``'.'``. ``\w`` (Unicode)
# covers most of PN_CHARS [188] incl. non-ASCII letters, so ``ex:café`` expands
# whole rather than being left as an unresolved bare prefixed name (the emitted
# query carries no ``PREFIX`` block — ADR-0015 expand-at-parse). The few
# non-letter PN_CHARS members ``\w`` misses (U+00B7, combining marks U+0300-036F,
# U+203F/2040) are vanishingly rare in shapes graphs; a local name containing
# them would partially match and corrupt — accept the narrowing rather than
# embed exotic Unicode classes for a near-zero case. ``_PLX`` admits ``%XX``
# percent-escapes, so ``ex:a%2Fb`` is not truncated into a malformed
# ``<…a>%2Fb``. PN_LOCAL_ESC backslash-escapes (``ex:a\.b``) remain unsupported:
# they denote literal chars and would need un-escaping before splicing into
# ``<…>`` — rare in shapes graphs; authors use a full ``<IRIREF>`` instead. The
# prefix arm stays ASCII-narrow (interior dots and non-ASCII leading chars in
# PN_PREFIX [189] are not real-world cases; a miss there leaves text intact,
# never corrupts).
_PLX = r"%[0-9A-Fa-f]{2}"
_PREFIXED_NAME = (
    r"(?<![\w:?])(?P<prefix>[A-Za-z][\w-]*):"
    rf"(?P<local>[\w:](?:(?:[\w.\-:]|{_PLX})*(?:[\w\-:]|{_PLX}))?)"
    r"(?![\w:])"
)

# Protected regions - string literals ([176]-[179]), IRIREF ([159]), comments
# (§19.4) - shared by both token regexes; never scanned for keywords or braces.
_PROTECTED_ARMS = (
    rf"(?P<long1>{_STRING_LITERAL_LONG1})"
    rf"|(?P<long2>{_STRING_LITERAL_LONG2})"
    rf"|(?P<s1>{_STRING_LITERAL1})"
    rf"|(?P<s2>{_STRING_LITERAL2})"
    rf"|(?P<iri>{_IRIREF})"
    rf"|(?P<comment>{_COMMENT})"
)
_PROTECTED_TOKEN = re.compile(_PROTECTED_ARMS)
# Prefix expansion additionally recognises the prefixed-name arm.
EXPAND_TOKEN = re.compile(_PROTECTED_ARMS + "|" + _PREFIXED_NAME)
# Comment matcher for whitespace/comment skipping (§19.4) — narrower than the
# full protected-token matcher, which also spans strings and IRIREFs.
_COMMENT_RE = re.compile(_COMMENT)

# VARNAME [187] allows a leading digit and non-ASCII (PN_CHARS_BASE); this
# ASCII letter/underscore narrowing is a documented narrowing (matches the
# PN_LOCAL one above). Subsequent chars use ``\w`` (Unicode in Py3).
_VAR_NAME = r"[A-Za-z_][\w_]*"
SPARQL_VAR = re.compile(rf"(?<![\w:?])\?(?P<name>{_VAR_NAME})(?![\w:])")

# Keyword token boundary. The negated lookbehind excludes identifier chars and
# both variable sigils (``?``/``$`` - SPARQL [163]/[164]) so keyword-named
# variables (``?minus``) are not read as the keyword. The lookahead only
# excludes identifier chars: a keyword legitimately followed by a variable
# (``LIMIT ?x``) must still match.
_BOUNDARY = r"(?<![\w:?$])"
_END = r"(?![\w:])"


def word_bounded(literal: str) -> str:
    """Regex fragment matching *literal* as a standalone SPARQL keyword token."""
    return rf"{_BOUNDARY}{re.escape(literal)}{_END}"


def word_bounded_any(literals: tuple[str, ...]) -> str:
    """Regex fragment matching any of *literals* as a standalone keyword token."""
    return rf"{_BOUNDARY}(?:{'|'.join(map(re.escape, literals))}){_END}"


# ``$this`` / ``?this`` focus-node reference (SHACL-SPARQL §3.3.1). Both sigils
# denote the same pre-bound variable ``this`` (SPARQL [163]/[164]); the ``$``
# form is the SHACL authoring convention, but ``?this`` is equivalent and must
# substitute identically — a dangling ``?this`` would be an unbound variable.
# Used both for Appendix-A binding detection (select_scan) and focus-node
# substitution (translation).
THIS_REF = re.compile(rf"{_BOUNDARY}(?:\$|\?)this{_END}")


def _skip_protected(text: str, pos: int) -> int:
    """Advance *pos* past a protected token at *pos*, or return *pos* unchanged."""
    match = _PROTECTED_TOKEN.match(text, pos)
    return match.end() if match else pos


def _iter_code(text: str) -> Iterator[tuple[int, int]]:
    """Yield ``(start, end)`` of each maximal code (non-protected) region.

    Code regions are the gaps between protected matches (string literals,
    IRIREFs, comments); the protected-token regex yields them directly. This is
    the canonical "walk past protected regions" shared by ``code_spans`` and
    ``find_keyword``.
    """
    pos = 0
    for m in _PROTECTED_TOKEN.finditer(text):
        if m.start() > pos:
            yield pos, m.start()
        pos = m.end()
    if pos < len(text):
        yield pos, len(text)


def skip_ws_and_comments(text: str, pos: int) -> int:
    """Advance *pos* past whitespace and SPARQL comments (§19.4)."""
    while pos < len(text):
        if text[pos] in " \t\r\n":
            pos += 1
            continue
        if m := _COMMENT_RE.match(text, pos):
            pos = m.end()
            continue
        break
    return pos


def find_keyword(text: str, keyword: str, start: int = 0) -> int | None:
    """Return the start index of *keyword* at a code position, or ``None``.

    Searches only code regions, so a keyword-shaped substring inside a string
    literal, IRIREF, or comment is not matched.
    """
    keyword_re = re.compile(word_bounded(keyword), re.IGNORECASE)
    for span_start, span_end in _iter_code(text):
        if span_end <= start:
            continue
        if m := keyword_re.search(text, max(span_start, start), span_end):
            return m.start()
    return None


def code_spans(text: str) -> list[tuple[int, int]]:
    """Return ``(start, end)`` spans of code (non-protected) regions in *text*."""
    return list(_iter_code(text))


def extract_braced_body(text: str, open_brace: int) -> tuple[str, int]:
    """Return inner text and index after the matching ``}`` for ``{`` at *open_brace*."""
    if open_brace >= len(text) or text[open_brace] != "{":
        msg = "sh:select WHERE block is missing opening brace"
        raise ValueError(msg)
    depth = 0
    body_start = -1
    pos = open_brace
    while pos < len(text):
        protected_end = _skip_protected(text, pos)
        if protected_end != pos:
            pos = protected_end
            continue
        char = text[pos]
        if char == "{":
            depth += 1
            if depth == 1:
                body_start = pos + 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[body_start:pos], pos + 1
        pos += 1
    msg = "sh:select WHERE block has unbalanced braces"
    raise ValueError(msg)
