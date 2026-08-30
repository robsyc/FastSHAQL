"""Unit tests for ``support.scenarios`` — Scale/Scenario + cartesian generator."""

from __future__ import annotations

from support.scenarios import CARTESIAN, SCENARIOS, SCENARIOS_ROOT, Scale


def test_cartesian_anchor_data_is_nonempty_and_parses() -> None:
    graph = CARTESIAN.data_at(CARTESIAN.anchor_scale)
    assert len(graph) > 0


def test_cartesian_generator_is_deterministic() -> None:
    scale = Scale({"entities": 3, "multi_value": 2}, "test")
    assert CARTESIAN.generator(scale) == CARTESIAN.generator(scale)
    other = Scale({"entities": 3, "multi_value": 3}, "test")
    assert CARTESIAN.generator(scale) != CARTESIAN.generator(other)


def test_cartesian_row_explosion_grows_with_multi_value() -> None:
    # Per-entity row count is K^4 (ADR-0014); triple count grows with K.
    small = len(CARTESIAN.data_at(Scale({"entities": 1, "multi_value": 2}, "s")))
    large = len(CARTESIAN.data_at(Scale({"entities": 1, "multi_value": 4}, "l")))
    assert large > small


def test_scenarios_registry_includes_cartesian() -> None:
    assert SCENARIOS["cartesian"] is CARTESIAN
    assert CARTESIAN.root == SCENARIOS_ROOT / "cartesian"
    assert CARTESIAN.sweep, "cartesian must declare a degradation sweep"
