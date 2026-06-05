"""Reports tab JavaScript asset contracts."""

from __future__ import annotations

from pathlib import Path

REPORTS_JS = (
    Path(__file__).resolve().parents[4]
    / "dadaia_workspace"
    / "features"
    / "panel"
    / "views"
    / "assets"
    / "js"
    / "reports.js"
)


def test_reports_js_preserves_path_separators_when_encoding_report_paths() -> None:
    """Report route paths must encode segments without turning '/' into '%2F'."""
    source = REPORTS_JS.read_text(encoding="utf-8")

    assert "function encodeReportPath(path)" in source
    assert ".split('/')" in source
    assert ".join('/')" in source
    assert "fetch('/reports/' + encodeReportPath(report.path))" in source
    assert "authedFetch('/api/reports/' + encodeReportPath(report.path)" in source
    assert "+ '/important'" in source
    assert "fetch('/reports/' + encodeURIComponent(report.path))" not in source
    assert "authedFetch('/api/reports/' + encodeURIComponent(report.path)" not in source
