"""Drift guard for the generated-data scenario registry (ADR-0021).

Mirrors ``test_case_registry`` but over ``SCENARIOS_ROOT`` ↔ ``SCENARIOS``: every
scenario case directory on disk is registered, and every registered scenario case
has a directory. Generated ``data.ttl`` is not part of this check (gitignored).
"""

from __future__ import annotations

from support.scenarios import SCENARIOS, SCENARIOS_ROOT


def test_scenario_registry_is_complete() -> None:
    on_disk: set[tuple[str, str]] = {
        (p.parent.parent.name, p.parent.name)
        for p in SCENARIOS_ROOT.glob("*/*/query.graphql")
    }
    registered: set[tuple[str, str]] = {
        (scenario.name, case)
        for scenario in SCENARIOS.values()
        for case in scenario.cases
    }
    missing = on_disk - registered
    extra = registered - on_disk
    assert not missing, (
        f"Unregistered scenario cases on disk (won't run): {sorted(missing)}"
    )
    assert not extra, (
        f"Registered scenario cases with no directory on disk: {sorted(extra)}"
    )
