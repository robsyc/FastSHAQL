"""Unit tests for the store-matrix session plumbing (no Docker needed).

``gsp_payloads`` is the portability-critical serializer — per-graph Turtle,
never TriG — and ``selected_stores`` is the ``EVAL_STORE`` seam.
"""

from __future__ import annotations

import pytest

from support.eval.session import gsp_payloads
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
    assert [target for target, _ in payloads] == ["default="]
    body = payloads[0][1]
    assert "L" in body
    # Turtle only — a TriG body would open a graph block.
    assert "{" not in body


def test_gsp_payloads_dataset_splits_named_graphs() -> None:
    payloads = list(gsp_payloads(_dataset_with_named_graphs()))
    targets = [target for target, _ in payloads]
    assert "default=" in targets
    # The named graph IRI survives URL-quoting as a ?graph= target.
    assert "graph=urn%3Aex%3Ag1" in targets
    by_target = dict(payloads)
    assert "Alpha" in by_target["graph=urn%3Aex%3Ag1"]
    assert "Default" in by_target["default="]


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

    payloads = dict(gsp_payloads(ds))
    # rdflib's Dataset.graphs() always appends the (empty) default graph.
    assert set(payloads) == {"graph=urn%3Aex%3Ag1", "default="}
    assert "Alpha" in payloads["graph=urn%3Aex%3Ag1"]
    assert payloads["default="].strip() == ""


def test_gsp_payloads_empty_graph_is_one_empty_default_put() -> None:
    from rdflib import Graph

    payloads = list(gsp_payloads(Graph()))
    assert [target for target, _ in payloads] == ["default="]
    assert payloads[0][1].strip() == ""


def test_store_registry_keys_match_spec_names_and_licenses() -> None:
    """``STORES`` is keyed by each spec's own ``name`` — EVAL_STORE lookups,
    report rows, and divergence keys all lean on that identity."""
    for key, spec in STORES.items():
        assert spec.name == key
        assert spec.license in {"oss", "free"}
