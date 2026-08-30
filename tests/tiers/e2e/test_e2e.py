"""Declarative end-to-end acceptance tests (ADR-0021).

Full pipeline: parse shapes, build executable schema, execute GraphQL against
in-memory RDF, assert JSON results and optional ``expected.sparql`` via ``RecordingStore``.

Order: parametrized ``test_e2e_execute`` over ``CASES``.
"""

from __future__ import annotations

import pytest

from support.cases import CASES, CaseSet, data_graph_for
from support.runners import run_case

E2E_CASES: tuple[tuple[str, tuple[str, ...]], ...] = tuple(CASES.items())


@pytest.mark.parametrize(
    ("fixture_name", "case"),
    [(name, case) for name, cases in E2E_CASES for case in cases],
    ids=[f"{name}/{case}" for name, cases in E2E_CASES for case in cases],
)
async def test_e2e_execute(fixture_name: str, case: str) -> None:
    await run_case(CaseSet(fixture_name), case, data_graph_for(fixture_name))
