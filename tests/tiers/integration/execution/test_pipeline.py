"""Execution pipeline — ``core/execution/``.

Integration: exercises resolver wiring, context injection, and error handling.
Full-pipeline acceptance lives in ``tests/tiers/e2e/``; converter logic in
``tests/tiers/unit/execution/test_converter_scalars.py`` and
``tests/tiers/unit/execution/test_converter_relationships.py``.

Order: resolver wiring → context injection → error handling → store concurrency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from graphql import graphql
from rdflib import RDF, Dataset, Graph, Literal, Namespace, URIRef

from fastshaql.core.execution import InMemoryStore, ResolverContext
from fastshaql.core.kernel.context import QueryContext
from fastshaql.executable import build_executable_schema

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry

EX = Namespace("http://example.org/")
G1 = URIRef("urn:ex:g1")
G2 = URIRef("urn:ex:g2")

THINGS_QUERY = "{ thing { iri label } }"


async def execute(schema, query: str, store: InMemoryStore, *, query_context=None):
    ctx = ResolverContext(store=store, query_context=query_context)
    return await graphql(schema, query, context_value=ctx)


async def test_execute_empty_graph_returns_empty_list(
    minimal_registry: ShapeRegistry,
) -> None:
    schema = build_executable_schema(minimal_registry)
    store = InMemoryStore(Graph())
    result = await execute(schema, THINGS_QUERY, store)
    assert result.errors is None
    assert result.data == {"thing": []}


async def test_execute_concurrent_sibling_fields_serialize_on_rdflib(
    minimal_registry: ShapeRegistry,
) -> None:
    """Aliased sibling root fields resolve concurrently on one shared
    ``InMemoryStore`` — rdflib's SPARQL parser is not thread-safe, so the
    store serializes queries (see its class docstring). Without the lock,
    concurrent parses intermittently corrupt parser state into random
    ``BadSyntax`` errors on byte-identical, valid queries."""
    schema = build_executable_schema(minimal_registry)
    data = Graph()
    data.add((EX["thing-1"], RDF.type, EX["Thing"]))
    store = InMemoryStore(data)
    query = "{ a: thing { iri } b: thing { iri } c: thing { iri } }"
    expected = {letter: [{"iri": str(EX["thing-1"])}] for letter in "abc"}
    for _ in range(5):
        result = await execute(schema, query, store)
        assert result.errors is None, result.errors
        assert result.data == expected


async def test_execute_strips_iri_when_not_selected(
    minimal_registry: ShapeRegistry,
    minimal_data_graph: Graph,
) -> None:
    schema = build_executable_schema(minimal_registry)
    store = InMemoryStore(minimal_data_graph)
    result = await execute(schema, "{ thing { label } }", store)
    assert result.errors is None
    assert result.data == {
        "thing": [
            {"label": "Alpha"},
            {"label": "Beta"},
        ]
    }


async def test_execute_requires_resolver_context_store(
    minimal_registry: ShapeRegistry,
) -> None:
    schema = build_executable_schema(minimal_registry)
    result = await graphql(schema, THINGS_QUERY, context_value=object())
    assert result.data is None
    assert result.errors is not None
    assert len(result.errors) == 1
    assert "ResolverContext" in str(result.errors[0].message)


async def test_execute_query_context_lang_filters_multi_language_data(
    filters_registry: ShapeRegistry,
    filters_data_graph: Graph,
) -> None:
    schema = build_executable_schema(filters_registry)
    store = InMemoryStore(filters_data_graph)
    result = await execute(
        schema,
        "{ person { name bio } }",
        store,
        query_context=QueryContext(lang_tags=("en",)),
    )

    assert result.errors is None
    alice_data = next(p for p in result.data["person"] if p["name"] == "Alice")
    assert alice_data["bio"] == ["Hello"]


async def test_execute_records_metrics_when_attached(
    minimal_registry: ShapeRegistry,
    minimal_data_graph: Graph,
) -> None:
    from fastshaql.core.execution import ExecutionMetrics, execute_query
    from support.graphql_utils import root_field_node, shape_for_root_field

    store = InMemoryStore(minimal_data_graph)
    field_node = root_field_node("{ thing { label } }")
    shape = shape_for_root_field(minimal_registry, field_node.name.value)
    metrics = ExecutionMetrics()
    ctx = ResolverContext(store=store, metrics=metrics)
    await execute_query(shape, field_node, minimal_registry, ctx)
    # Strictly positive: every phase does real work here, and the dataclass
    # defaults are 0.0 — a `>=` assert would pass with metrics never wired.
    assert metrics.translate_ms > 0.0
    assert metrics.store_ms > 0.0
    assert metrics.convert_ms > 0.0
    # total_ms wraps the whole call: the phases are contained in it.
    assert metrics.total_ms >= (
        metrics.translate_ms + metrics.store_ms + metrics.convert_ms
    )


async def test_execute_passes_metrics_to_store_when_attached(
    minimal_registry: ShapeRegistry,
) -> None:
    """Profiling runs forward the metrics object to the store's ``query`` —
    the seam HTTP-backed stores use to record the http/decode split."""
    from fastshaql.core.execution import (
        ExecutionMetrics,
        ResolverContext,
        execute_query,
    )
    from support.graphql_utils import root_field_node, shape_for_root_field

    seen: list[tuple[str, object]] = []

    class MetricsSpyStore:
        async def query(self, sparql: str, metrics: object = None) -> list[dict]:
            seen.append((sparql, metrics))
            return []

    field_node = root_field_node("{ thing { label } }")
    shape = shape_for_root_field(minimal_registry, field_node.name.value)
    metrics = ExecutionMetrics()
    ctx = ResolverContext(store=MetricsSpyStore(), metrics=metrics)
    await execute_query(shape, field_node, minimal_registry, ctx)
    assert len(seen) == 1
    assert "SELECT" in seen[0][0]  # the rendered query travels with it
    assert seen[0][1] is metrics


async def test_execute_leaves_pre_widening_stores_working_without_metrics(
    minimal_registry: ShapeRegistry,
) -> None:
    """No metrics attached → the store is called exactly as before the
    ``metrics`` widening: one-argument ``query`` implementations keep working
    in production (ADR-0022)."""
    from fastshaql.core.execution import ResolverContext, execute_query
    from support.graphql_utils import root_field_node, shape_for_root_field

    class LegacyOneArgStore:
        async def query(self, sparql: str) -> list[dict]:  # noqa: ARG002 — the shape is the point
            return []

    field_node = root_field_node("{ thing { label } }")
    shape = shape_for_root_field(minimal_registry, field_node.name.value)
    ctx = ResolverContext(
        store=LegacyOneArgStore(),  # ty: ignore[invalid-argument-type]
    )
    result = await execute_query(shape, field_node, minimal_registry, ctx)
    assert result == []


async def test_execute_legacy_store_with_metrics_raises_typeerror(
    minimal_registry: ShapeRegistry,
) -> None:
    """Metrics attached → the same one-arg ``query`` cannot serve the run:
    the failure is a loud ``TypeError``, never a silently unprofiled one
    (ADR-0022) — the complement of the no-metrics compat test above."""
    from fastshaql.core.execution import (
        ExecutionMetrics,
        ResolverContext,
        execute_query,
    )
    from support.graphql_utils import root_field_node, shape_for_root_field

    class LegacyOneArgStore:
        async def query(self, sparql: str) -> list[dict]:  # noqa: ARG002 — the shape is the point
            return []

    field_node = root_field_node("{ thing { label } }")
    shape = shape_for_root_field(minimal_registry, field_node.name.value)
    ctx = ResolverContext(
        store=LegacyOneArgStore(),  # ty: ignore[invalid-argument-type]
        metrics=ExecutionMetrics(),
    )
    with pytest.raises(TypeError, match="unexpected keyword argument 'metrics'"):
        await execute_query(shape, field_node, minimal_registry, ctx)


async def test_execute_query_context_lang_no_match_drops_field_keeps_entity(
    filters_registry: ShapeRegistry,
    filters_data_graph: Graph,
) -> None:
    schema = build_executable_schema(filters_registry)
    store = InMemoryStore(filters_data_graph)
    result = await execute(
        schema,
        "{ person { name bio } }",
        store,
        query_context=QueryContext(lang_tags=("de",)),
    )

    assert result.errors is None
    alice_data = next(p for p in result.data["person"] if p["name"] == "Alice")
    assert alice_data["bio"] == []


def _named_graph_dataset(default_union: bool = False) -> Dataset:
    """Data only in named graphs g1/g2; the default graph is empty.

    *default_union* is the instance lever that governs the no-``FROM`` default
    graph (ADR-0011): ``False`` → only the unnamed default (empty
    here); ``True`` → union of all graphs. Explicit ``FROM`` isolates under
    either value (see ``test_named_graph_isolation.py``).
    """
    ds = Dataset(default_union=default_union)
    thing = EX["Thing"]
    ds.graph(G1).add((EX["thing-1"], RDF.type, thing))
    ds.graph(G1).add((EX["thing-1"], EX.label, Literal("Alpha")))
    ds.graph(G2).add((EX["thing-2"], RDF.type, thing))
    ds.graph(G2).add((EX["thing-2"], EX.label, Literal("Beta")))
    return ds


async def test_execute_read_graphs_scopes_to_named_graph(
    minimal_registry: ShapeRegistry,
) -> None:
    schema = build_executable_schema(minimal_registry)
    store = InMemoryStore(_named_graph_dataset())
    result = await execute(
        schema,
        THINGS_QUERY,
        store,
        query_context=QueryContext(read_graphs=("urn:ex:g1",)),
    )

    assert result.errors is None
    assert result.data == {"thing": [{"iri": str(EX["thing-1"]), "label": "Alpha"}]}


async def test_execute_read_graphs_merge_multiple_graphs(
    minimal_registry: ShapeRegistry,
) -> None:
    schema = build_executable_schema(minimal_registry)
    store = InMemoryStore(_named_graph_dataset())
    result = await execute(
        schema,
        THINGS_QUERY,
        store,
        query_context=QueryContext(read_graphs=("urn:ex:g1", "urn:ex:g2")),
    )

    assert result.errors is None
    labels = {row["label"] for row in result.data["thing"]}
    assert labels == {"Alpha", "Beta"}


async def test_execute_no_read_graphs_unnamed_only_when_default_union_false(
    minimal_registry: ShapeRegistry,
) -> None:
    """No ``FROM`` + ``default_union=False`` → only the (empty) default graph."""
    schema = build_executable_schema(minimal_registry)
    store = InMemoryStore(_named_graph_dataset(default_union=False))
    result = await execute(schema, THINGS_QUERY, store)

    assert result.errors is None
    assert result.data == {"thing": []}


async def test_execute_no_read_graphs_union_when_default_union_true(
    minimal_registry: ShapeRegistry,
) -> None:
    """No ``FROM`` + ``default_union=True`` → union of all named graphs.

    Pins the in-process contract ``load_data()`` adopts (ADR-0011): the
    bare no-``FROM`` query sees the union of every graph, matching GraphDB's
    hardcoded default-graph semantics. Explicit ``FROM`` isolation is pinned by
    the two tests above and by the declarative ``named_graphs`` e2e cases.
    """
    schema = build_executable_schema(minimal_registry)
    store = InMemoryStore(_named_graph_dataset(default_union=True))
    result = await execute(schema, THINGS_QUERY, store)

    assert result.errors is None
    labels = {row["label"] for row in result.data["thing"]}
    assert labels == {"Alpha", "Beta"}
