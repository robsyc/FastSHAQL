"""Unit tests for the shipped httpx-backed store (``fastshaql.stores.http``).

Uses ``httpx.MockTransport`` as the HTTP double — the caller-injected client's
transport — so no Docker or real triple store is needed. The import guard's
no-httpx branch is exercised for real by the ``import-guard`` just recipe.
"""

from __future__ import annotations

from io import BytesIO

import httpx
import pytest
from rdflib import Graph, Literal, URIRef

pytest.importorskip("httpx")

from fastshaql.core import SparqlRow, SparqlStore
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
