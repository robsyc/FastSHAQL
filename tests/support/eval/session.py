"""Triple-store session contract for the evaluation harness.

A *store session* is a live triple store (started in a container by an
evaluation-tier fixture) that the parity/perf runners exercise via
``HttpxSparqlStore``. ``StoreSession`` is the only interface the harness
consumes; each adapter module owns its container lifecycle behind a ``start()``
context manager and is registered in ``support.eval.stores`` (see ADR-0022).

This module also hosts the plumbing every HTTP store adapter shares: the
readiness poll, the error-raising response check, per-graph Graph Store
Protocol serialization, and the read-back checks that turn silent store-side
data loss into a loud infra error instead of misleading parity rows.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol
from urllib.parse import quote

import httpx
from rdflib import ConjunctiveGraph, Dataset, Graph
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID

from fastshaql.core import decode_sparql_results

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


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


def gsp_payloads(graph: Graph) -> Iterator[tuple[str, str, int]]:
    """Serialize *graph* into per-graph GSP PUT payloads: ``(query, turtle,
    triple_count)`` — the count is the read-back expectation (see
    :func:`gsp_triple_count`).

    A ``Dataset`` (multi-graph) becomes one ``?graph=<iri>`` payload per named
    graph plus one ``?default=`` payload for its unnamed graph; a plain
    ``Graph`` a single ``?default=`` payload. Per-graph Turtle only — never
    TriG/N-Quads to a GSP target: Oxigraph rejects it with a 400 that
    *destructively empties the target graph*, and Fuseki accepts it but
    silently drops the named-graph block (ADR-0022).
    """
    if not isinstance(graph, ConjunctiveGraph):
        yield "default=", graph.serialize(format="turtle"), len(graph)
        return
    # Dataset.graphs() is the non-deprecated spelling of ConjunctiveGraph.contexts().
    contexts = graph.graphs() if isinstance(graph, Dataset) else graph.contexts()
    for context in contexts:
        turtle = context.serialize(format="turtle")
        if context.identifier == DATASET_DEFAULT_GRAPH_ID:
            yield "default=", turtle, len(context)
        else:
            yield f"graph={quote(str(context.identifier))}", turtle, len(context)


def triple_total(graph: Graph) -> int:
    """Total triples in *graph* — per context for a dataset (quad count)."""
    if not isinstance(graph, ConjunctiveGraph):
        return len(graph)
    # Dataset.graphs() is the non-deprecated spelling of .contexts().
    contexts = graph.graphs() if isinstance(graph, Dataset) else graph.contexts()
    return sum(len(context) for context in contexts)


def gsp_triple_count(client: httpx.Client, store_url: str, target: str) -> int:
    """Read one GSP target back and count its triples (verify-after-load).

    Deliberately GSP, not SPARQL: the count must not depend on the store's
    no-``FROM`` default-graph contract (ADR-0011) — the same reason the loads
    themselves are per-graph GSP PUTs.
    """
    response = client.get(f"{store_url}?{target}", headers={"Accept": "text/turtle"})
    check(response)
    return len(Graph().parse(data=response.text, format="turtle"))


def sparql_triple_count(client: httpx.Client, query_endpoint: str) -> int:
    """``COUNT(*)`` over the union default graph (QLever's load check — its
    union contract makes the plain BGP the whole dataset)."""
    response = client.post(
        query_endpoint,
        content=b"SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }",
        headers={
            "Content-Type": "application/sparql-query",
            "Accept": "application/sparql-results+json",
        },
    )
    check(response)
    return int(decode_sparql_results(response.content)[0]["n"])


def verify_loaded(store: str, expected: int, actual: int) -> None:
    """Raise when a load read-back disagrees with what was sent."""
    if actual != expected:
        raise RuntimeError(
            f"{store}: load verification failed — sent {expected} triples, "
            f"read back {actual}"
        )
