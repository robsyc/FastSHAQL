"""Known store divergences — case-level, never normalized away (ADR-0022).

When a store legitimately deviates (a named SPARQL interpretation or an
engine limitation), the case is registered here. The registry drives two
things:

- ``xfail`` marks applied at collection (``tests/tiers/evaluation/conftest.py``)
  keyed by ``(store, source, case)`` — the source names a ``CaseSet`` (case
  parity) or a ``Scenario`` (scenario parity) — or ``(store, source, None)``
  to cover a whole source (scenario parity runs its cases inside one test).
  A healed divergence surfaces as XPASS rather than vanishing silently.
- the report's parity matrix, where recorded outcomes read ``divergence``
  instead of ``fail`` for registered cases.

Entry discipline: one entry per diverging case with the reason phrased as the
*store's* behavior (not as a harness workaround), plus an upstream link when
one exists. Entries are live-run findings, kept current with the pinned image
tags.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Divergence:
    """Why a store legitimately fails a parity case."""

    reason: str
    upstream: str = ""
    """Tracker/doc link for the store behavior, when one exists."""


KNOWN_DIVERGENCES: dict[tuple[str, str, str | None], Divergence] = {
    # The no-FROM default graph is store-defined (SPARQL §13; ADR-0011): the
    # goldens assume the union contract (in-memory ``Dataset(default_union=True)``,
    # GraphDB, QLever). Oxigraph and Jena keep it unnamed-only, so a query with
    # no dataset clause sees only the unnamed graph.
    ("oxigraph", "named_graphs", "no_iris"): Divergence(
        reason=(
            "no-FROM default graph is the unnamed graph only (standard SPARQL); "
            "the golden assumes the union contract (ADR-0011)"
        ),
        upstream="https://www.w3.org/TR/sparql11-query/#rdfDataset",
    ),
    ("fuseki", "named_graphs", "no_iris"): Divergence(
        reason=(
            "no-FROM default graph is the unnamed graph only (standard Jena); "
            "the golden assumes the union contract (ADR-0011)"
        ),
        upstream="https://www.w3.org/TR/sparql11-query/#rdfDataset",
    ),
    # A single-valued derived field (``maxCount 1``) whose ``sh:values``
    # expression yields five matching candidates — the ``sh:node`` anchor only
    # sets the child field set, it filters nothing. The translated query has
    # no ORDER BY, and the converter keeps the first child row of a non-list
    # relationship, so whichever candidate an engine returns first surfaces;
    # the golden pins the rdflib/GraphDB order (rb1).
    ("oxigraph", "derived_relationships", "shnode_anchored_derived_target"): Divergence(
        reason=(
            "single-valued derived field over five matching candidates — no "
            "ORDER BY, so the winner is engine row order (ADR-0010); the "
            "golden pins the rdflib/GraphDB tie-break"
        ),
        upstream="https://www.w3.org/TR/sparql11-query/#solOrder",
    ),
    ("fuseki", "derived_relationships", "shnode_anchored_derived_target"): Divergence(
        reason=(
            "single-valued derived field over five matching candidates — no "
            "ORDER BY, so the winner is engine row order (ADR-0010); the "
            "golden pins the rdflib/GraphDB tie-break"
        ),
        upstream="https://www.w3.org/TR/sparql11-query/#solOrder",
    ),
}
