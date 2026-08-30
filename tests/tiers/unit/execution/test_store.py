"""Store implementations for query execution — ``core/execution/store.py``.

Unit tier: ``InMemoryStore`` (rdflib-backed, async ``query``), the in-process
``SparqlStore`` consumed by the execution layer. The HTTP-backed store ships
behind the ``httpx`` extra (``tests/tiers/unit/stores/``).
"""

from __future__ import annotations

from rdflib import Graph, Literal, URIRef

from fastshaql.core.execution.store import InMemoryStore


async def test_in_memory_store_query_returns_bindings() -> None:
    graph = Graph()
    graph.add((URIRef("http://ex/s"), URIRef("http://ex/label"), Literal("Alpha")))

    store = InMemoryStore(graph)
    rows = await store.query(
        "SELECT ?label WHERE { <http://ex/s> <http://ex/label> ?label }"
    )

    assert len(rows) == 1
    assert rows[0]["label"] == Literal("Alpha")
