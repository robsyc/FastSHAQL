"""Unit tests for the shipped httpx-backed store (``fastshaql.stores.http``).

Uses ``httpx.MockTransport`` as the HTTP double — the caller-injected client's
transport — so no Docker or real triple store is needed. The import guard's
no-httpx branch is exercised for real by the ``import-guard`` just recipe.
The core ``timed`` helper's exception-safety contract is pinned here beside
the other metrics tests.
"""

from __future__ import annotations

from io import BytesIO

import httpx
import pytest
from rdflib import Graph, Literal, URIRef

pytest.importorskip("httpx")

from fastshaql.core import ExecutionMetrics, SparqlRow, SparqlStore
from fastshaql.stores.http import HttpxSparqlStore


def _sparql_json_stub(graph: Graph):
    """Return an httpx transport that answers SPARQL SELECT with JSON results."""

    def handler(request: httpx.Request) -> httpx.Response:
        sparql = request.content.decode()
        result = graph.query(sparql)
        buf = BytesIO()
        result.serialize(buf, format="json")
        return httpx.Response(
            200,
            content=buf.getvalue(),
            headers={"Content-Type": "application/sparql-results+json"},
        )

    return httpx.MockTransport(handler)


async def test_query_decodes_bindings_through_shared_seam() -> None:
    graph = Graph()
    graph.add((URIRef("http://ex/s"), URIRef("http://ex/label"), Literal("Alpha")))

    transport = _sparql_json_stub(graph)
    async with httpx.AsyncClient(transport=transport, base_url="http://stub") as client:
        store = HttpxSparqlStore(client, "http://stub/sparql")
        rows: list[SparqlRow] = await store.query(
            "SELECT ?label WHERE { <http://ex/s> <http://ex/label> ?label }"
        )

    assert isinstance(store, SparqlStore)
    assert len(rows) == 1
    assert rows[0]["label"] == Literal("Alpha")


async def test_query_posts_through_the_caller_supplied_client() -> None:
    # The store owns only the SPARQL protocol shaping: the POST must travel
    # through exactly the client the caller injected, to the configured
    # endpoint, with the query as the body and protocol content types.
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            content=b'{"results": {"bindings": []}}',
            headers={"Content-Type": "application/sparql-results+json"},
        )

    sparql = "SELECT ?s WHERE { ?s ?p ?o }"
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://stub") as client:
        store = HttpxSparqlStore(client, "http://stub/sparql")
        await store.query(sparql)

    assert len(seen) == 1
    request = seen[0]
    assert str(request.url) == "http://stub/sparql"
    assert request.method == "POST"
    assert request.content == sparql.encode()
    assert request.headers["Content-Type"] == "application/sparql-query"
    assert request.headers["Accept"] == "application/sparql-results+json"


async def test_http_error_raises() -> None:
    # A 4xx/5xx from the endpoint surfaces as ``httpx.HTTPStatusError`` with
    # the status and body — not as a decode error on the error payload.
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="repository unavailable")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://stub") as client:
        store = HttpxSparqlStore(client, "http://stub/sparql")
        with pytest.raises(
            httpx.HTTPStatusError,
            match="SPARQL endpoint returned 500: repository unavailable",
        ):
            await store.query("SELECT ?x WHERE { ?x ?y ?z }")


async def test_metrics_records_http_and_decode_split(monkeypatch) -> None:
    # The optional metrics argument splits the store phase at its wire seams:
    # http_ms covers request→response, decode_ms covers body→rows. A fake
    # clock (advanced by the transport handler and the decode wrapper) pins
    # both phases to exact values — timing-scale mutants can't hide behind
    # `> 0` asserts.
    import fastshaql.stores.http as http_module

    clock = {"now": 100.0}
    monkeypatch.setattr(http_module.time, "perf_counter", lambda: clock["now"])

    def handler(_request: httpx.Request) -> httpx.Response:
        clock["now"] += 0.5  # the simulated round trip
        return httpx.Response(
            200,
            content=b'{"results": {"bindings": []}}',
            headers={"Content-Type": "application/sparql-results+json"},
        )

    real_decode = http_module.decode_sparql_results

    def slow_decode(raw: bytes) -> list:
        clock["now"] += 0.25  # the simulated wire decode
        return real_decode(raw)

    monkeypatch.setattr(http_module, "decode_sparql_results", slow_decode)

    metrics = ExecutionMetrics()
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://stub") as client:
        store = HttpxSparqlStore(client, "http://stub/sparql")
        await store.query("SELECT ?s WHERE { ?s ?p ?o }", metrics=metrics)

    assert metrics.http_ms == pytest.approx(500.0)
    assert metrics.decode_ms == pytest.approx(250.0)


async def test_http_ms_recorded_on_error_response(monkeypatch) -> None:
    # A failing round trip still accounts its transport time before raising —
    # same fake-clock pinning as the success-path test, so the assert is exact
    # (the start reference is before the POST), never a timing race.
    import fastshaql.stores.http as http_module

    clock = {"now": 100.0}
    monkeypatch.setattr(http_module.time, "perf_counter", lambda: clock["now"])

    def handler(_request: httpx.Request) -> httpx.Response:
        clock["now"] += 0.25  # the simulated (failing) round trip
        return httpx.Response(503, text="overloaded")

    metrics = ExecutionMetrics()
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://stub") as client:
        store = HttpxSparqlStore(client, "http://stub/sparql")
        with pytest.raises(httpx.HTTPStatusError):
            await store.query("SELECT ?x WHERE { ?x ?y ?z }", metrics=metrics)

    assert metrics.http_ms == pytest.approx(250.0)
    assert metrics.decode_ms == 0.0


def test_timed_records_phase_when_body_raises(monkeypatch) -> None:
    # ``timed``'s try/finally still accounts the phase as the exception
    # unwinds — a failing store round trip keeps its ``store_ms``. Same
    # fake-clock pinning as the metrics tests above, so the assert is exact.
    import fastshaql.core.execution.store as store_module
    from fastshaql.core.execution.store import timed

    clock = {"now": 100.0}
    monkeypatch.setattr(store_module.time, "perf_counter", lambda: clock["now"])

    metrics = ExecutionMetrics()

    def explode() -> None:
        clock["now"] += 0.75  # the simulated failing phase
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"), timed(metrics, "store_ms"):
        explode()

    assert metrics.store_ms == pytest.approx(750.0)
