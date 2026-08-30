"""Cross-cutting request parameters for GraphQL operations (ADR-0011)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryContext:
    """Bundled parameters scoped to a single GraphQL operation."""

    lang_tags: tuple[str, ...] = ()
    """Language preference chain for language-accepting properties
    (ADR-0012): an ordered tuple of BCP 47 basic ranges (``"en"``,
    ``"nl-BE"``) plus the sentinels ``""`` (untagged-only) and ``"*"``
    (any tagged literal); the empty tuple means *no preference* — no
    language machinery is emitted."""

    read_graphs: tuple[str, ...] = ()
    """Read scope: per-request graph IRIs translated to ``FROM`` clauses —
    the queried default graph is their RDF merge (many allowed; empty tuple
    uses the store's default dataset unchanged). See ADR-0011 and CONTEXT.md
    **read_graphs**."""

    write_graph: str | None = None
    """Reserved for the future writes era: the SPARQL Update ``WITH`` / Graph
    Store Protocol *write target* — one graph, deliberately a separate slot
    from the read scope. Reads never consume it; query translation rejects a
    set value (ADR-0011)."""


_Q_PARAMETER = re.compile(
    r"q\s*=\s*(0(?:\.\d{0,3})?|1(?:\.0{0,3})?)", re.IGNORECASE | re.ASCII
)
"""The weight parameter of one Accept-Language entry — ``q`` per RFC 9110
§12.4.2, name case-insensitive: ``0`` optionally followed by up to three
decimals, or ``1`` by up to three zeros. Anything else (``q=2``, ``q=00.5``,
four decimals) is malformed — skipped like any other invalid parameter, so
a later valid ``q`` in the same entry may still win. ``re.ASCII`` holds
``\\d`` to RFC 5234 ``DIGIT`` — Unicode decimal digits are malformed."""


def _entry_weight(segment: str) -> float | None:
    """Weight of one comma-separated Accept-Language entry, or ``None`` when
    no well-formed ``q`` parameter is present.

    An invalid weight parameter is skipped, not the entry: malformed
    values fall back to the default weight 1.0 (RFC 9110 §12.4.2 constrains
    senders only; recipient handling of invalid weights is unspecified).
    """
    for parameter in segment.split(";")[1:]:
        match = _Q_PARAMETER.fullmatch(parameter.strip())
        if match is not None:
            return float(match[1])
    return None


def lang_tags_from_accept_language(header: str | None) -> tuple[str, ...]:
    """Resolve an Accept-Language header *value* into a language preference
    chain (RFC 9110 §12.5.4 / RFC 4647 basic ranges; ADR-0012) — the
    framework-neutral string-to-tuple parser, Core not Adapter.

    ``None`` or a blank header yields ``()``. Entries carry an optional
    ``q`` weight (missing/malformed → 1.0); ``q=0`` entries are dropped,
    the rest sort by weight descending (first-seen on ties), and exact
    duplicates keep the higher-weighted occurrence. Tags are lowercased;
    ``*`` passes through as the any-language sentinel. No subtag expansion;
    the untagged sentinel ``""`` is never synthesized..
    """
    if header is None or not header.strip():
        return ()
    kept: dict[str, tuple[float, int]] = {}
    for position, raw_segment in enumerate(header.split(",")):
        segment = raw_segment.strip()
        tag = segment.split(";", maxsplit=1)[0].strip().lower()
        if not tag:
            continue
        weight = _entry_weight(segment)
        if weight == 0.0:
            continue
        effective = 1.0 if weight is None else weight
        prior = kept.get(tag)
        if prior is None or effective > prior[0]:
            kept[tag] = (effective, position)
    return tuple(
        tag
        for tag, _ in sorted(kept.items(), key=lambda item: (-item[1][0], item[1][1]))
    )
