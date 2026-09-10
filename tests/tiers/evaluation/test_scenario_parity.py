"""Scenario parity across the store matrix at the anchor scale (ADR-0022/0021).

The generated anchor data is loaded into each store and every scenario case is
compared order-independently to the committed ``expected.json`` — the
real-store correctness check for generated-data scenarios. Outcomes land in
the report's parity matrix (a diverging scenario case needs a set-level
known-divergence entry: its cases run inside this one test).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from support.eval.parity import check_parity
from support.scenarios import SCENARIOS

if TYPE_CHECKING:
    from fastshaql.core.execution.store import SparqlStore
    from support.eval.session import StoreSession
    from support.eval.stores import StoreSpec
    from support.scenarios import Scenario

pytest.importorskip("testcontainers")


@pytest.mark.parametrize("scenario", tuple(SCENARIOS.values()), ids=lambda s: s.name)
async def test_scenario_parity(
    store_spec: StoreSpec,
    store_session: StoreSession,
    store: SparqlStore,
    scenario: Scenario,
) -> None:
    await check_parity(
        store_spec,
        store_session,
        store,
        scenario,
        scenario.cases,
        scenario.data_at(scenario.anchor_scale),
    )
