"""Regenerate the module-dependency diagram in docs/ARCHITECTURE.md.

Runs ``tach show --mermaid`` and splices the output between the
``<!-- module-graph:start/end -->`` markers. Manual regeneration
(``just module-graph``), not CI — the diagram is documentation, not a gate.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARCHITECTURE = ROOT / "docs" / "ARCHITECTURE.md"
TACH = Path(sys.executable).parent / "tach"  # the venv's tach binary
START = "<!-- module-graph:start -->"
END = "<!-- module-graph:end -->"


def main() -> int:
    graph = subprocess.run(  # noqa: S603 — the pinned venv's tach binary, not untrusted input
        [str(TACH), "show", "--mermaid", "-o", "-"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    text = ARCHITECTURE.read_text()
    try:
        pre, rest = text.split(START)
        _, post = rest.split(END)
    except ValueError:
        print(f"{ARCHITECTURE} is missing {START}/{END} markers")
        return 1
    ARCHITECTURE.write_text(f"{pre}{START}\n\n```mermaid\n{graph}\n```\n\n{END}{post}")
    print("docs/ARCHITECTURE.md module graph regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
