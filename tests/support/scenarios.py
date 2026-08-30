"""Generated-data scenarios for evaluation: scale-parametric data + degradation sweeps.

A *scenario* is a case source whose data is synthetically generated (rather than
hand-authored) and that carries a scale axis for performance-degradation probing.
Scenario data lives under ``tests/fixtures/scenarios/<name>/``: committed
``shapes.ttl`` + correctness-anchor cases (``smoke/``); the generated ``data.ttl``
is gitignored (produced by ``generate.py`` for manual runs, or in-memory by the
harness via ``Scenario.data_at``).

Each scenario declares its own generator and names its own scale parameters; the
harness is parameter-name agnostic. Contrast ``support.cases`` (hand-authored,
committed data, correctness e2e). See ADR-0021 (tier model and the
cases/scenarios split).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph

from support.cases import E2eCase, load_case_from

SCENARIOS_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "scenarios"


@dataclass(frozen=True)
class Scale:
    """One point on a scenario's scale axis.

    A flat ``params`` mapping lets each scenario name its own axes
    (``entities`` / ``multi_value`` / ``langs`` / ``depth`` …) without the harness
    knowing the parameter names. Frozen → hashable → cacheable.
    """

    params: Mapping[str, int]
    label: str


# Pure: Scale → Turtle text (deterministic, seeded). No I/O.
DataGenerator = Callable[[Scale], str]


@dataclass(frozen=True)
class Scenario:
    """One generated-data scenario under ``tests/fixtures/scenarios/<name>/``.

    Satisfies ``support.cases.CaseSource`` structurally (``name`` + ``load_case``),
    so the same ``run_case`` / ``run_case_on_store`` runners serve cases and scenarios.
    """

    name: str
    cases: tuple[str, ...]
    generator: DataGenerator
    anchor_scale: Scale
    sweep: tuple[Scale, ...]

    @property
    def root(self) -> Path:
        return SCENARIOS_ROOT / self.name

    def shapes_path(self) -> Path:
        return self.root / "shapes.ttl"

    def case_dir(self, case: str) -> Path:
        return self.root / case

    def load_case(self, case: str) -> E2eCase:
        return load_case_from(self.case_dir(case), case)

    def data_at(self, scale: Scale) -> Graph:
        """Generate scenario data at *scale* in-memory (pure — no disk write)."""
        graph = Graph()
        graph.parse(data=self.generator(scale), format="turtle")
        return graph


# ---------------------------------------------------------------------------
# Cartesian row-explosion scenario (ADR-0014). One child per Thing; per-entity
# row count is K^4 (K tags x K altLabels x K child-tags x K child-altLabels).
# Distinct lexical forms keep the dedup-coercion wrinkle observable, not masked.
# ---------------------------------------------------------------------------

_CARTESIAN_NS = "http://example.org/cartesian/"


def _mint_iri(seed: int, *parts: str) -> str:
    digest = hashlib.sha256(f"{seed}|{'|'.join(parts)}".encode()).hexdigest()[:12]
    return f"{_CARTESIAN_NS}{digest}"


def _emit_cartesian_data(*, entities: int, multi_value: int, seed: int = 0) -> str:
    lines = ["@prefix ex: <http://example.org/> .\n\n"]
    for i in range(entities):
        thing = f"<{_mint_iri(seed, 'thing', str(i))}>"
        child = f"<{_mint_iri(seed, 'child', str(i))}>"
        lines.append(f"{thing} a ex:Thing .\n")
        for slot in range(multi_value):
            lines.append(f'{thing} ex:tag "tag-e{i}-v{slot}" .\n')
            lines.append(f'{thing} ex:altLabel "alt-e{i}-v{slot}" .\n')
        lines.append(f"{thing} ex:hasChild {child} .\n")
        lines.append(f"{child} a ex:Child .\n")
        for slot in range(multi_value):
            lines.append(f'{child} ex:tag "ctag-e{i}-v{slot}" .\n')
            lines.append(f'{child} ex:altLabel "calt-e{i}-v{slot}" .\n')
    return "".join(lines)


def _generate_cartesian(scale: Scale) -> str:
    return _emit_cartesian_data(
        entities=scale.params["entities"],
        multi_value=scale.params["multi_value"],
        seed=scale.params.get("seed", 0),
    )


CARTESIAN = Scenario(
    name="cartesian",
    cases=("smoke",),
    generator=_generate_cartesian,
    anchor_scale=Scale({"entities": 1, "multi_value": 2}, "anchor"),
    sweep=(
        Scale({"entities": 10, "multi_value": 2}, "N10-K2"),
        Scale({"entities": 50, "multi_value": 2}, "N50-K2"),
        Scale({"entities": 50, "multi_value": 4}, "N50-K4"),
        Scale({"entities": 100, "multi_value": 4}, "N100-K4"),
        Scale({"entities": 50, "multi_value": 8}, "N50-K8"),
    ),
)

# Canonical scenario registry — single source of truth (mirrors support.cases.CASES).
SCENARIOS: dict[str, Scenario] = {"cartesian": CARTESIAN}
