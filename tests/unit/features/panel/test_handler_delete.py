"""Unit tests for PanelHandler.do_DELETE — T-P5-31.

Covers:
  - DELETE /api/reports/<path> with valid Bearer token dispatches to api_report_delete view.
  - DELETE /api/reports/<path> without valid Bearer token returns 401.
  - DELETE /unknown/path returns 404.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler

from dadaia_workspace.features.panel.handler import make_handler_class

# ---------------------------------------------------------------------------
# Stub view infrastructure (copied pattern from test_handler.py)
# ---------------------------------------------------------------------------


@dataclass
class _StubView:
    """Records calls made by the handler dispatch loop."""

    name: str
    call_count: int = 0
    last_kwargs: dict[str, str] = field(default_factory=dict)
    status: int = 200
    content_type: str = "application/json"
    body: bytes = b'{"deleted": true}'

    def __call__(self, **kwargs: str) -> tuple[int, str, bytes]:
        self.call_count += 1
        self.last_kwargs = dict(kwargs)
        return (self.status, self.content_type, self.body)


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


def _dispatch_delete(
    handler_class: type[BaseHTTPRequestHandler],
    path: str,
    token: str | None = None,
) -> tuple[int, bytes]:
    """Drive a single DELETE request through *handler_class* for *path*.

    Returns ``(status_code, response_body_bytes)``.
    """
    auth_line = f"Authorization: Bearer {token}\r\n" if token else ""
    raw_request = (
        f"DELETE {path} HTTP/1.1\r\nHost: localhost\r\n{auth_line}\r\n".encode()
    )
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]

    response = fake_sock._wfile.getvalue()
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

_TOKEN = "test-token-abc"


def _make_views() -> dict[str, _StubView]:
    names = ["index", "api_servers", "api_contexts", "memory", "memory_view", "static"]
    views: dict[str, _StubView] = {n: _StubView(name=n) for n in names}
    views["api_report_delete"] = _StubView(name="api_report_delete")
    views["api_reports"] = _StubView(name="api_reports")
    return views  # type: ignore[return-value]


def test_delete_report_with_valid_token_dispatches_view() -> None:
    """DELETE /api/reports/foo.html with valid Bearer token calls api_report_delete view."""
    views = _make_views()
    handler_class = make_handler_class(views, token=_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_delete(handler_class, "/api/reports/foo.html", token=_TOKEN)

    assert status == 200
    assert views["api_report_delete"].call_count == 1
    assert views["api_report_delete"].last_kwargs == {"path": "foo.html"}


def test_delete_report_without_token_returns_401() -> None:
    """DELETE /api/reports/foo.html without Authorization header returns 401."""
    views = _make_views()
    handler_class = make_handler_class(views, token=_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_delete(handler_class, "/api/reports/foo.html", token=None)

    assert status == 401
    assert views["api_report_delete"].call_count == 0


def test_delete_report_with_wrong_token_returns_401() -> None:
    """DELETE /api/reports/foo.html with wrong Bearer token returns 401."""
    views = _make_views()
    handler_class = make_handler_class(views, token=_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_delete(handler_class, "/api/reports/foo.html", token="wrong-token")

    assert status == 401
    assert views["api_report_delete"].call_count == 0


def test_delete_unknown_path_returns_404() -> None:
    """DELETE /unknown/path returns 404."""
    views = _make_views()
    handler_class = make_handler_class(views, token=_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_delete(handler_class, "/unknown/path", token=_TOKEN)

    assert status == 404


def test_delete_report_nested_path_captures_full_path() -> None:
    """DELETE /api/reports/ctx/agent/file.html captures full path including slashes."""
    views = _make_views()
    handler_class = make_handler_class(views, token=_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_delete(
        handler_class, "/api/reports/ctx/agent/file.html", token=_TOKEN
    )

    assert status == 200
    assert views["api_report_delete"].call_count == 1
    assert views["api_report_delete"].last_kwargs == {"path": "ctx/agent/file.html"}
