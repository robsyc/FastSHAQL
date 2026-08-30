"""Evidence: the rdflib ``FROM`` / no-``FROM`` truth table.

Backs the ADR-0011 contract: explicit ``FROM`` isolates its
listed graphs unconditionally — the ``datasetClause`` path in
``rdflib.plugins.sparql.sparql`` (the ``if datasetClause:`` branch) copies the
listed graphs into a fresh default graph and **never consults** the global
``SPARQL_DEFAULT_GRAPH_UNION`` or the instance ``Dataset.default_union``.

The no-``FROM`` default graph is the *interaction* of two levers:

- the **global** ``SPARQL_DEFAULT_GRAPH_UNION`` — picks ``self.graph = dataset``
  (True) vs ``self.graph = dataset.default_context`` (False);
- the **instance** ``Dataset.default_union`` — when ``self.graph`` *is* the
  dataset, it governs whether ``Dataset.triples`` (``graph.py``) yields the union
  of all graphs or only the default context.

Removing the production global (so rdflib's default ``True`` stands) makes
``Dataset.default_union`` the sole lever — the regime fastshaql ships. The
``test_global_false_overrides…`` case is the smoking gun: with the pre-removal
global=False, ``default_union=True`` is silently overridden to default-only,
which is exactly why the global must be *removed* (not left) once
``load_data()`` adopts ``default_union=True``.

See CONTEXT.md: **No-``FROM`` default graph**, **Default graph**, **Dataset clause**.
"""

from __future__ import annotations

import pytest
import rdflib.plugins.sparql
from rdflib import RDF, Dataset, Literal, Namespace, URIRef

EX = Namespace("http://example.org/")
G1 = URIRef("urn:ex:g1")
G2 = URIRef("urn:ex:g2")
LABEL = EX["label"]

FROM_G1 = (
    "SELECT DISTINCT ?label FROM <urn:ex:g1> "
    "WHERE { ?s <http://example.org/label> ?label }"
)
NO_FROM = "SELECT DISTINCT ?label WHERE { ?s <http://example.org/label> ?label }"


def _multi_graph_dataset(default_union: bool) -> Dataset:
    """One triple in the default graph and one entity per named graph (g1/g2)."""
    ds = Dataset(default_union=default_union)
    ds.add((EX["thing-default"], RDF.type, EX["Thing"]))
    ds.add((EX["thing-default"], LABEL, Literal("Default")))
    g1 = ds.graph(G1)
    g1.add((EX["thing-1"], RDF.type, EX["Thing"]))
    g1.add((EX["thing-1"], LABEL, Literal("Alpha")))
    g2 = ds.graph(G2)
    g2.add((EX["thing-2"], RDF.type, EX["Thing"]))
    g2.add((EX["thing-2"], LABEL, Literal("Beta")))
    return ds


def _labels(dataset: Dataset, sparql: str) -> set[str]:
    return {str(row.asdict()["label"]) for row in dataset.query(sparql)}


@pytest.mark.parametrize("global_union", [False, True])
@pytest.mark.parametrize("default_union", [False, True])
def test_from_isolates_listed_graph_under_every_union_combination(
    monkeypatch: pytest.MonkeyPatch,
    global_union: bool,
    default_union: bool,
) -> None:
    """``FROM <g1>`` returns only g1's triples under all 4 flag combinations."""
    monkeypatch.setattr(
        rdflib.plugins.sparql, "SPARQL_DEFAULT_GRAPH_UNION", global_union
    )
    labels = _labels(_multi_graph_dataset(default_union), FROM_G1)
    assert labels == {"Alpha"}


def test_no_from_union_when_default_union_true_under_global_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Global at rdflib default (True) + ``default_union=True`` → union of all."""
    monkeypatch.setattr(rdflib.plugins.sparql, "SPARQL_DEFAULT_GRAPH_UNION", True)
    labels = _labels(_multi_graph_dataset(default_union=True), NO_FROM)
    assert labels == {"Default", "Alpha", "Beta"}


def test_no_from_default_only_when_default_union_false_under_global_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Global at rdflib default (True) + ``default_union=False`` → default only."""
    monkeypatch.setattr(rdflib.plugins.sparql, "SPARQL_DEFAULT_GRAPH_UNION", True)
    labels = _labels(_multi_graph_dataset(default_union=False), NO_FROM)
    assert labels == {"Default"}


def test_global_false_overrides_default_union_true_to_default_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pre-removal global=False forces default-only even when default_union=True.

    This is why the global must be *removed* (reverting to rdflib's True default)
    rather than left in place once ``load_data()`` adopts ``default_union=True``:
    a False global silently pins the no-``FROM`` graph to the default context,
    defeating the union contract regardless of the instance flag.
    """
    monkeypatch.setattr(rdflib.plugins.sparql, "SPARQL_DEFAULT_GRAPH_UNION", False)
    labels = _labels(_multi_graph_dataset(default_union=True), NO_FROM)
    assert labels == {"Default"}
