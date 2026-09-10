"""Triple-store session contract for the evaluation harness.

A *store session* is a live triple store (started in a container by an
evaluation-tier fixture) that the parity/perf runners exercise via
``HttpxSparqlStore``. ``StoreSession`` is the only interface the harness
consumes; each adapter module owns its container lifecycle behind a ``start()``
context manager and is registered in ``support.eval.stores`` (see ADR-0022).

This module also hosts the plumbing every HTTP store adapter shares: the
readiness poll, the error-raising response check, and per-graph Graph Store
Protocol serialization.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol
from urllib.parse import quote

import httpx
from rdflib import ConjunctiveGraph, Dataset
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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


def check(response: httpx.Response) -> None:
    """Raise with the store's error body included (the body says why)."""
    if response.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"{response.request.method} {response.url} -> "
            f"{response.status_code}: {response.text}",
            request=response.request,
            response=response,
        )


def poll_until(predicate: Callable[[], bool], *, timeout: float, what: str) -> None:
    """Call *predicate* until truthy or *timeout* elapses (readiness waits)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except Exception:  # noqa: BLE001, S110 — not-ready stores fail noisily
            pass
        time.sleep(0.25)
    raise TimeoutError(f"{what} not ready within {timeout:.0f}s")


def gsp_payloads(graph: Graph) -> Iterator[tuple[str, str]]:
    """Serialize *graph* into per-graph GSP PUT payloads: ``(query, turtle)``.

    A ``Dataset`` (multi-graph) becomes one ``?graph=<iri>`` payload per named
    graph plus one ``?default=`` payload for its unnamed graph; a plain
    ``Graph`` a single ``?default=`` payload. Per-graph Turtle only — never
    TriG/N-Quads to a GSP target: Oxigraph rejects it with a 400 that
    *destructively empties the target graph*, and Fuseki accepts it but
    silently drops the named-graph block (ADR-0022).
    """
    if not isinstance(graph, ConjunctiveGraph):
        yield "default=", graph.serialize(format="turtle")
        return
    # Dataset.graphs() is the non-deprecated spelling of ConjunctiveGraph.contexts().
    contexts = graph.graphs() if isinstance(graph, Dataset) else graph.contexts()
    for context in contexts:
        turtle = context.serialize(format="turtle")
        if context.identifier == DATASET_DEFAULT_GRAPH_ID:
            yield "default=", turtle
        else:
            yield f"graph={quote(str(context.identifier))}", turtle
