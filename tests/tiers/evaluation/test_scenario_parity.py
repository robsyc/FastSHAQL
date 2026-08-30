"""Scenario parity against GraphDB CE at the anchor scale (ADR-0022/0021).

The generated anchor data is loaded into a real triple store and the response
compared order-independently to the committed ``expected.json`` — the real-store
correctness check for generated-data scenarios.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from support.runners import run_case_on_store
from support.scenarios import SCENARIOS

if TYPE_CHECKING:
    from support.eval.graphdb import GraphDbSession

pytest.importorskip("testcontainers")


@pytest.mark.parametrize("scenario", tuple(SCENARIOS.values()), ids=lambda s: s.name)
async def test_scenario_parity(
    graphdb_session: GraphDbSession,
    graphdb_store,
    scenario,
) -> None:
    graphdb_session.load_graph(scenario.data_at(scenario.anchor_scale))
    for case in scenario.cases:
        await run_case_on_store(scenario, case, graphdb_store)
