"""Execution pipeline — ``core/execution/``.

Integration: exercises resolver wiring, context injection, and error handling.
Full-pipeline acceptance lives in ``tests/tiers/e2e/``; converter logic in
``tests/tiers/unit/execution/test_converter_scalars.py`` and
``tests/tiers/unit/execution/test_converter_relationships.py``.

Order: resolver wiring → context injection → error handling → store concurrency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

THINGS_QUERY = "{ things { iri label } }"


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
    assert result.data == {"things": []}


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
    query = "{ a: things { iri } b: things { iri } c: things { iri } }"
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
    result = await execute(schema, "{ things { label } }", store)
    assert result.errors is None
    assert result.data == {
        "things": [
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
        "{ persons { name bio } }",
        store,
        query_context=QueryContext(lang_tags=("en",)),
    )

    assert result.errors is None
    alice_data = next(p for p in result.data["persons"] if p["name"] == "Alice")
    assert alice_data["bio"] == ["Hello"]


async def test_execute_records_metrics_when_attached(
    minimal_registry: ShapeRegistry,
    minimal_data_graph: Graph,
) -> None:
    from fastshaql.core.execution import ExecutionMetrics, execute_query
    from support.graphql_utils import root_field_node, shape_for_root_field

    store = InMemoryStore(minimal_data_graph)
    field_node = root_field_node("{ things { label } }")
    shape = shape_for_root_field(minimal_registry, field_node.name.value)
    metrics = ExecutionMetrics()
    ctx = ResolverContext(store=store, metrics=metrics)
    await execute_query(shape, field_node, minimal_registry, ctx)
    assert metrics.translate_ms >= 0.0
    assert metrics.store_ms >= 0.0
    assert metrics.convert_ms >= 0.0


async def test_execute_query_context_lang_no_match_drops_field_keeps_entity(
    filters_registry: ShapeRegistry,
    filters_data_graph: Graph,
) -> None:
    schema = build_executable_schema(filters_registry)
    store = InMemoryStore(filters_data_graph)
    result = await execute(
        schema,
        "{ persons { name bio } }",
        store,
        query_context=QueryContext(lang_tags=("de",)),
    )

    assert result.errors is None
    alice_data = next(p for p in result.data["persons"] if p["name"] == "Alice")
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
    assert result.data == {"things": [{"iri": str(EX["thing-1"]), "label": "Alpha"}]}


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
    labels = {row["label"] for row in result.data["things"]}
    assert labels == {"Alpha", "Beta"}


async def test_execute_no_read_graphs_unnamed_only_when_default_union_false(
    minimal_registry: ShapeRegistry,
) -> None:
    """No ``FROM`` + ``default_union=False`` → only the (empty) default graph."""
    schema = build_executable_schema(minimal_registry)
    store = InMemoryStore(_named_graph_dataset(default_union=False))
    result = await execute(schema, THINGS_QUERY, store)

    assert result.errors is None
    assert result.data == {"things": []}


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
    labels = {row["label"] for row in result.data["things"]}
    assert labels == {"Alpha", "Beta"}
