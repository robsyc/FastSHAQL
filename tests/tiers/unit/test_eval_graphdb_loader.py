"""GraphDB session data loading — serialisation preserves named graphs.

The parity tier loads ``case_set.load_data()`` (a ``Dataset``) into GraphDB via
``GraphDbSession.load_graph``. A ``Dataset`` must be serialised as TriG (Turtle
silently drops named graphs — see ADR-0011), and a plain ``Graph`` as
Turtle. The content type is set to match so GraphDB's RDF4J statements endpoint
routes the payload correctly.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from rdflib import Dataset, Graph, Literal, Namespace, URIRef

from support.eval.graphdb import GraphDbSession

EX = Namespace("http://example.org/")


def _session() -> tuple[GraphDbSession, MagicMock]:
    sess = GraphDbSession(
        base_url="http://gdb", query_endpoint="http://gdb/repositories/x"
    )
    client = MagicMock()
    client.post.return_value.status_code = 200
    client.delete.return_value.status_code = 204
    sess._client = client  # type: ignore[assignment]
    return sess, client


def _dataset_with_named_graphs() -> Dataset:
    ds = Dataset()
    ds.add((EX["thing-default"], EX["label"], Literal("Default")))
    g1 = ds.graph(URIRef("urn:ex:g1"))
    g1.add((EX["thing-1"], EX["label"], Literal("Alpha")))
    return ds


def test_load_graph_serialises_dataset_as_trig() -> None:
    sess, client = _session()
    sess.load_graph(_dataset_with_named_graphs())

    assert client.post.called
    kwargs = client.post.call_args.kwargs
    assert kwargs["headers"]["Content-Type"] == "application/x-trig"
    body = kwargs["content"].decode()
    # Named-graph structure and both graphs' data survive in the TriG payload.
    assert "urn:ex:g1" in body
    assert "Alpha" in body
    assert "Default" in body


def test_load_graph_serialises_plain_graph_as_turtle() -> None:
    sess, client = _session()
    g = Graph()
    g.add((EX["x"], EX["label"], Literal("L")))
    sess.load_graph(g)

    assert client.post.called
    kwargs = client.post.call_args.kwargs
    assert kwargs["headers"]["Content-Type"] == "application/x-turtle"
    body = kwargs["content"].decode()
    assert "L" in body
    # Turtle must not introduce a bnode-named graph block (TriG on a plain Graph would).
    assert "{" not in body


def test_load_graph_clears_before_load() -> None:
    sess, client = _session()
    sess.load_graph(Graph())
    # clear_repository (DELETE) runs before the POST.
    assert client.delete.called
