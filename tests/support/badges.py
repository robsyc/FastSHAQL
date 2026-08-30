"""Generate shields.io endpoint badges from local stats.

Run by the ``badges`` just recipe after its quiet coverage run: reads the
coverage JSON report, the exported mutmut stats, and the committed
complexipy snapshot, then writes the three endpoint JSONs (``coverage.json``,
``mutants.json``, ``complexity.json``) into ``badges/``. The Nightly
workflow pushes them to the ``badges`` data branch. Stdlib only.
"""

import json
import sys
from pathlib import Path
from typing import Any

from .mutation.floor import mutation_score

ROOT = Path(__file__).resolve().parents[2]
BADGES = ROOT / "badges"
COVERAGE_RAW = BADGES / "coverage-raw.json"
MUTANT_STATS = ROOT / "mutants" / "mutmut-cicd-stats.json"
MUTANT_FLOOR = ROOT / "mutmut-floor.json"
COMPLEXITY_SNAPSHOT = ROOT / "complexipy-snapshot.json"


def load_json(path: Path) -> Any:
    """Parse ``path`` as JSON, exiting with a clear message when it is missing."""
    if not path.exists():
        raise SystemExit(
            f"badges: missing input {path} — run `just badges` / `just mutate` first"
        )
    return json.loads(path.read_text())


def coverage_color(percent: float) -> str:
    """Shields color tiers for coverage; the suite gates at 100 (brightgreen)."""
    if percent >= 100:
        return "brightgreen"
    if percent >= 90:
        return "green"
    if percent >= 75:
        return "yellow"
    if percent >= 60:
        return "orange"
    return "red"


def mutants_color(score: float, floor: float) -> str:
    """Green at/above the committed floor; yellow just below, red further below."""
    if score >= floor:
        return "green"
    if score >= floor - 2:
        return "yellow"
    return "red"


def write_badge(name: str, label: str, message: str, color: str) -> None:
    """Write one shields.io endpoint badge (schemaVersion 1) into badges/."""
    badge = {"schemaVersion": 1, "label": label, "message": message, "color": color}
    (BADGES / name).write_text(json.dumps(badge) + "\n")


def main() -> int:
    """Write the three endpoint badges; exits non-zero when an input is missing."""
    percent = float(load_json(COVERAGE_RAW)["totals"]["percent_covered"])
    stats: dict[str, int] = load_json(MUTANT_STATS)
    floor = float(load_json(MUTANT_FLOOR)["floor"])
    score = mutation_score(stats)
    snapshot: list[dict[str, Any]] = load_json(COMPLEXITY_SNAPSHOT)
    total = sum(fn["complexity"] for entry in snapshot for fn in entry["functions"])
    BADGES.mkdir(exist_ok=True)
    write_badge("coverage.json", "coverage", f"{percent:.0f}%", coverage_color(percent))
    write_badge("mutants.json", "mutants", f"{score:.1f}%", mutants_color(score, floor))
    write_badge("complexity.json", "complexity", str(total), "blue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
