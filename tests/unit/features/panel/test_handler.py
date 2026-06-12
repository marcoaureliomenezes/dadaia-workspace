"""Unit tests for PanelHandler dispatch — T-2.2 / T-2.3.

Panel auth removed by operator decision 2026-06-11 — see handler.py module
docstring; the no-auth + Host-guard contract is pinned in
``test_no_auth_contract.py``.  The Bearer/launch-token/session-cookie tests that
used to live in this file (the ``T-010-21`` loopback-auth block, the ``T-011-13``
launch-token exchange block, and ``test_make_handler_class_rejects_loopback_bypass_kwarg``)
were DELETED with that change — the panel is a loopback-only local dev tool that
serves every route WITHOUT a credential.  What remains here is the still-real
behaviour: regex route dispatch, named-group capture, the 404 error contract, and
POST workflow-run dispatch/validation (now credential-free).

Tests use a thin in-process driver that wires stub view callables into
``make_handler_class`` and exercises the dispatch logic without spinning a
real HTTP server.

Stub views record which route was hit and which capture groups were passed;
they return a minimal ``(status, content_type, body)`` triple.

Assertions:
  (a) ``/`` invokes the index view with no captured groups.
  (b) ``/api/panel-status`` invokes the api_panel_status view with no captured groups.
  (c) ``/memory/foo/bar.html`` invokes the memory view with
      ``slug="foo"``, ``path="bar.html"``.
  (d) ``/memory-view/foo/bar.html`` invokes the memory_view view with
      ``slug="foo"``, ``path="bar.html"``.
  (e) ``/static/panel.css`` invokes the static view with
      ``name="panel.css"``.
  (f) ``/unknown`` returns HTTP 404 with the error-contract body.
  (g) ``/health`` returns HTTP 200 with JSON body (no credential).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler

from dadaia_workspace.features.panel.handler import _NOT_FOUND_BODY, make_handler_class

# ---------------------------------------------------------------------------
# Stub view infrastructure
# ---------------------------------------------------------------------------


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
    """Return a dict of stub views keyed by route name."""
    names = [
        "index",
        "api_panel_status",
        "health",
        "api_contexts",
        "memory",
        "memory_view",
        "static",
    ]
    return {n: _StubView(name=n) for n in names}


# ---------------------------------------------------------------------------
# In-process request driver
# ---------------------------------------------------------------------------


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

    # BaseHTTPRequestHandler expects the socket to look like a real one.
    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)

    def recv(self, n: int) -> bytes:
        return self._rfile.read(n)


def _dispatch(
    handler_class: type[BaseHTTPRequestHandler],
    path: str,
) -> tuple[int, bytes]:
    """Drive a single GET request through *handler_class* for *path*.

    Sends a loopback ``Host`` header (no credential — the panel serves every
    route without one).  Returns ``(status_code, response_body_bytes)`` from the
    fake socket's wfile.
    """
    raw_request = (f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n").encode()
    fake_sock = _FakeSocket(raw_request)

    # Instantiate the handler; it will process the request in __init__.
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]

    response = fake_sock._wfile.getvalue()

    # Parse status line: "HTTP/1.1 <code> <reason>\r\n..."
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])

    # Body is after the double CRLF.
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dispatch_index() -> None:
    """(a) GET / invokes the index stub."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    _dispatch(handler_class, "/")

    assert stubs["index"].call_count == 1
    assert stubs["index"].last_kwargs == {}
    # No other stub was called.
    for name, stub in stubs.items():
        if name != "index":
            assert stub.call_count == 0, f"Unexpected call to stub '{name}'"


def test_dispatch_api_panel_status() -> None:
    """(b) GET /api/panel-status invokes the api_panel_status stub with no captured groups."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    _dispatch(handler_class, "/api/panel-status")

    assert stubs["api_panel_status"].call_count == 1
    assert stubs["api_panel_status"].last_kwargs == {}


def test_dispatch_api_contexts() -> None:
    """GET /api/contexts invokes the api_contexts stub."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    _dispatch(handler_class, "/api/contexts")

    assert stubs["api_contexts"].call_count == 1
    assert stubs["api_contexts"].last_kwargs == {}


def test_dispatch_memory_with_named_groups() -> None:
    """(c) GET /memory/foo/bar.html invokes memory view with slug="foo", path="bar.html"."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    _dispatch(handler_class, "/memory/foo/bar.html")

    assert stubs["memory"].call_count == 1
    assert stubs["memory"].last_kwargs == {"slug": "foo", "path": "bar.html"}


def test_dispatch_memory_view_with_named_groups() -> None:
    """(d) GET /memory-view/foo/bar.html invokes memory_view with slug="foo", path="bar.html"."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    _dispatch(handler_class, "/memory-view/foo/bar.html")

    assert stubs["memory_view"].call_count == 1
    assert stubs["memory_view"].last_kwargs == {"slug": "foo", "path": "bar.html"}


def test_dispatch_static_with_named_group() -> None:
    """(e) GET /static/panel.css invokes static view with name="panel.css"."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    _dispatch(handler_class, "/static/panel.css")

    assert stubs["static"].call_count == 1
    assert stubs["static"].last_kwargs == {"name": "panel.css"}


def test_dispatch_unknown_returns_404_with_error_contract_body() -> None:
    """(f) GET /unknown returns HTTP 404 with the error-contract body (T-2.3)."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    status, body = _dispatch(handler_class, "/unknown")

    assert status == 404
    assert body == _NOT_FOUND_BODY

    # No view stub should have been called.
    for stub in stubs.values():
        assert stub.call_count == 0, f"Stub '{stub.name}' was unexpectedly called"


def test_dispatch_strips_query_string_before_matching() -> None:
    """Route matching strips query string so /api/panel-status?x=1 still dispatches."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    _dispatch(handler_class, "/api/panel-status?refresh=1")

    assert stubs["api_panel_status"].call_count == 1


def test_dispatch_health_returns_200() -> None:
    """(g) GET /health returns HTTP 200 with JSON body containing status=ok (no credential)."""
    import json

    stubs = _make_stubs()
    # Override health stub to return a realistic JSON body.
    stubs["health"].content_type = "application/json"
    stubs["health"].body = json.dumps({"status": "ok", "version": "0.1.2"}).encode()
    stubs["health"].status = 200
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    status, body = _dispatch(handler_class, "/health")

    assert status == 200
    assert stubs["health"].call_count == 1
    data = json.loads(body)
    assert data["status"] == "ok"


def test_dispatch_memory_nested_path() -> None:
    """Memory route captures multi-segment paths: /memory/foo/dir/file.html."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    _dispatch(handler_class, "/memory/foo/dir/file.html")

    assert stubs["memory"].call_count == 1
    assert stubs["memory"].last_kwargs == {"slug": "foo", "path": "dir/file.html"}


# The POST /api/workflows/<name>/run route was removed with the Run button
# (operator decision 2026-06-11: workflow DAGs are documentation, not executables).
