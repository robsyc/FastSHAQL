"""Evaluation report v2 — JSON sidecar and GitHub workflow summary renderer.

The report carries the store dimension (ADR-0022): metadata for every store
that ran, the parity conformance matrix (per source in markdown, per case
in the JSON artifact), and whole-flow perf rows — total wall clock plus the
translate / store / convert split (graphql-core overhead is the residual;
HTTP stores split ``store`` further into http / decode). Report-only: no
thresholds — benchmarks are CI-flaky.

Rows accumulate during the evaluation pytest session (one session per store
matrix selection); ``pytest_sessionfinish`` writes the JSON artifact. CI
renders the markdown into ``$GITHUB_STEP_SUMMARY``.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPORT_VERSION = 2


@dataclass(frozen=True)
class PercentileTimings:
    """Median and 95th percentile — p99 is dropped: noise at 10 samples."""

    p50: float
    p95: float


@dataclass(frozen=True)
class StoreInfo:
    """One store that ran, as the report header names it."""

    image: str
    license: str
    """License tier: ``oss`` or ``free``."""
    notes: str


@dataclass(frozen=True)
class ParityRow:
    """One case's parity outcome on one store."""

    store: str
    source: str
    """Case-source name: a ``CaseSet`` (case parity) or ``Scenario`` (scenario)."""
    case: str
    outcome: str
    """``pass`` | ``divergence`` (registered, expected) | ``fail``."""
    reason: str = ""
    """The divergence reason, when outcome is ``divergence``."""


@dataclass(frozen=True)
class PhaseTimings:
    """The measured phases of one perf sample point.

    ``total`` is the whole graphql-core operation (``graphql()`` wall clock);
    ``core`` its per-sample residual over ``execute_query`` — graphql-core
    parse/resolve/format; ``translate``/``store``/``convert`` the phases
    measured inside ``execute_query``, with ``http``/``decode`` the ``store``
    split for HTTP stores (in-memory rows carry rdflib execution in ``store``
    and zeros there).
    """

    total: PercentileTimings
    core: PercentileTimings
    translate: PercentileTimings
    store: PercentileTimings
    http: PercentileTimings
    decode: PercentileTimings
    convert: PercentileTimings


@dataclass(frozen=True)
class PerfRow:
    """One scenario/scale point on one store: phase timings in ms."""

    store: str
    scenario: str
    scale: str
    rows: int
    entities: int
    timings_ms: PhaseTimings


@dataclass
class EvalReport:
    report_version: int = REPORT_VERSION
    commit: str = ""
    stores: dict[str, StoreInfo] = field(default_factory=dict)
    parity: list[ParityRow] = field(default_factory=list)
    perf: list[PerfRow] = field(default_factory=list)

    def add_store(
        self,
        *,
        name: str,
        image: str,
        license: str,  # noqa: A002 — v2 schema name, not the site builtin
        notes: str,
    ) -> None:
        """Record a store that started (skipped stores never register)."""
        self.stores[name] = StoreInfo(image=image, license=license, notes=notes)

    def add_parity(
        self, store: str, source: str, case: str, outcome: str, reason: str = ""
    ) -> None:
        self.parity.append(
            ParityRow(
                store=store,
                source=source,
                case=case,
                outcome=outcome,
                reason=reason,
            )
        )

    def add_perf(
        self,
        *,
        store: str,
        scenario: str,
        scale: str,
        rows: int,
        entities: int,
        phases: PhaseTimings,
    ) -> None:
        self.perf.append(
            PerfRow(
                store=store,
                scenario=scenario,
                scale=scale,
                rows=rows,
                entities=entities,
                timings_ms=phases,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "commit": self.commit,
            "stores": {name: asdict(info) for name, info in self.stores.items()},
            "parity": [asdict(row) for row in self.parity],
            "perf": [asdict(row) for row in self.perf],
        }

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load_json(cls, path: Path) -> EvalReport:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("report_version") != REPORT_VERSION:
            raise ValueError(
                f"unsupported report_version {data.get('report_version')!r}; "
                f"this renderer reads v{REPORT_VERSION}"
            )
        return cls(
            commit=data.get("commit", ""),
            stores={
                name: StoreInfo(**info) for name, info in data.get("stores", {}).items()
            },
            parity=[ParityRow(**row) for row in data.get("parity", [])],
            perf=[
                PerfRow(
                    store=row["store"],
                    scenario=row["scenario"],
                    scale=row["scale"],
                    rows=row["rows"],
                    entities=row["entities"],
                    timings_ms=PhaseTimings(
                        **{
                            phase: PercentileTimings(**timings)
                            for phase, timings in row["timings_ms"].items()
                        }
                    ),
                )
                for row in data.get("perf", [])
            ],
        )


_REPORT: EvalReport | None = None


def get_report() -> EvalReport:
    """Session-scoped report singleton (evaluation tier only)."""
    global _REPORT
    if _REPORT is None:
        _REPORT = EvalReport(
            commit=os.environ.get("GITHUB_SHA", os.environ.get("EVAL_COMMIT", "")),
        )
    return _REPORT


def reset_report() -> None:
    """Reset singleton (tests only)."""
    global _REPORT
    _REPORT = None


def _pair(timings: PercentileTimings) -> str:
    return f"{timings.p50:.1f}/{timings.p95:.1f}"


def _render_stores(report: EvalReport) -> list[str]:
    lines = ["### Stores", ""]
    if not report.stores:
        return [*lines, "_No stores ran (missing Docker, licenses, or selection)._"]
    lines.extend(["| store | image | license | notes |", "| --- | --- | --- | --- |"])
    for name, info in report.stores.items():
        lines.append(f"| {name} | `{info.image}` | {info.license} | {info.notes} |")
    return lines


def _render_parity(report: EvalReport) -> list[str]:
    lines = ["### Parity", ""]
    if not report.parity:
        return [*lines, "_No parity data recorded._"]
    counts: dict[tuple[str, str], dict[str, int]] = {}
    for row in report.parity:
        cell = counts.setdefault(
            (row.store, row.source), {"pass": 0, "divergence": 0, "fail": 0}
        )
        cell[row.outcome] += 1
    lines.extend(
        [
            "| store | source | pass | divergence | fail |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for (store, source), cell in sorted(counts.items()):
        lines.append(
            f"| {store} | {source} | {cell['pass']} "
            f"| {cell['divergence']} | {cell['fail']} |"
        )
    divergences = [row for row in report.parity if row.outcome == "divergence"]
    failures = [row for row in report.parity if row.outcome == "fail"]
    if divergences:
        lines.extend(["", "**Known divergences:**"])
        lines.extend(
            f"- {row.store}/{row.source}/{row.case} — {row.reason}"
            for row in divergences
        )
    if failures:
        lines.extend(["", "**Failures:**"])
        lines.extend(f"- {row.store}/{row.source}/{row.case}" for row in failures)
    return lines


def _render_perf(report: EvalReport) -> list[str]:
    if not report.perf:
        return ["### Performance", "", "_No perf data recorded._"]
    lines: list[str] = []
    # Rows arrive store-major (pytest collection runs one store's scenarios,
    # then the next store's); regroup scenario-major so each scenario forms
    # ONE cross-store table. sorted() is stable — stores keep arrival order.
    ordered = sorted(report.perf, key=lambda row: row.scenario)
    for scenario, rows in itertools.groupby(ordered, key=lambda row: row.scenario):
        lines.extend(
            [
                f"### {scenario}",
                "",
                (
                    "| store | scale | rows | entities | total | core | translate "
                    "| store | http | decode | convert |"
                ),
                (
                    "| --- | --- | ---: | ---: | --- | --- | --- | --- | --- "
                    "| --- | --- |"
                ),
            ]
        )
        for row in rows:
            t = row.timings_ms
            lines.append(
                f"| {row.store} | {row.scale} | {row.rows} | {row.entities} "
                f"| {_pair(t.total)} | {_pair(t.core)} | {_pair(t.translate)} "
                f"| {_pair(t.store)} | {_pair(t.http)} | {_pair(t.decode)} "
                f"| {_pair(t.convert)} |"
            )
    lines.extend(
        [
            "",
            (
                "_All timings p50/p95 in ms. Phases: total = whole "
                "graphql-core operation wall clock = core + translate + "
                "store + convert (+ε); core = graphql-core parse/resolve/"
                "format (total minus execute_query); translate = AST→SPARQL; "
                "store = store round trip inside execute_query — http/"
                "decode are its split for HTTP stores, while in-memory "
                "baseline rows carry rdflib execution in store with http/"
                "decode = 0; convert = bindings→JSON. Report-only, no "
                "thresholds (ADR-0022)._"
            ),
        ]
    )
    return lines


def render_markdown(report: EvalReport) -> str:
    """Render the store matrix report for ``$GITHUB_STEP_SUMMARY``."""
    lines = ["## Evaluation", ""]
    if report.commit:
        lines.append(f"Commit: `{report.commit[:7]}`")
        lines.append("")
    lines.extend(_render_stores(report))
    lines.append("")
    lines.extend(_render_parity(report))
    lines.append("")
    lines.extend(_render_perf(report))
    return "\n".join(lines) + "\n"


def default_report_path() -> Path:
    return Path(os.environ.get("EVAL_REPORT_PATH", "evaluation-report.json"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Render evaluation report markdown.")
    parser.add_argument(
        "--render-summary",
        action="store_true",
        help="Append markdown to $GITHUB_STEP_SUMMARY from the JSON report.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_report_path(),
        help="Path to evaluation-report.json",
    )
    args = parser.parse_args()
    if not args.render_summary:
        parser.error("only --render-summary is supported")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        if args.input.is_file():
            print(render_markdown(EvalReport.load_json(args.input)))
        return

    if args.input.is_file():
        markdown = render_markdown(EvalReport.load_json(args.input))
    else:
        markdown = (
            "## Evaluation\n\n"
            "_Report unavailable — the store or pytest may have failed before "
            "recording results. See job log._\n"
        )
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write(markdown)


if __name__ == "__main__":
    main()
