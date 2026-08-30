"""Unit tests for the endpoint-badge generator (``tests/support/badges.py``).

The badge JSONs must agree with the gates they advertise: the mutation score
is shared with the floor gate (``tests/support/mutation/floor.py``), and the
color tiers encode the thresholds the README badges promise. Order: pure
helpers → full ``main`` run from temp inputs.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from support.badges import coverage_color, main, mutants_color, mutation_score


def test_mutation_score_matches_floor_formula() -> None:
    stats = {"total": 120, "skipped": 20, "killed": 95, "timeout": 5}
    assert mutation_score(stats) == 100.0


def test_mutation_score_zero_when_nothing_testable() -> None:
    stats = {"total": 10, "skipped": 10, "killed": 0, "timeout": 0}
    assert mutation_score(stats) == 0.0


@pytest.mark.parametrize(
    ("percent", "color"),
    [
        (100.0, "brightgreen"),
        (90.0, "green"),
        (89.9, "yellow"),
        (75.0, "yellow"),
        (60.0, "orange"),
        (59.9, "red"),
    ],
)
def test_coverage_color_tiers(percent: float, color: str) -> None:
    assert coverage_color(percent) == color


def test_mutants_color_relative_to_floor() -> None:
    assert mutants_color(90.0, 90.0) == "green"
    assert mutants_color(88.5, 90.0) == "yellow"
    assert mutants_color(87.9, 90.0) == "red"


def test_main_writes_badges_from_stats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    badges = tmp_path / "badges"
    badges.mkdir()
    stats = tmp_path / "stats.json"
    floor = tmp_path / "floor.json"
    snapshot = tmp_path / "snapshot.json"
    (badges / "coverage-raw.json").write_text(
        json.dumps({"totals": {"percent_covered": 100.0}})
    )
    stats.write_text(
        json.dumps({"total": 120, "skipped": 20, "killed": 95, "timeout": 5})
    )
    floor.write_text(json.dumps({"floor": 90.0}))
    snapshot.write_text(
        json.dumps([{"functions": [{"complexity": 3}, {"complexity": 4}]}])
    )
    monkeypatch.setattr("support.badges.BADGES", badges)
    monkeypatch.setattr("support.badges.COVERAGE_RAW", badges / "coverage-raw.json")
    monkeypatch.setattr("support.badges.MUTANT_STATS", stats)
    monkeypatch.setattr("support.badges.MUTANT_FLOOR", floor)
    monkeypatch.setattr("support.badges.COMPLEXITY_SNAPSHOT", snapshot)

    assert main() == 0

    coverage = json.loads((badges / "coverage.json").read_text())
    assert coverage == {
        "schemaVersion": 1,
        "label": "coverage",
        "message": "100%",
        "color": "brightgreen",
    }
    mutants = json.loads((badges / "mutants.json").read_text())
    assert (mutants["message"], mutants["color"]) == ("100.0%", "green")
    complexity = json.loads((badges / "complexity.json").read_text())
    assert (complexity["message"], complexity["color"]) == ("7", "blue")
