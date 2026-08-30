"""Triple-store session contract for the evaluation harness.

A *store session* is a live triple store (started in a container by an
evaluation-tier fixture) that the parity/perf runners exercise via
``HttpxSparqlStore``. ``StoreSession`` is the only interface the harness
consumes; ``graphdb.py`` is the reference adapter.

To add a store (e.g. QLever): implement this Protocol in a sibling module
(``qlever.py``), start its container in a session-scoped fixture, and yield the
session. Runners and the report are store-agnostic. See ADR-0022.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from rdflib import Graph


class StoreSession(Protocol):
    """Live triple-store session exercised by the evaluation tier."""

    query_endpoint: str
    """SPARQL query URL consumed by ``HttpxSparqlStore``."""

    image: str
    """Container image tag, recorded in the evaluation report."""

    def load_graph(self, graph: Graph) -> None:
        """Replace the store's contents with *graph* (per-case data reset)."""
        ...

    def close(self) -> None:
        """Release resources (HTTP clients, etc.) — call from fixture teardown."""
        ...
