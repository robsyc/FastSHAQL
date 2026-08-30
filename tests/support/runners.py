"""Declarative-case runners: translate or execute a fixture case.

``translate_case`` produces the SPARQL translation for inline inspection
(integration tier); ``run_case`` executes the full pipeline and golden-asserts
(e2e tier). Both read parsed inputs from ``support.cases`` factories so there is
exactly one parse path per case set. See ADR-0021.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastshaql.core.translation import VariableMap, translate_query
from support.cases import CaseSource, registry_for_path
from support.goldens import canonicalize
from support.graphql_utils import root_field_node, shape_for_root_field

if TYPE_CHECKING:
    from rdflib import Graph

    from fastshaql.core.execution.store import SparqlRow, SparqlStore
    from fastshaql.core.ir import NodeShapeIR
    from fastshaql.core.registry import ShapeRegistry
    from fastshaql.core.translation.variables import TranslationResult


@dataclass(frozen=True)
class TranslateCaseResult:
    """Translation output for a declarative case."""

    translation: TranslationResult
    shape: NodeShapeIR
    registry: ShapeRegistry

    @property
    def var_map(self) -> VariableMap:
        return self.translation.var_map


class RecordingStore:
    """Wraps a ``SparqlStore`` and records every SPARQL string executed."""

    def __init__(self, inner: SparqlStore) -> None:
        self._inner = inner
        self.queries: list[str] = []
        self.total_rows: int = 0

    async def query(self, sparql: str) -> list[SparqlRow]:
        self.queries.append(sparql)
        rows = await self._inner.query(sparql)
        self.total_rows += len(rows)
        return rows


def translate_case(case_set: CaseSource, case: str) -> TranslateCaseResult:
    """Translate a declarative case's GraphQL query against its shapes."""
    registry = registry_for_path(case_set.shapes_path())
    case_files = case_set.load_case(case)
    field_node = root_field_node(case_files.query)
    shape = shape_for_root_field(registry, field_node.name.value)
    translation = translate_query(
        shape,
        field_node,
        registry,
        query_context=case_files.query_context,
    )
    return TranslateCaseResult(translation=translation, shape=shape, registry=registry)


async def run_case(case_set: CaseSource, case: str, data: Graph) -> None:
    """Execute a declarative e2e case (schema build + GraphQL + JSON/SPARQL assertions).

    *data* is an explicit dependency: the caller controls provenance — committed
    file via ``CaseSet.load_data()`` (cached via ``data_graph_for``) or generated
    via ``Scenario.data_at()``.
    """
    from graphql import graphql

    from fastshaql.core.execution import InMemoryStore, ResolverContext
    from fastshaql.executable import build_executable_schema

    registry = registry_for_path(case_set.shapes_path())
    case_files = case_set.load_case(case)

    schema = build_executable_schema(registry)
    store = RecordingStore(InMemoryStore(data))
    ctx = ResolverContext(store=store, query_context=case_files.query_context)
    result = await graphql(schema, case_files.query, context_value=ctx)

    assert result.errors is None, result.errors
    assert case_files.expected_json is not None
    assert canonicalize(result.formatted) == canonicalize(case_files.expected_json)
    if case_files.expected_sparql is not None:
        assert store.queries[0] == case_files.expected_sparql
        assert len(store.queries) == 1


async def run_case_on_store(
    case_set: CaseSource,
    case: str,
    store: SparqlStore,
) -> None:
    """Execute a declarative case against *store* and golden-assert JSON only."""
    from graphql import graphql

    from fastshaql.core.execution import ResolverContext
    from fastshaql.executable import build_executable_schema

    registry = registry_for_path(case_set.shapes_path())
    case_files = case_set.load_case(case)

    schema = build_executable_schema(registry)
    ctx = ResolverContext(store=store, query_context=case_files.query_context)
    result = await graphql(schema, case_files.query, context_value=ctx)

    assert result.errors is None, result.errors
    assert case_files.expected_json is not None
    assert canonicalize(result.formatted) == canonicalize(case_files.expected_json)
