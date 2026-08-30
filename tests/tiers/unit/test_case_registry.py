"""Drift guard for the hand-authored case registry (ADR-0021).

``CASES`` is the opt-in manifest of which ``tests/fixtures/cases/<set>/<case>/``
directories the e2e suite runs. A case directory that exists on disk but is not
registered would silently never execute; this guard turns that drift into a loud
failure. The registry is intentionally explicit so a case can be present but
opted out (e.g. work-in-progress) by leaving it unregistered. Generated-data
scenarios live under ``tests/fixtures/scenarios/`` and have their own guard.
"""

from __future__ import annotations

from support.cases import CASES, CASES_ROOT


def test_case_registry_is_complete() -> None:
    on_disk: set[tuple[str, str]] = {
        (p.parent.parent.name, p.parent.name)
        for p in CASES_ROOT.glob("*/*/query.graphql")
    }
    registered: set[tuple[str, str]] = {
        (set_name, case) for set_name, cases in CASES.items() for case in cases
    }
    missing = on_disk - registered
    extra = registered - on_disk
    assert not missing, (
        f"Unregistered cases fixtures on disk (won't run): {sorted(missing)}"
    )
    assert not extra, (
        f"Registered cases fixtures with no directory on disk: {sorted(extra)}"
    )
