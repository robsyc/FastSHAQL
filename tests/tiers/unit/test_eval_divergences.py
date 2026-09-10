"""Drift guard for the known-divergence registry.

A typo'd ``KNOWN_DIVERGENCES`` key fails silently twice over: the collection
hook never matches (so nothing is xfailed) and parity records plain ``fail``
rows. This test resolves every key against the real stores and case sources
so a drift surfaces here instead — divergences.py itself is registry-only
prose, but its keys are fair game to validate.
"""

from __future__ import annotations

from support.cases import CASES
from support.eval.divergences import KNOWN_DIVERGENCES
from support.eval.stores import STORES
from support.scenarios import SCENARIOS


def test_known_divergence_keys_resolve_to_real_stores_sources_and_cases() -> None:
    cases_by_source: dict[str, tuple[str, ...]] = {
        **CASES,
        **{name: scenario.cases for name, scenario in SCENARIOS.items()},
    }
    for store, source, case in KNOWN_DIVERGENCES:
        assert store in STORES, f"unknown store {store!r}"
        assert source in cases_by_source, f"unknown case source {source!r}"
        if case is None:
            # Set-level keys only match sources whose cases run inside one
            # test (scenario parity); case parity parametrizes one case per
            # test, so a None key for a CASES set would xfail nothing.
            assert source in SCENARIOS, (
                f"set-level key for {source!r} never matches: its cases run "
                "one per test"
            )
        else:
            assert case in cases_by_source[source], (
                f"unknown case {case!r} for source {source!r}"
            )
