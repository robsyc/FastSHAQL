"""Scenario performance-degradation sweep (report-only — ADR-0022/0021).

Each scenario runs across its declared scale axis on every selected store
and on the in-memory (rdflib) baseline: whole-operation latency per sample
(``total`` split into ``core`` and the translate / store / http / decode /
convert phases — ``PhaseTimings`` in ``support/eval/report.py`` is the
canonical phase model), plus rows and entities per sample, landed as median
+ p95 in ``evaluation-report.json``. No thresholds — benchmarks are
CI-flaky; nightly / manual probe (``just eval``).
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

import pytest
from graphql import graphql

from fastshaql.core.execution import ExecutionMetrics, InMemoryStore, ResolverContext
from fastshaql.executable import build_executable_schema
from support.cases import registry_for_path
from support.eval.report import PercentileTimings, PhaseTimings, get_report
from support.graphql_utils import root_field_node
from support.runners import RecordingStore
from support.scenarios import SCENARIOS, Scenario

if TYPE_CHECKING:
    from graphql import GraphQLSchema

    from fastshaql.core.execution.store import SparqlStore
    from support.cases import E2eCase
    from support.eval.session import StoreSession
    from support.eval.stores import StoreSpec

pytest.importorskip("testcontainers")

_WARMUP = 2
_SAMPLES = 10

# One bucket per PhaseTimings field — the collector and the schema stay in
# sync because both spell the phase names exactly once, here and in the class.
_PHASES = ("total", "core", "translate", "store", "http", "decode", "convert")

_FlowSamples = defaultdict[str, list[float]]
"""Per-phase operation samples (ms), one entry per measured sample."""


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
    )


def _phase_timings(samples: _FlowSamples) -> PhaseTimings:
    return PhaseTimings(**{phase: _percentiles(samples[phase]) for phase in _PHASES})


async def _sample_flow(
    store: SparqlStore,
    case: E2eCase,
    schema: GraphQLSchema,
    root_field: str,
) -> tuple[_FlowSamples, int, int]:
    """Warm up, then measure ``_SAMPLES`` whole-operation runs on *store*."""
    recording = RecordingStore(store)
    samples: _FlowSamples = defaultdict(list)
    rows = entities = 0
    for i in range(_WARMUP + _SAMPLES):
        metrics = ExecutionMetrics()
        ctx = ResolverContext(
            store=recording, query_context=case.query_context, metrics=metrics
        )
        if i == _WARMUP:
            recording.total_rows = 0
        start = time.perf_counter()
        result = await graphql(schema, case.query, context_value=ctx)
        wall_ms = (time.perf_counter() - start) * 1e3
        assert result.errors is None, result.errors
        assert result.data is not None  # errors are None — narrows the stub type
        if i >= _WARMUP:
            samples["total"].append(wall_ms)
            # Residual per sample (not difference of percentiles): graphql-core
            # parse/validate/resolve-dispatch/format around execute_query.
            samples["core"].append(wall_ms - metrics.execute_ms)
            samples["translate"].append(metrics.translate_ms)
            # The store round trip window: rdflib execution for the in-memory
            # baseline, http+decode for HTTP stores.
            samples["store"].append(metrics.store_ms)
            samples["http"].append(metrics.http_ms)
            samples["decode"].append(metrics.decode_ms)
            samples["convert"].append(metrics.convert_ms)
            if i == _WARMUP:
                rows = recording.total_rows
                entities = len(result.data[root_field])
    return samples, rows, entities


def _flow_inputs(scenario: Scenario) -> tuple[E2eCase, GraphQLSchema, str]:
    case = scenario.load_case(scenario.cases[0])
    registry = registry_for_path(scenario.shapes_path())
    root_field = root_field_node(case.query).name.value
    return case, build_executable_schema(registry), root_field


def _record(
    store_name: str,
    scenario: Scenario,
    scale: str,
    sampled: tuple[_FlowSamples, int, int],
) -> None:
    samples, rows, entities = sampled
    get_report().add_perf(
        store=store_name,
        scenario=scenario.name,
        scale=scale,
        rows=rows,
        entities=entities,
        phases=_phase_timings(samples),
    )


@pytest.mark.parametrize("scenario", tuple(SCENARIOS.values()), ids=lambda s: s.name)
async def test_scenario_perf_degradation(
    store_spec: StoreSpec,
    store_session: StoreSession,
    store: SparqlStore,
    scenario: Scenario,
) -> None:
    case, schema, root_field = _flow_inputs(scenario)
    for scale in scenario.sweep:
        store_session.load_graph(scenario.data_at(scale))
        _record(
            store_spec.name,
            scenario,
            scale.label,
            await _sample_flow(store, case, schema, root_field),
        )


@pytest.mark.parametrize("scenario", tuple(SCENARIOS.values()), ids=lambda s: s.name)
async def test_scenario_perf_baseline(scenario: Scenario) -> None:
    """In-memory (rdflib) baseline rows for the cross-store perf table."""
    case, schema, root_field = _flow_inputs(scenario)
    for scale in scenario.sweep:
        store = InMemoryStore(scenario.data_at(scale))
        _record(
            "in-memory",
            scenario,
            scale.label,
            await _sample_flow(store, case, schema, root_field),
        )
