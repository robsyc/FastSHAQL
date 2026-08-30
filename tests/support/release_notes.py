"""Extract one release section from CHANGELOG.md.

Run by the ``release-notes VERSION`` just recipe: prints the section body
under the ``## [VERSION]`` heading (up to the next ``## `` heading, blank
edges trimmed) to stdout. CHANGELOG.md is the single source of truth for
release notes — the Release workflow pipes this into the GitHub Release
body. Stdlib only.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"


def section_body(changelog: str, version: str) -> list[str] | None:
    """Return the lines under ``## [version]``, or None when absent."""
    prefix = f"## [{version}]"
    body: list[str] = []
    in_section = False
    for line in changelog.splitlines():
        if line.startswith(prefix):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            body.append(line)
    return body if in_section else None


def main() -> int:
    """Print the CHANGELOG.md section body for the given version."""
    if len(sys.argv) != 2:
        raise SystemExit("usage: release_notes.py VERSION")
    version = sys.argv[1]
    if not CHANGELOG.exists():
        raise SystemExit(f"missing changelog: {CHANGELOG}")
    body = section_body(CHANGELOG.read_text(), version)
    if body is None:
        raise SystemExit(f"no '## [{version}]' section in {CHANGELOG}")
    sys.stdout.write("\n".join(body).strip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
