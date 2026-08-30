"""Scenario performance-degradation sweep (report-only — ADR-0022/0021).

Each scenario runs across its declared scale axis; materialised SPARQL rows and
per-phase latency percentiles (translate / store / convert) are recorded in
``evaluation-report.json``. No thresholds — benchmarks are CI-flaky; nightly /
manual probe (``just eval``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fastshaql.core.execution import ExecutionMetrics, ResolverContext, execute_query
from support.cases import registry_for_path
from support.eval.report import PercentileTimings, get_report
from support.graphql_utils import root_field_node, shape_for_root_field
from support.runners import RecordingStore
from support.scenarios import SCENARIOS, Scenario

if TYPE_CHECKING:
    from support.eval.graphdb import GraphDbSession

pytest.importorskip("testcontainers")

_WARMUP = 2
_SAMPLES = 10


def _percentile(sorted_samples: list[float], pct: float) -> float:
    if not sorted_samples:
        return 0.0
    idx = round(pct * (len(sorted_samples) - 1))
    return sorted_samples[min(idx, len(sorted_samples) - 1)]


def _percentiles(samples: list[float]) -> PercentileTimings:
    ordered = sorted(samples)
    return PercentileTimings(
        p50=_percentile(ordered, 0.50),
        p95=_percentile(ordered, 0.95),
        p99=_percentile(ordered, 0.99),
    )


@pytest.mark.parametrize("scenario", tuple(SCENARIOS.values()), ids=lambda s: s.name)
async def test_scenario_perf_degradation(
    graphdb_session: GraphDbSession,
    graphdb_store,
    scenario: Scenario,
) -> None:
    case = scenario.load_case(scenario.cases[0])
    registry = registry_for_path(scenario.shapes_path())
    field_node = root_field_node(case.query)
    shape = shape_for_root_field(registry, field_node.name.value)

    for scale in scenario.sweep:
        graphdb_session.load_graph(scenario.data_at(scale))
        store = RecordingStore(graphdb_store)

        for _ in range(_WARMUP):
            metrics = ExecutionMetrics()
            ctx = ResolverContext(
                store=store,
                query_context=case.query_context,
                metrics=metrics,
            )
            await execute_query(shape, field_node, registry, ctx)

        store_samples: list[float] = []
        convert_samples: list[float] = []
        translate_ms = 0.0
        rows = 0
        entities = 0

        for i in range(_SAMPLES):
            metrics = ExecutionMetrics()
            ctx = ResolverContext(
                store=store,
                query_context=case.query_context,
                metrics=metrics,
            )
            if i == 0:
                store.total_rows = 0
            result = await execute_query(shape, field_node, registry, ctx)
            store_samples.append(metrics.store_ms)
            convert_samples.append(metrics.convert_ms)
            translate_ms = metrics.translate_ms
            if i == 0:
                rows = store.total_rows
                entities = len(result)

        get_report().add_perf(
            scenario=scenario.name,
            scale=scale.label,
            rows=rows,
            entities=entities,
            translate_ms=translate_ms,
            store=_percentiles(store_samples),
            convert=_percentiles(convert_samples),
        )
