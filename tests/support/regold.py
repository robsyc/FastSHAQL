"""Regenerate the golden files of an e2e case from the live pipeline.

Companion to ``support.runners.run_case``: the same parse → build → execute
path, but writing instead of asserting. Refuses to write when the operation
errors or the store records anything other than exactly one query — a golden
must capture a healthy run, never a failure.

Usage (repo root)::

    uv run python tests/support/regold.py <set> [<case> ...]

With no *case* arguments, regolds every registered case of the set. Writing is
only half the workflow: always read the regenerated SPARQL against
``data.ttl``/``data.trig`` and the source under ``src/`` before keeping it —
the pipeline produces what it produces, which is not always what it should.
"""

# ruff: noqa: T201 — CLI tool; stdout progress lines are the interface

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graphql import graphql

from fastshaql.core.execution import InMemoryStore, ResolverContext
from fastshaql.executable import build_executable_schema
from support.cases import CASES, CaseSet, registry_for_path
from support.runners import RecordingStore


async def _regold(case_set: CaseSet, case: str) -> list[str]:
    """Rewrite one case's goldens; returns the changed-file basenames."""
    loaded = case_set.load_case(case)
    registry = registry_for_path(case_set.shapes_path())
    schema = build_executable_schema(registry)
    store = RecordingStore(InMemoryStore(case_set.load_data()))
    ctx = ResolverContext(store=store, query_context=loaded.query_context)
    result = await graphql(schema, loaded.query, context_value=ctx)

    assert result.errors is None, f"{case_set.name}/{case}: {result.errors}"
    assert len(store.queries) == 1, (
        f"{case_set.name}/{case}: {len(store.queries)} queries recorded, expected 1"
    )

    sparql_text = store.queries[0] + "\n"
    json_text = json.dumps(result.formatted, indent=2, ensure_ascii=False) + "\n"

    changed: list[str] = []
    for basename, text in (
        ("expected.sparql", sparql_text),
        ("expected.json", json_text),
    ):
        path = case_set.case_dir(case) / basename
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            changed.append(basename)
    return changed


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    set_name = argv[1]
    if set_name not in CASES:
        print(f"unknown set {set_name!r}; registered: {sorted(CASES)}", file=sys.stderr)
        return 2
    cases = argv[2:] or list(CASES[set_name])

    case_set = CaseSet(set_name)
    for case in cases:
        changed = asyncio.run(_regold(case_set, case))
        print(
            f"{set_name}/{case}: {'rewrote ' + ', '.join(changed) if changed else 'unchanged'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
