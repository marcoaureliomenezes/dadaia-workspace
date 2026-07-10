"""Tests for report identity injection at serve time (operator demand 2026-06-11).

Covers ``views/api_reports.py::serve_report_file``. Three survivors:
  1. Identity injection param: with head / no head / fragment (neither
     <html> nor <head>) / idempotent / ordering-before-agent-style.
  2. Non-HTML verbatim param: png/css/json.
  3. Traversal 403 + missing 404.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api_reports import serve_report_file

pytestmark = pytest.mark.unit


def _service(workspace_root: Path) -> PanelService:
    """Lightweight stub exposing only the attribute serve_report_file uses."""
    return cast(PanelService, SimpleNamespace(workspace_root=workspace_root))


def _write_report(tmp_path: Path, rel: str, content: bytes) -> Path:
    target = tmp_path / ".dadaia" / "reports" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Identity injection param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "html", "expected_snippets"),
    [
        pytest.param(
            "ctx/agent/r.html",
            "<!DOCTYPE html><html><head><title>Report</title>"
            "<style>body{color:#eee;background:#fff}</style></head>"
            "<body><h1>Findings</h1></body></html>",
            [
                '<link rel="stylesheet" href="/static/tokens.css">',
                '<link rel="stylesheet" href="/static/reports-doc.css">',
                "<h1>Findings</h1>",
            ],
            id="with-head-gets-identity-injected",
        ),
        pytest.param(
            "c/a/bare.html",
            "<html><body><p>raw report</p></body></html>",
            ["/static/reports-doc.css", "<p>raw report</p>"],
            id="no-head-still-injects",
        ),
        pytest.param(
            "c/a/frag.html",
            "<p>fragment only</p>",
            ["/static/reports-doc.css", "<p>fragment only</p>"],
            id="fragment-no-html-no-head-still-injects",
        ),
    ],
)
def test_identity_injection(
    tmp_path: Path, rel: str, html: str, expected_snippets: list[str]
) -> None:
    ws = _write_report(tmp_path, rel, html.encode("utf-8"))
    view = serve_report_file(_service(ws))
    status, content_type, body = view(path=rel)

    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    out = body.decode("utf-8")
    for snippet in expected_snippets:
        assert snippet in out

    # Only run the shared idempotency/ordering checks once (independent of
    # which row above triggered this call).
    if rel != "ctx/agent/r.html":
        return

    # Injection is idempotent — a report already carrying the identity link is
    # not double-injected.
    already_linked = (
        '<html><head><link rel="stylesheet" href="/static/reports-doc.css">'
        "</head><body>y</body></html>"
    )
    ws_idempotent = _write_report(
        tmp_path / "idempotent", "c/a/done.html", already_linked.encode("utf-8")
    )
    view_idempotent = serve_report_file(_service(ws_idempotent))
    _, _, body_idempotent = view_idempotent(path="c/a/done.html")
    out_idempotent = body_idempotent.decode("utf-8")
    assert out_idempotent.count("/static/reports-doc.css") == 1

    # Ordering: the base identity link is injected right after <head>, BEFORE
    # the agent's own inline <style>.
    with_style = "<html><head><style>body{color:red}</style></head><body>x</body></html>"
    ws_ordered = _write_report(tmp_path / "ordered", "c/a/r.html", with_style.encode("utf-8"))
    view_ordered = serve_report_file(_service(ws_ordered))
    _, _, body_ordered = view_ordered(path="c/a/r.html")
    out_ordered = body_ordered.decode("utf-8")
    assert out_ordered.index("/static/reports-doc.css") < out_ordered.index(
        "<style>body{color:red}"
    )


# ---------------------------------------------------------------------------
# 2. Non-HTML verbatim param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "content", "expected_ct", "check_no_injection"),
    [
        pytest.param(
            "c/a/diagram.png", bytes(range(256)) + b"\x89PNG", "image/png", False, id="png-verbatim"
        ),
        pytest.param(
            "c/a/style.css", b"body{color:#123}", "text/css; charset=utf-8", True, id="css-verbatim"
        ),
        pytest.param(
            "c/a/data.json",
            b'{"k": "v"}',
            "application/json; charset=utf-8",
            False,
            id="json-verbatim",
        ),
    ],
)
def test_non_html_assets_served_verbatim(
    tmp_path: Path, rel: str, content: bytes, expected_ct: str, check_no_injection: bool
) -> None:
    ws = _write_report(tmp_path, rel, content)
    view = serve_report_file(_service(ws))
    status, content_type, body = view(path=rel)
    assert status == 200
    assert content_type == expected_ct
    assert body == content
    if check_no_injection:
        assert b"reports-doc.css" not in body


# ---------------------------------------------------------------------------
# 3. Traversal 403 + missing 404
# ---------------------------------------------------------------------------


def test_path_traversal_rejected_and_missing_report_404(tmp_path: Path) -> None:
    (tmp_path / ".dadaia" / "reports").mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("SECRET", encoding="utf-8")
    view = serve_report_file(_service(tmp_path))

    status_traversal, _, body_traversal = view(path="../../secret.txt")
    assert status_traversal == 403
    assert b"SECRET" not in body_traversal

    status_missing, _, _ = view(path="c/a/nope.html")
    assert status_missing == 404
