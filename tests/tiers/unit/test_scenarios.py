"""Unit tests for ``support.scenarios`` — Scale/Scenario + the generators."""

from __future__ import annotations

import pytest

from support.scenarios import (
    CARTESIAN,
    SCENARIOS,
    SCENARIOS_ROOT,
    Scale,
)

ALL_SCENARIOS = tuple(SCENARIOS.values())


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
def test_anchor_data_is_nonempty_and_parses(scenario) -> None:
    graph = scenario.data_at(scenario.anchor_scale)
    assert len(graph) > 0


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
def test_generator_is_deterministic(scenario) -> None:
    # Same scale → byte-identical Turtle; the neighbouring sweep point must
    # move the output (the axis is live, not decorative).
    scale = scenario.sweep[0]
    assert scenario.generator(scale) == scenario.generator(scale)
    assert scenario.generator(scale) != scenario.generator(scenario.sweep[1])


def test_cartesian_row_explosion_grows_with_multi_value() -> None:
    # Per-entity row count is K^4 (ADR-0014); triple count grows with K.
    small = len(CARTESIAN.data_at(Scale({"entities": 1, "multi_value": 2}, "s")))
    large = len(CARTESIAN.data_at(Scale({"entities": 1, "multi_value": 4}, "l")))
    assert large > small


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
def test_sweep_grows_the_dataset(scenario) -> None:
    # The sweep's span must grow the dataset: more triples at sweep[-1] than
    # at sweep[0], whatever each scenario's axis measures.
    first = scenario.data_at(scenario.sweep[0])
    last = scenario.data_at(scenario.sweep[-1])
    assert len(last) > len(first) > 0


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
def test_seed_changes_minted_iris(scenario) -> None:
    # IRIs are hash-minted from the seed (literals are seed-independent), so
    # reseeding must change the generated data at the first sweep point.
    params = scenario.sweep[0].params
    seed_0 = scenario.generator(Scale({**params, "seed": 0}, "seed0"))
    seed_1 = scenario.generator(Scale({**params, "seed": 1}, "seed1"))
    assert seed_0 != seed_1


def test_scenarios_registry_includes_cartesian() -> None:
    assert SCENARIOS["cartesian"] is CARTESIAN
    assert CARTESIAN.root == SCENARIOS_ROOT / "cartesian"
    assert CARTESIAN.sweep, "cartesian must declare a degradation sweep"


def test_scenarios_registry_covers_all_scenarios() -> None:
    # Every declared scenario is registered under its own name with a sweep.
    for name, scenario in SCENARIOS.items():
        assert scenario.name == name
        assert scenario.root == SCENARIOS_ROOT / name
        assert scenario.sweep, f"{name} must declare a degradation sweep"
