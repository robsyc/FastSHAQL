"""Drift guard for the known-divergence registry.

A typo'd ``KNOWN_DIVERGENCES`` key fails silently twice over: the collection
hook never matches (so nothing is xfailed) and parity records plain ``fail``
rows. This test resolves every key against the real stores and case sources
so a drift surfaces here instead — divergences.py itself is registry-only
prose, but its keys are fair game to validate.

The xfail hook (``tests/tiers/evaluation/conftest.py``) matches parity items
by test *name* (``_PARITY_TESTS``), so a renamed or newly added parity test
falls out of that frozenset silently — the companion test pins the coupling.
"""

from __future__ import annotations

import re
from pathlib import Path

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
            # The mirror image: a case-level key never xfails a scenario
            # (its parity items carry no ``case`` param — only the set-level
            # key can), so case-level keys must target hand-authored sets.
            assert source in CASES, (
                f"case-level key for {source!r} never xfails: scenario parity "
                "runs its cases inside one test — use a set-level key"
            )
            assert case in cases_by_source[source], (
                f"unknown case {case!r} for source {source!r}"
            )


def test_xfail_hook_covers_every_parity_test_name() -> None:
    """The hook's name frozenset stays in lockstep with the parity tests.

    ``_PARITY_TESTS`` is string coupling: rename ``test_case_parity`` or add
    a parity test without registering it and its divergences stop xfailing
    (plain red rows instead) — with no signal pointing at the frozenset.
    """
    evaluation_dir = Path(__file__).resolve().parents[1] / "evaluation"
    hook = (evaluation_dir / "conftest.py").read_text(encoding="utf-8")
    match = re.search(r"_PARITY_TESTS = frozenset\(\{(.*?)\}\)", hook, re.DOTALL)
    assert match is not None, "_PARITY_TESTS frozenset not found in the hook"
    registered = {name.strip(' "') for name in match.group(1).split(",")}

    parity_tests: set[str] = set()
    for path in sorted(evaluation_dir.glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        parity_tests.update(re.findall(r"(?:async )?def (test_\w*parity\w*)\(", source))

    assert parity_tests, "no parity tests found — the guard's glob drifted"
    assert registered == parity_tests, (
        f"_PARITY_TESTS {sorted(registered)} drifted from the evaluation "
        f"tier's parity tests {sorted(parity_tests)}"
    )
