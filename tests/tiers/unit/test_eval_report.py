"""Unit tests for evaluation report v2 rendering and round-tripping."""

from __future__ import annotations

import json

import pytest

from support.eval.report import (
    EvalReport,
    ParityRow,
    PercentileTimings,
    PhaseTimings,
    render_markdown,
    reset_report,
)


def _perf_report() -> EvalReport:
    report = EvalReport(commit="abc1234567890")
    report.add_store(
        name="oxigraph", image="oxigraph/oxigraph:0.5.9", license="oss", notes=""
    )
    report.add_perf(
        store="oxigraph",
        scenario="cartesian",
        scale="N10-K2",
        rows=256,
        entities=10,
        phases=PhaseTimings(
            total=PercentileTimings(p50=30.0, p95=40.0),
            core=PercentileTimings(p50=2.0, p95=3.0),
            translate=PercentileTimings(p50=1.2, p95=1.5),
            store=PercentileTimings(p50=8.0, p95=9.5),
            http=PercentileTimings(p50=5.0, p95=6.0),
            decode=PercentileTimings(p50=2.0, p95=2.5),
            convert=PercentileTimings(p50=20.0, p95=25.0),
        ),
    )
    report.add_perf(
        store="in-memory",
        scenario="cartesian",
        scale="N10-K2",
        rows=256,
        entities=10,
        phases=PhaseTimings(
            total=PercentileTimings(p50=60.0, p95=70.0),
            core=PercentileTimings(p50=2.0, p95=2.5),
            translate=PercentileTimings(p50=1.0, p95=1.1),
            store=PercentileTimings(p50=55.0, p95=60.0),
            http=PercentileTimings(p50=0.0, p95=0.0),
            decode=PercentileTimings(p50=0.0, p95=0.0),
            convert=PercentileTimings(p50=50.0, p95=55.0),
        ),
    )
    report.add_parity("oxigraph", "filters", "scalar_gt", "pass")
    report.add_parity(
        "oxigraph",
        "named_graphs",
        "no_iris",
        "divergence",
        reason="no-FROM default graph is unnamed-only",
    )
    return report


def test_render_markdown_stores_and_perf_tables() -> None:
    md = render_markdown(_perf_report())
    assert "| store | image | license | notes |" in md
    assert "| oxigraph | `oxigraph/oxigraph:0.5.9` | oss |" in md
    assert "### cartesian" in md
    # Every phase names a column, core and store included — header and row
    # stay aligned.
    assert "| total | core | translate | store | http | decode | convert |" in md
    # Cross-store rows: both stores in one scenario table, p50/p95 pairs.
    assert "| oxigraph | N10-K2 | 256 | 10 | 30.0/40.0 | 2.0/3.0 | 1.2/1.5 |" in md
    assert "| in-memory | N10-K2 | 256 | 10 | 60.0/70.0 |" in md
    # The footnote states the closed accounting and the in-memory carve-out.
    assert (
        "total = whole graphql-core operation wall clock = core + translate + store"
        in md
    )
    assert "in-memory baseline rows carry rdflib execution in store" in md


def test_render_markdown_parity_matrix_names_divergences() -> None:
    md = render_markdown(_perf_report())
    assert "| store | source | pass | divergence | fail |" in md
    assert "| oxigraph | filters | 1 | 0 | 0 |" in md
    assert "| oxigraph | named_graphs | 0 | 1 | 0 |" in md
    assert "**Known divergences:**" in md
    assert (
        "- oxigraph/named_graphs/no_iris — no-FROM default graph is unnamed-only" in md
    )


def test_render_markdown_empty_report() -> None:
    md = render_markdown(EvalReport())
    assert "_No stores ran" in md
    assert "_No parity data recorded._" in md
    assert "_No perf data recorded._" in md


def _flat_phases() -> PhaseTimings:
    """Zero timings — column structure is what the regroup tests assert."""
    zero = PercentileTimings(p50=0.0, p95=0.0)
    return PhaseTimings(
        total=zero,
        core=zero,
        translate=zero,
        store=zero,
        http=zero,
        decode=zero,
        convert=zero,
    )


def test_render_perf_regroups_store_major_rows_per_scenario() -> None:
    """Rows arrive store-major (collection order) — one section per scenario,
    every store's rows side by side in it."""
    report = EvalReport()
    for store in ("oxigraph", "in-memory"):
        for scenario in ("cartesian", "wide-results"):
            report.add_perf(
                store=store,
                scenario=scenario,
                scale="N10",
                rows=1,
                entities=1,
                phases=_flat_phases(),
            )
    md = render_markdown(report)
    assert md.count("### cartesian") == 1
    assert md.count("### wide-results") == 1
    # Each section carries BOTH stores' rows side by side.
    cartesian = md.split("### cartesian", 1)[1].split("### ", 1)[0]
    assert "| oxigraph | N10 | 1 | 1 |" in cartesian
    assert "| in-memory | N10 | 1 | 1 |" in cartesian


def test_render_markdown_perf_without_parity() -> None:
    """Perf present, parity empty — each section's empty branch stands alone."""
    report = EvalReport()
    report.add_perf(
        store="in-memory",
        scenario="cartesian",
        scale="N10",
        rows=1,
        entities=1,
        phases=_flat_phases(),
    )
    md = render_markdown(report)
    assert "_No parity data recorded._" in md
    assert "### cartesian" in md
    assert "_No perf data recorded._" not in md


def test_report_roundtrip_json(tmp_path) -> None:
    report = _perf_report()
    path = tmp_path / "report.json"
    report.write_json(path)
    loaded = EvalReport.load_json(path)
    assert loaded.commit == "abc1234567890"
    assert loaded.stores["oxigraph"].license == "oss"
    assert loaded.parity == [
        ParityRow("oxigraph", "filters", "scalar_gt", "pass"),
        ParityRow(
            "oxigraph",
            "named_graphs",
            "no_iris",
            "divergence",
            reason="no-FROM default graph is unnamed-only",
        ),
    ]
    assert loaded.perf[0].timings_ms.store == PercentileTimings(p50=8.0, p95=9.5)
    assert loaded.perf[0].timings_ms.http == PercentileTimings(p50=5.0, p95=6.0)


def test_load_json_rejects_foreign_version(tmp_path) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"report_version": 1, "perf": []}))
    with pytest.raises(ValueError, match="unsupported report_version"):
        EvalReport.load_json(path)


def test_get_report_reads_commit_from_environment(monkeypatch) -> None:
    reset_report()
    monkeypatch.setenv("EVAL_COMMIT", "feed1234")
    from support.eval.report import get_report

    assert get_report().commit == "feed1234"
    reset_report()
