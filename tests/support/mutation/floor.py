"""Gate the mutation score against the committed floor (mutmut-floor.json).

Score follows mutmut's badge convention: (killed + timeout) / (total - skipped).
Run `just mutate` (mutmut run + export-cicd-stats) first — this reads
mutants/mutmut-cicd-stats.json and exits non-zero below the floor.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATS = ROOT / "mutants" / "mutmut-cicd-stats.json"
FLOOR = ROOT / "mutmut-floor.json"


def mutation_score(stats: dict[str, int]) -> float:
    """Score per mutmut's badge convention: (killed + timeout) / (total - skipped)."""
    tested = stats["total"] - stats["skipped"]
    return (stats["killed"] + stats["timeout"]) / tested * 100 if tested else 0.0


def main() -> int:
    stats = json.loads(STATS.read_text())
    floor = json.loads(FLOOR.read_text())["floor"]
    score = mutation_score(stats)
    print(
        f"mutation score {score:.1f}% (floor {floor:.1f}%) — "
        f"killed={stats['killed']} survived={stats['survived']} "
        f"timeout={stats['timeout']} no_tests={stats['no_tests']} "
        f"suspicious={stats['suspicious']} skipped={stats['skipped']} "
        f"total={stats['total']}"
    )
    return 0 if score >= floor else 1


if __name__ == "__main__":
    sys.exit(main())
