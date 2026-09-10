"""Parity outcome recording — the glue between the runners and the report.

Loads a source's data into the store session, runs each case through the
store-backed pipeline, and records the outcome per case: ``pass``, ``fail``,
or ``divergence`` when the (store, source, case) combination is a registered
known divergence (with its reason). Only golden mismatches (``AssertionError``)
are recorded — re-raised so pytest owns the red/xfail verdict; infra faults
(timeouts, HTTP errors) propagate unrecorded as pytest errors, never
mislabeled ``divergence``/``fail``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from support.eval.divergences import KNOWN_DIVERGENCES
from support.eval.report import get_report
from support.runners import run_case_on_store

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rdflib import Graph

    from fastshaql.core.execution.store import SparqlStore
    from support.cases import CaseSource
    from support.eval.session import StoreSession
    from support.eval.stores import StoreSpec


async def check_parity(
    spec: StoreSpec,
    session: StoreSession,
    store: SparqlStore,
    source: CaseSource,
    cases: Iterable[str],
    data: Graph,
) -> None:
    """Run *cases* against *store* over *data*, recording each outcome."""
    session.load_graph(data)
    report = get_report()
    for case in cases:
        known = KNOWN_DIVERGENCES.get((spec.name, source.name, case)) or (
            KNOWN_DIVERGENCES.get((spec.name, source.name, None))
        )
        try:
            await run_case_on_store(source, case, store)
        except AssertionError:  # golden mismatch — record, pytest owns the verdict
            report.add_parity(
                spec.name,
                source.name,
                case,
                "divergence" if known else "fail",
                reason=known.reason if known else "",
            )
            raise
        report.add_parity(spec.name, source.name, case, "pass")
