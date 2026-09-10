"""Unit tests for the store-matrix session plumbing (no Docker needed).

``gsp_payloads`` is the portability-critical serializer — per-graph Turtle,
never TriG — and ``selected_stores`` is the ``EVAL_STORE`` seam. The
read-back helpers (``gsp_triple_count`` / ``sparql_triple_count`` /
``verify_loaded``) are exercised against ``httpx.MockTransport`` doubles.
"""

from __future__ import annotations

import pytest

from support.eval.session import (
    gsp_payloads,
    gsp_triple_count,
    sparql_triple_count,
    triple_total,
    verify_loaded,
)
from support.eval.stores import DEFAULT_STORES, STORES, selected_stores


def _dataset_with_named_graphs():
    from rdflib import Dataset, Literal, Namespace, URIRef

    ex = Namespace("http://example.org/")
    ds = Dataset()
    ds.add((ex["thing-default"], ex["label"], Literal("Default")))
    g1 = ds.graph(URIRef("urn:ex:g1"))
    g1.add((ex["thing-1"], ex["label"], Literal("Alpha")))
    return ds


def test_gsp_payloads_plain_graph_is_one_default_put() -> None:
    from rdflib import Graph, Literal, Namespace

    g = Graph()
    g.add(
        (
            Namespace("http://example.org/")["x"],
            Namespace("http://example.org/")["l"],
            Literal("L"),
        )
    )
    payloads = list(gsp_payloads(g))
    assert [payload[0] for payload in payloads] == ["default="]
    body = payloads[0][1]
    assert "L" in body
    # Turtle only — a TriG body would open a graph block.
    assert "{" not in body
    assert payloads[0][2] == 1  # the read-back expectation travels with it


def test_gsp_payloads_dataset_splits_named_graphs() -> None:
    payloads = list(gsp_payloads(_dataset_with_named_graphs()))
    targets = [payload[0] for payload in payloads]
    assert "default=" in targets
    # The named graph IRI survives URL-quoting as a ?graph= target.
    assert "graph=urn%3Aex%3Ag1" in targets
    by_target = {target: body for target, body, _ in payloads}
    assert "Alpha" in by_target["graph=urn%3Aex%3Ag1"]
    assert "Default" in by_target["default="]
    counts = {target: count for target, _, count in payloads}
    assert counts["default="] == 1
    assert counts["graph=urn%3Aex%3Ag1"] == 1


def test_selected_stores_defaults_to_license_free_set(monkeypatch) -> None:
    monkeypatch.delenv("EVAL_STORE", raising=False)
    assert tuple(spec.name for spec in selected_stores()) == DEFAULT_STORES


def test_selected_stores_parses_comma_separated(monkeypatch) -> None:
    monkeypatch.setenv("EVAL_STORE", "qlever, graphdb")
    assert tuple(spec.name for spec in selected_stores()) == ("qlever", "graphdb")


def test_selected_stores_rejects_unknown_name(monkeypatch) -> None:
    monkeypatch.setenv("EVAL_STORE", "virtuoso")
    with pytest.raises(SystemExit, match="virtuoso"):
        selected_stores()


def test_selected_stores_empty_selection_exits_loudly(monkeypatch) -> None:
    """An explicit-but-empty EVAL_STORE must fail, not collect zero tests
    and look green."""
    monkeypatch.setenv("EVAL_STORE", " , ")
    with pytest.raises(SystemExit, match="selects no stores"):
        selected_stores()


def test_selected_stores_dedupes_repeated_names(monkeypatch) -> None:
    monkeypatch.setenv("EVAL_STORE", "oxigraph,oxigraph, fuseki")
    assert tuple(spec.name for spec in selected_stores()) == ("oxigraph", "fuseki")


def test_gsp_payloads_named_graphs_only_dataset_still_clears_default() -> None:
    """A Dataset with no default-graph content still emits a ``?default=`` PUT.

    The payload body is empty — its job is clearing the target's default graph:
    ``load_graph`` replaces the whole store (clear-first), so stale triples
    from the previous case must be wiped, not retained.
    """
    from rdflib import Dataset, Literal, Namespace, URIRef

    ex = Namespace("http://example.org/")
    ds = Dataset()
    g1 = ds.graph(URIRef("urn:ex:g1"))
    g1.add((ex["a"], ex["label"], Literal("Alpha")))

    payloads = {target: body for target, body, _ in gsp_payloads(ds)}
    # rdflib's Dataset.graphs() always appends the (empty) default graph.
    assert set(payloads) == {"graph=urn%3Aex%3Ag1", "default="}
    assert "Alpha" in payloads["graph=urn%3Aex%3Ag1"]
    assert payloads["default="].strip() == ""


def test_gsp_payloads_empty_graph_is_one_empty_default_put() -> None:
    from rdflib import Graph

    payloads = list(gsp_payloads(Graph()))
    assert [payload[0] for payload in payloads] == ["default="]
    assert payloads[0][1].strip() == ""
    assert payloads[0][2] == 0


def test_store_registry_keys_match_spec_names_and_licenses() -> None:
    """``STORES`` is keyed by each spec's own ``name`` — EVAL_STORE lookups,
    report rows, and divergence keys all lean on that identity."""
    for key, spec in STORES.items():
        assert spec.name == key
        assert spec.license in {"oss", "free"}


def test_triple_total_counts_per_context() -> None:
    from rdflib import Graph, Literal, Namespace

    ex = Namespace("http://example.org/")
    ds = _dataset_with_named_graphs()
    g2 = ds.graph(Namespace("urn:ex:")["g2"])
    g2.add((ex["thing-2"], ex["label"], Literal("Beta")))
    g2.add((ex["thing-2"], ex["label2"], Literal("Gamma")))
    assert triple_total(ds) == 4
    assert triple_total(Graph()) == 0


def test_gsp_triple_count_reads_back_target() -> None:
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://stub/store?default="
        assert request.headers["Accept"] == "text/turtle"
        return httpx.Response(
            200,
            text=(
                '<http://ex/a> <http://ex/l> "L" .\n<http://ex/b> <http://ex/l> "M" .\n'
            ),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert gsp_triple_count(client, "http://stub/store", "default=") == 2


def test_gsp_triple_count_raises_with_error_body() -> None:
    import httpx

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError, match="boom"):
        gsp_triple_count(client, "http://stub/store", "default=")


def test_sparql_triple_count_parses_binding() -> None:
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Content-Type"] == "application/sparql-query"
        assert b"COUNT" in request.content
        return httpx.Response(
            200,
            content=(
                b'{"results": {"bindings": [{"n": {"type": "literal", '
                b'"datatype": "http://www.w3.org/2001/XMLSchema#integer", '
                b'"value": "42"}}]}}'
            ),
            headers={"Content-Type": "application/sparql-results+json"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert sparql_triple_count(client, "http://stub/sparql") == 42


def test_verify_loaded_passes_on_match_and_raises_on_mismatch() -> None:
    verify_loaded("stub", 3, 3)
    with pytest.raises(RuntimeError, match="sent 3 triples, read back 2"):
        verify_loaded("stub", 3, 2)
