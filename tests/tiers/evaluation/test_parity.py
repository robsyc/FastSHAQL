"""Evaluation parity — hand-authored golden cases across the store matrix.

Reuses the declarative case sets (``CASES``) verbatim: each store gets the
same data and query, compared order-independently against the in-memory
goldens (ADR-0010/0022). Outcomes land in the report's parity matrix; known
divergences xfail at collection and record as ``divergence``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from support.cases import CASES, CaseSet
from support.eval.parity import check_parity

if TYPE_CHECKING:
    from fastshaql.core.execution.store import SparqlStore
    from support.eval.session import StoreSession
    from support.eval.stores import StoreSpec

pytest.importorskip("testcontainers")

PARITY_CASES: tuple[tuple[str, tuple[str, ...]], ...] = tuple(CASES.items())


@pytest.mark.parametrize(
    ("fixture_name", "case"),
    [(name, case) for name, cases in PARITY_CASES for case in cases],
    ids=[f"{name}/{case}" for name, cases in PARITY_CASES for case in cases],
)
async def test_case_parity(
    store_spec: StoreSpec,
    store_session: StoreSession,
    store: SparqlStore,
    fixture_name: str,
    case: str,
) -> None:
    case_set = CaseSet(fixture_name)
    await check_parity(
        store_spec, store_session, store, case_set, [case], case_set.load_data()
    )
