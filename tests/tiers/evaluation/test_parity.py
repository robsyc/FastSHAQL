"""Evaluation parity — hand-authored golden cases against GraphDB CE.

Reuses the declarative case sets (``CASES``) but swaps ``InMemoryStore`` for an
``HttpxSparqlStore`` backed by a testcontainers GraphDB instance. JSON assertions
are order-independent (ADR-0010; canonical compare via ``support.goldens``).
See ADR-0022.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from support.cases import CASES, CaseSet
from support.runners import run_case_on_store

if TYPE_CHECKING:
    from support.eval.graphdb import GraphDbSession

pytest.importorskip("testcontainers")

PARITY_CASES: tuple[tuple[str, tuple[str, ...]], ...] = tuple(CASES.items())


@pytest.mark.parametrize(
    ("fixture_name", "case"),
    [(name, case) for name, cases in PARITY_CASES for case in cases],
    ids=[f"{name}/{case}" for name, cases in PARITY_CASES for case in cases],
)
async def test_case_parity(
    graphdb_session: GraphDbSession,
    graphdb_store,
    fixture_name: str,
    case: str,
) -> None:
    case_set = CaseSet(fixture_name)
    graphdb_session.load_graph(case_set.load_data())
    await run_case_on_store(case_set, case, graphdb_store)
