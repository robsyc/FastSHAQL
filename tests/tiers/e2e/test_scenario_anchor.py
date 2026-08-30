"""Scenario correctness anchors (ADR-0021).

Each scenario's small-scale anchor data is validated against its committed
``expected.json`` via the in-memory store — the correctness floor for generated
data. Full-scale parity/perf against GraphDB lives in ``tests/tiers/evaluation/``.
"""

from __future__ import annotations

import pytest

from support.runners import run_case
from support.scenarios import SCENARIOS

SCENARIO_ANCHORS = tuple(SCENARIOS.values())


@pytest.mark.parametrize("scenario", SCENARIO_ANCHORS, ids=lambda s: s.name)
async def test_scenario_anchor(scenario) -> None:
    data = scenario.data_at(scenario.anchor_scale)
    for case in scenario.cases:
        await run_case(scenario, case, data)
