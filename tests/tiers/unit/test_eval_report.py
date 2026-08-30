"""Unit tests for evaluation report rendering."""

from __future__ import annotations

from support.eval.report import EvalReport, PercentileTimings, render_markdown


def test_render_markdown_perf_table() -> None:
    report = EvalReport(commit="abc1234567890", store_image="ontotext/graphdb:10.8.4")
    report.add_perf(
        scenario="cartesian",
        scale="N10-K2",
        rows=256,
        entities=10,
        translate_ms=1.2,
        store=PercentileTimings(p50=5.0, p95=6.0, p99=7.0),
        convert=PercentileTimings(p50=20.0, p95=25.0, p99=30.0),
    )
    md = render_markdown(report)
    assert "### cartesian" in md
    assert "N10-K2" in md
    assert "256" in md
    assert "1.2" in md
    assert "5.0/6.0/7.0" in md


def test_report_roundtrip_json(tmp_path) -> None:
    report = EvalReport(commit="abc", store_image="ontotext/graphdb:10.8.4")
    report.add_perf(
        scenario="cartesian",
        scale="N10-K2",
        rows=1,
        entities=1,
        translate_ms=0.1,
        store=PercentileTimings(p50=1.0, p95=2.0, p99=3.0),
        convert=PercentileTimings(p50=4.0, p95=5.0, p99=6.0),
    )
    path = tmp_path / "report.json"
    report.write_json(path)
    loaded = EvalReport.load_json(path)
    assert loaded.commit == "abc"
    assert len(loaded.perf) == 1
    assert loaded.perf[0].rows == 1
