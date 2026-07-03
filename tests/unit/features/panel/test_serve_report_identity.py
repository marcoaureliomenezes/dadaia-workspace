"""Tests for report identity injection at serve time (operator demand 2026-06-11).

Covers ``views/api_reports.py::serve_report_file``:
  - Served HTML reports get the dadaia identity stylesheets injected into <head>.
  - The readability override (reports-doc.css) is present so inheritance wins.
  - Injection is idempotent (no double-inject when re-served).
  - Reports lacking <head>/<html> still get the identity wrapped in.
  - Non-HTML report assets (png, css, json) are served verbatim, unchanged.
  - Path traversal outside .dadaia/reports/ is rejected (403); missing => 404.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api_reports import serve_report_file


def _service(workspace_root: Path) -> PanelService:
    """Lightweight stub exposing only the attribute serve_report_file uses."""
    return cast(PanelService, SimpleNamespace(workspace_root=workspace_root))


def _write_report(tmp_path: Path, rel: str, content: bytes) -> Path:
    target = tmp_path / ".dadaia" / "reports" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return tmp_path


def test_html_report_gets_identity_injected(tmp_path: Path) -> None:
    """A served HTML report must carry the identity stylesheets in <head>."""
    html = (
        "<!DOCTYPE html><html><head><title>Report</title>"
        "<style>body{color:#eee;background:#fff}</style></head>"
        "<body><h1>Findings</h1></body></html>"
    )
    ws = _write_report(tmp_path, "ctx/agent/r.html", html.encode("utf-8"))

    view = serve_report_file(_service(ws))
    status, content_type, body = view(path="ctx/agent/r.html")

    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    out = body.decode("utf-8")
    assert '<link rel="stylesheet" href="/static/tokens.css">' in out
    assert '<link rel="stylesheet" href="/static/reports-doc.css">' in out
    # The original report content survives.
    assert "<h1>Findings</h1>" in out


def test_injected_after_head_open_before_agent_style(tmp_path: Path) -> None:
    """Base identity link is injected right after <head> (before agent <style>)."""
    html = "<html><head><style>body{color:red}</style></head><body>x</body></html>"
    ws = _write_report(tmp_path, "c/a/r.html", html.encode("utf-8"))
    view = serve_report_file(_service(ws))
    _, _, body = view(path="c/a/r.html")
    out = body.decode("utf-8")
    # The reports-doc.css link appears before the agent's inline <style>.
    assert out.index("/static/reports-doc.css") < out.index("<style>body{color:red}")


def test_injection_is_idempotent(tmp_path: Path) -> None:
    """A report already carrying the identity link is not double-injected."""
    html = (
        '<html><head><link rel="stylesheet" href="/static/reports-doc.css">'
        "</head><body>y</body></html>"
    )
    ws = _write_report(tmp_path, "c/a/done.html", html.encode("utf-8"))
    view = serve_report_file(_service(ws))
    _, _, body = view(path="c/a/done.html")
    out = body.decode("utf-8")
    assert out.count("/static/reports-doc.css") == 1


def test_report_without_head_gets_head_inserted(tmp_path: Path) -> None:
    """A bare HTML report (no <head>) still receives the identity head block."""
    html = "<html><body><p>raw report</p></body></html>"
    ws = _write_report(tmp_path, "c/a/bare.html", html.encode("utf-8"))
    view = serve_report_file(_service(ws))
    status, _, body = view(path="c/a/bare.html")
    assert status == 200
    out = body.decode("utf-8")
    assert "/static/reports-doc.css" in out
    assert "<p>raw report</p>" in out


def test_report_without_html_or_head(tmp_path: Path) -> None:
    """A fragment with neither <html> nor <head> still gets the identity."""
    html = "<p>fragment only</p>"
    ws = _write_report(tmp_path, "c/a/frag.html", html.encode("utf-8"))
    view = serve_report_file(_service(ws))
    _, _, body = view(path="c/a/frag.html")
    out = body.decode("utf-8")
    assert "/static/reports-doc.css" in out
    assert "<p>fragment only</p>" in out


def test_non_html_asset_served_verbatim(tmp_path: Path) -> None:
    """Non-HTML report assets (png) are served byte-for-byte unchanged."""
    data = bytes(range(256)) + b"\x89PNG"
    ws = _write_report(tmp_path, "c/a/diagram.png", data)
    view = serve_report_file(_service(ws))
    status, content_type, body = view(path="c/a/diagram.png")
    assert status == 200
    assert content_type == "image/png"
    assert body == data


def test_css_asset_served_verbatim(tmp_path: Path) -> None:
    """A .css asset adjacent to a report is served verbatim (no injection)."""
    css = b"body{color:#123}"
    ws = _write_report(tmp_path, "c/a/style.css", css)
    view = serve_report_file(_service(ws))
    status, content_type, body = view(path="c/a/style.css")
    assert status == 200
    assert content_type == "text/css; charset=utf-8"
    assert body == css
    assert b"reports-doc.css" not in body


def test_json_asset_served_verbatim(tmp_path: Path) -> None:
    """A .json asset is served verbatim with the json content-type."""
    payload = b'{"k": "v"}'
    ws = _write_report(tmp_path, "c/a/data.json", payload)
    view = serve_report_file(_service(ws))
    status, content_type, body = view(path="c/a/data.json")
    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    assert body == payload


def test_path_traversal_rejected(tmp_path: Path) -> None:
    """Traversal outside .dadaia/reports/ returns 403."""
    (tmp_path / ".dadaia" / "reports").mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("SECRET", encoding="utf-8")
    view = serve_report_file(_service(tmp_path))
    status, _, body = view(path="../../secret.txt")
    assert status == 403
    assert b"SECRET" not in body


def test_missing_report_returns_404(tmp_path: Path) -> None:
    """A missing report path returns 404."""
    (tmp_path / ".dadaia" / "reports").mkdir(parents=True)
    view = serve_report_file(_service(tmp_path))
    status, _, _ = view(path="c/a/nope.html")
    assert status == 404
