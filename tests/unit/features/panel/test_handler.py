"""Unit tests for PanelHandler dispatch — T-2.2 / T-2.3.

Panel auth removed by operator decision 2026-06-11 — see handler.py module
docstring; the no-auth + Host-guard contract is pinned in
``test_no_auth_contract.py``. What remains here is the still-real behaviour:
regex route dispatch (GET/DELETE/POST), named-group capture, the 404 error
contract, and query-string stripping.

One merged param dispatch table: (method, path) -> (view name, captured
kwargs) or 404, including the DELETE/POST report-important rows folded in from
test_handler_delete.py (the `/important`-before-catchall ordering is proven by
the DELETE-with-`/important`-suffix row dispatching to the unmark view, not the
plain delete view).
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler

import pytest

from dadaia_workspace.features.panel.handler import _NOT_FOUND_BODY, make_handler_class

pytestmark = pytest.mark.unit


@dataclass
class _StubView:
    """Records calls made by the handler dispatch loop."""

    name: str
    call_count: int = 0
    last_kwargs: dict[str, str] = field(default_factory=dict)
    status: int = 200
    content_type: str = "text/plain"
    body: bytes = b"ok"

    def __call__(self, **kwargs: str) -> tuple[int, str, bytes]:
        self.call_count += 1
        self.last_kwargs = dict(kwargs)
        return (self.status, self.content_type, self.body)


def _make_stubs() -> dict[str, _StubView]:
    names = [
        "index",
        "api_panel_status",
        "health",
        "api_contexts",
        "memory",
        "memory_view",
        "static",
        "api_report_delete",
        "api_report_mark_important",
        "api_report_unmark_important",
        "api_reports",
    ]
    stubs = {n: _StubView(name=n) for n in names}
    stubs["health"].content_type = "application/json"
    stubs["health"].body = json.dumps({"status": "ok", "version": "0.1.2"}).encode()
    return stubs


class _FakeSocket:
    """Minimal socket-like object for BaseHTTPRequestHandler instantiation."""

    def __init__(self, request_bytes: bytes) -> None:
        self._rfile = io.BytesIO(request_bytes)
        self._wfile = io.BytesIO()

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        if "r" in mode:
            return self._rfile
        return self._wfile

    def getsockname(self) -> tuple[str, int]:
        return ("127.0.0.1", 4999)

    def getpeername(self) -> tuple[str, int]:
        return ("127.0.0.1", 12345)

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)

    def recv(self, n: int) -> bytes:
        return self._rfile.read(n)


def _dispatch(
    handler_class: type[BaseHTTPRequestHandler],
    method: str,
    path: str,
) -> tuple[int, bytes]:
    """Drive a single request through *handler_class* for *method*/*path*.

    Sends a loopback ``Host`` header (no credential — the panel serves every
    route without one). Returns ``(status_code, response_body_bytes)``.
    """
    raw_request = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode()
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]

    response = fake_sock._wfile.getvalue()
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


@pytest.mark.parametrize(
    ("method", "path", "expected_view", "expected_kwargs"),
    [
        pytest.param("GET", "/", "index", {}, id="get-index-no-groups"),
        pytest.param(
            "GET", "/api/panel-status", "api_panel_status", {}, id="get-api-panel-status-no-groups"
        ),
        pytest.param("GET", "/api/contexts", "api_contexts", {}, id="get-api-contexts-no-groups"),
        pytest.param(
            "GET",
            "/memory/foo/bar.html",
            "memory",
            {"slug": "foo", "path": "bar.html"},
            id="get-memory-named-groups",
        ),
        pytest.param(
            "GET",
            "/memory/foo/dir/file.html",
            "memory",
            {"slug": "foo", "path": "dir/file.html"},
            id="get-memory-nested-path",
        ),
        pytest.param(
            "GET",
            "/memory-view/foo/bar.html",
            "memory_view",
            {"slug": "foo", "path": "bar.html"},
            id="get-memory-view-named-groups",
        ),
        pytest.param(
            "GET", "/static/panel.css", "static", {"name": "panel.css"}, id="get-static-named-group"
        ),
        pytest.param(
            "GET",
            "/api/panel-status?refresh=1",
            "api_panel_status",
            {},
            id="get-query-string-stripped-before-matching",
        ),
        pytest.param("GET", "/unknown", None, None, id="get-unknown-404"),
        pytest.param(
            "DELETE",
            "/api/reports/foo.html",
            "api_report_delete",
            {"path": "foo.html"},
            id="delete-report-dispatches-delete-view",
        ),
        pytest.param(
            "DELETE",
            "/api/reports/ctx/agent/file.html",
            "api_report_delete",
            {"path": "ctx/agent/file.html"},
            id="delete-report-nested-path-full-capture",
        ),
        pytest.param("DELETE", "/unknown/path", None, None, id="delete-unknown-404"),
        pytest.param(
            "POST",
            "/api/reports/ctx/agent/file.html/important",
            "api_report_mark_important",
            {"path": "ctx/agent/file.html"},
            id="post-important-before-catchall-marks",
        ),
        pytest.param(
            "DELETE",
            "/api/reports/ctx/agent/file.html/important",
            "api_report_unmark_important",
            {"path": "ctx/agent/file.html"},
            id="delete-important-before-catchall-unmarks-not-plain-delete",
        ),
        pytest.param("GET", "/health", "health", {}, id="get-health-200-json-no-credential"),
    ],
)
def test_dispatch_table(
    method: str,
    path: str,
    expected_view: str | None,
    expected_kwargs: dict[str, str] | None,
) -> None:
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    status, body = _dispatch(handler_class, method, path)

    if expected_view is None:
        assert status == 404
        assert body == _NOT_FOUND_BODY
        for stub in stubs.values():
            assert stub.call_count == 0, f"Stub '{stub.name}' was unexpectedly called"
        return

    assert status == 200
    hit = stubs[expected_view]
    assert hit.call_count == 1
    assert hit.last_kwargs == expected_kwargs
    for name, stub in stubs.items():
        if name != expected_view:
            assert stub.call_count == 0, f"Unexpected call to stub '{name}'"

    if expected_view == "health":
        data = json.loads(body)
        assert data["status"] == "ok"
