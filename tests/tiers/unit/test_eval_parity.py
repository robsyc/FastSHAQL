"""Unit tests for parity outcome recording — ``check_parity`` over stubs.

The runner is monkeypatched and the store is opaque: these tests pin the
recording contract only — passes recorded, golden mismatches (``AssertionError``)
recorded as ``fail``/``divergence`` (with the registered reason) and re-raised,
and infra faults propagating unrecorded so pytest reports them as errors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rdflib import Graph

from support.eval.divergences import Divergence
from support.eval.parity import check_parity
from support.eval.report import ParityRow, get_report, reset_report
from support.eval.stores import StoreSpec

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping
    from contextlib import AbstractContextManager
    from pathlib import Path

    from fastshaql.core.execution.store import ExecutionMetrics, SparqlRow
    from support.cases import E2eCase
    from support.eval.session import StoreSession


def _never_starts() -> AbstractContextManager[StoreSession]:
    raise AssertionError("stub spec is never started")


_SPEC = StoreSpec(name="stub", license="oss", notes="", start=_never_starts)


class _StubSource:
    """Structural ``CaseSource`` — the patched runner never reads past ``name``."""

    def __init__(self, name: str = "stub-cases") -> None:
        self.name = name

    def shapes_path(self) -> Path:
        raise AssertionError("the patched runner never reads shapes")

    def load_case(self, case: str) -> E2eCase:  # noqa: ARG002 — protocol slot
        raise AssertionError("the patched runner never loads cases")


class _StubSession:
    """Structural ``StoreSession`` — records the per-source data load."""

    query_endpoint = "http://stub/sparql"
    image = "stub:latest"

    def __init__(self) -> None:
        self.loaded: list[Graph] = []

    def load_graph(self, graph: Graph) -> None:
        self.loaded.append(graph)

    def close(self) -> None:
        pass


class _StubStore:
    """Opaque to ``check_parity`` — the patched runner never queries it."""

    async def query(
        self,
        sparql: str,  # noqa: ARG002 — protocol slot
        metrics: ExecutionMetrics | None = None,  # noqa: ARG002 — protocol slot
    ) -> list[SparqlRow]:
        raise AssertionError("the patched runner never queries the store")


def _fake_runner(
    errors: Mapping[str, BaseException],
) -> Callable[[object, str, object], Awaitable[None]]:
    """Patched ``run_case_on_store``: raise *errors[case]* when mapped."""

    async def runner(_source: object, case: str, _store: object) -> None:
        if error := errors.get(case):
            raise error

    return runner


@pytest.fixture(autouse=True)
def _isolated_report():
    """The report singleton never leaks between these tests (or out of them)."""
    reset_report()
    yield
    reset_report()


async def test_check_parity_records_each_pass_and_loads_data_first(monkeypatch) -> None:
    monkeypatch.setattr("support.eval.parity.KNOWN_DIVERGENCES", {})
    monkeypatch.setattr("support.eval.parity.run_case_on_store", _fake_runner({}))
    session = _StubSession()
    data = Graph()

    await check_parity(_SPEC, session, _StubStore(), _StubSource(), ("a", "b"), data)

    assert session.loaded == [data]  # data is loaded once, before any case
    assert get_report().parity == [
        ParityRow("stub", "stub-cases", "a", "pass"),
        ParityRow("stub", "stub-cases", "b", "pass"),
    ]


async def test_check_parity_unregistered_failure_records_fail_and_reraises(
    monkeypatch,
) -> None:
    monkeypatch.setattr("support.eval.parity.KNOWN_DIVERGENCES", {})
    monkeypatch.setattr(
        "support.eval.parity.run_case_on_store",
        _fake_runner({"a": AssertionError("golden mismatch")}),
    )

    with pytest.raises(AssertionError, match="golden mismatch"):
        await check_parity(
            _SPEC, _StubSession(), _StubStore(), _StubSource(), ("a",), Graph()
        )

    assert get_report().parity == [ParityRow("stub", "stub-cases", "a", "fail")]


async def test_check_parity_registered_divergence_records_reason(monkeypatch) -> None:
    """The registered reason lands in the row — CI summaries name the why."""
    monkeypatch.setattr(
        "support.eval.parity.KNOWN_DIVERGENCES",
        {("stub", "stub-cases", "a"): Divergence(reason="engine row order (ADR-0010)")},
    )
    monkeypatch.setattr(
        "support.eval.parity.run_case_on_store",
        _fake_runner({"a": AssertionError("golden mismatch")}),
    )

    with pytest.raises(AssertionError):
        await check_parity(
            _SPEC, _StubSession(), _StubStore(), _StubSource(), ("a",), Graph()
        )

    assert get_report().parity == [
        ParityRow(
            "stub",
            "stub-cases",
            "a",
            "divergence",
            reason="engine row order (ADR-0010)",
        )
    ]


async def test_check_parity_set_level_divergence_fallback(monkeypatch) -> None:
    """A case-level miss falls back to the ``(store, source, None)`` entry."""
    monkeypatch.setattr(
        "support.eval.parity.KNOWN_DIVERGENCES",
        {("stub", "stub-cases", None): Divergence(reason="whole source diverges")},
    )
    monkeypatch.setattr(
        "support.eval.parity.run_case_on_store",
        _fake_runner({"a": AssertionError("golden mismatch")}),
    )

    with pytest.raises(AssertionError):
        await check_parity(
            _SPEC, _StubSession(), _StubStore(), _StubSource(), ("a",), Graph()
        )

    assert get_report().parity == [
        ParityRow(
            "stub", "stub-cases", "a", "divergence", reason="whole source diverges"
        )
    ]


async def test_check_parity_case_level_entry_outranks_set_level(monkeypatch) -> None:
    """Both a case-level and a set-level entry registered — case-level wins."""
    monkeypatch.setattr(
        "support.eval.parity.KNOWN_DIVERGENCES",
        {
            ("stub", "stub-cases", "a"): Divergence(reason="case-level reason"),
            ("stub", "stub-cases", None): Divergence(reason="set-level reason"),
        },
    )
    monkeypatch.setattr(
        "support.eval.parity.run_case_on_store",
        _fake_runner({"a": AssertionError("golden mismatch")}),
    )

    with pytest.raises(AssertionError):
        await check_parity(
            _SPEC, _StubSession(), _StubStore(), _StubSource(), ("a",), Graph()
        )

    assert get_report().parity == [
        ParityRow("stub", "stub-cases", "a", "divergence", reason="case-level reason")
    ]


async def test_check_parity_infra_fault_propagates_unrecorded(monkeypatch) -> None:
    """Non-AssertionError faults are pytest errors — never divergence/fail rows."""
    monkeypatch.setattr("support.eval.parity.KNOWN_DIVERGENCES", {})
    monkeypatch.setattr(
        "support.eval.parity.run_case_on_store",
        _fake_runner({"a": TimeoutError("store not ready")}),
    )

    with pytest.raises(TimeoutError, match="store not ready"):
        await check_parity(
            _SPEC, _StubSession(), _StubStore(), _StubSource(), ("a",), Graph()
        )

    assert get_report().parity == []
