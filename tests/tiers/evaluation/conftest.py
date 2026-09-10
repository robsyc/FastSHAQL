"""Evaluation-tier fixtures — the store-matrix legs (ADR-0022).

One session-scoped container per selected leg (``EVAL_STORE`` selects; a
store whose prerequisites are missing skips itself), a fresh
``HttpxSparqlStore`` per test, and the report write on session finish. The
collection hook xfails known-divergence parity items.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from fastshaql.stores.http import HttpxSparqlStore
from support.eval.divergences import KNOWN_DIVERGENCES
from support.eval.report import default_report_path, get_report
from support.eval.stores import StoreSpec, selected_stores

pytest.importorskip("testcontainers")

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from fastshaql.core.execution.store import SparqlStore
    from support.eval.session import StoreSession


def pytest_sessionfinish(
    session: pytest.Session,  # noqa: ARG001
    exitstatus: int,  # noqa: ARG001
) -> None:
    """Write the evaluation report once per session (pytest hook)."""
    get_report().write_json(default_report_path())


@pytest.fixture(scope="session", params=selected_stores(), ids=lambda spec: spec.name)
def store_spec(request) -> StoreSpec:
    """The store-matrix legs this run exercises (``EVAL_STORE`` selects)."""
    return request.param


@pytest.fixture(scope="session")
def store_session(store_spec: StoreSpec) -> Iterator[StoreSession]:
    """One container-backed store session per selected store."""
    with store_spec.start() as session:
        get_report().add_store(
            name=store_spec.name,
            image=session.image,
            license=store_spec.license,
            notes=store_spec.notes,
        )
        yield session


@pytest.fixture
async def store(store_session: StoreSession) -> AsyncIterator[SparqlStore]:
    """Function-scoped ``HttpxSparqlStore`` — fresh async client per test."""
    client = httpx.AsyncClient(timeout=60.0)
    try:
        yield HttpxSparqlStore(client, store_session.query_endpoint)
    finally:
        await client.aclose()


_PARITY_TESTS = frozenset({"test_case_parity", "test_scenario_parity"})


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """xfail known-divergence parity items, keyed by their store + case params.

    Perf items are report-only (no parity assertion) and are never marked.
    """
    for item in items:
        if getattr(item, "originalname", None) not in _PARITY_TESTS:
            continue
        callspec = getattr(item, "callspec", None)
        if callspec is None:  # only parametrized items carry one
            continue
        params = callspec.params
        spec = params.get("store_spec")
        source = params.get("fixture_name") or params.get("scenario")
        if not isinstance(spec, StoreSpec) or source is None:
            continue
        source_name = getattr(source, "name", source)
        divergence = KNOWN_DIVERGENCES.get((spec.name, source_name, params.get("case")))
        if divergence is not None:
            item.add_marker(pytest.mark.xfail(reason=divergence.reason, strict=False))
