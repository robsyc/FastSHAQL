"""Evaluation report — JSON sidecar and GitHub workflow summary renderer.

Perf probes append rows during the evaluation pytest session; ``pytest_sessionfinish``
writes ``evaluation-report.json``. CI renders markdown into ``$GITHUB_STEP_SUMMARY``.
Store-agnostic (the ``store_image`` field records whichever ``StoreSession`` ran).
See ADR-0022.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PercentileTimings:
    p50: float
    p95: float
    p99: float


@dataclass(frozen=True)
class PerfRow:
    scenario: str
    scale: str
    rows: int
    entities: int
    timings_ms: dict[str, Any]


@dataclass
class EvalReport:
    report_version: int = 1
    commit: str = ""
    store_image: str = ""
    perf: list[PerfRow] = field(default_factory=list)

    def add_perf(
        self,
        *,
        scenario: str,
        scale: str,
        rows: int,
        entities: int,
        translate_ms: float,
        store: PercentileTimings,
        convert: PercentileTimings,
    ) -> None:
        self.perf.append(
            PerfRow(
                scenario=scenario,
                scale=scale,
                rows=rows,
                entities=entities,
                timings_ms={
                    "translate": round(translate_ms, 1),
                    "store": {
                        "p50": round(store.p50, 1),
                        "p95": round(store.p95, 1),
                        "p99": round(store.p99, 1),
                    },
                    "convert": {
                        "p50": round(convert.p50, 1),
                        "p95": round(convert.p95, 1),
                        "p99": round(convert.p99, 1),
                    },
                },
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "commit": self.commit,
            "store_image": self.store_image,
            "perf": [asdict(row) for row in self.perf],
        }

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load_json(cls, path: Path) -> EvalReport:
        data = json.loads(path.read_text(encoding="utf-8"))
        perf = [
            PerfRow(
                scenario=row["scenario"],
                scale=row["scale"],
                rows=row["rows"],
                entities=row["entities"],
                timings_ms=row["timings_ms"],
            )
            for row in data.get("perf", [])
        ]
        return cls(
            report_version=data.get("report_version", 1),
            commit=data.get("commit", ""),
            store_image=data.get("store_image", ""),
            perf=perf,
        )


_REPORT: EvalReport | None = None


def get_report() -> EvalReport:
    """Session-scoped report singleton (evaluation tier only)."""
    global _REPORT
    if _REPORT is None:
        _REPORT = EvalReport(
            commit=os.environ.get("GITHUB_SHA", os.environ.get("EVAL_COMMIT", "")),
            store_image=os.environ.get("EVAL_STORE_IMAGE", ""),
        )
    return _REPORT


def reset_report() -> None:
    """Reset singleton (tests only)."""
    global _REPORT
    _REPORT = None


def render_markdown(report: EvalReport) -> str:
    """Render perf degradation tables for ``$GITHUB_STEP_SUMMARY``."""
    lines = ["## Evaluation", ""]
    if report.commit:
        lines.append(f"Commit: `{report.commit[:7]}`  ")
    if report.store_image:
        lines.append(f"Store: `{report.store_image}`")
    lines.append("")

    if not report.perf:
        lines.append("_No perf data recorded._")
        return "\n".join(lines) + "\n"

    current_scenario: str | None = None
    for row in report.perf:
        if row.scenario != current_scenario:
            current_scenario = row.scenario
            lines.extend(
                [
                    f"### {row.scenario}",
                    "",
                    (
                        "| scale | rows | entities | translate | "
                        "store p50/p95/p99 | convert p50/p95/p99 |"
                    ),
                    "| --- | ---: | ---: | ---: | --- | --- |",
                ]
            )
        store = row.timings_ms["store"]
        convert = row.timings_ms["convert"]
        lines.append(
            f"| {row.scale} | {row.rows} | {row.entities} | "
            f"{row.timings_ms['translate']:.1f} | "
            f"{store['p50']:.1f}/{store['p95']:.1f}/{store['p99']:.1f} | "
            f"{convert['p50']:.1f}/{convert['p95']:.1f}/{convert['p99']:.1f} |"
        )
    lines.append("")
    lines.append(
        "_translate = AST→SPARQL; store = HTTP+triple-store+parse; "
        "convert = bindings→JSON (ADR-0022)._"
    )
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
