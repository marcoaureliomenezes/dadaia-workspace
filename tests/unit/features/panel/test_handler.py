"""Unit tests for PanelHandler dispatch — T-2.2 / T-2.3.

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
  (g) ``/health`` returns HTTP 200 with JSON body (public, no auth).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler

import pytest

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


# Token used by the routing tests below.  They construct the handler with this
# token and _dispatch sends it as a Bearer header, so routing logic is exercised
# without auth getting in the way (auth itself is covered by the dedicated tests
# in the T-010-21 section).
_ROUTING_TOKEN = "routing-test-token"


def _dispatch(
    handler_class: type[BaseHTTPRequestHandler],
    path: str,
) -> tuple[int, bytes]:
    """Drive a single GET request through *handler_class* for *path*.

    Always sends ``Authorization: Bearer _ROUTING_TOKEN`` so routing tests that
    target sensitive routes are not blocked by auth.  Returns
    ``(status_code, response_body_bytes)`` from the fake socket's wfile.
    """
    raw_request = (
        f"GET {path} HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer {_ROUTING_TOKEN}\r\n\r\n"
    ).encode()
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
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

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
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

    _dispatch(handler_class, "/api/panel-status")

    assert stubs["api_panel_status"].call_count == 1
    assert stubs["api_panel_status"].last_kwargs == {}


def test_dispatch_api_contexts() -> None:
    """GET /api/contexts invokes the api_contexts stub."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

    _dispatch(handler_class, "/api/contexts")

    assert stubs["api_contexts"].call_count == 1
    assert stubs["api_contexts"].last_kwargs == {}


def test_dispatch_memory_with_named_groups() -> None:
    """(c) GET /memory/foo/bar.html invokes memory view with slug="foo", path="bar.html"."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

    _dispatch(handler_class, "/memory/foo/bar.html")

    assert stubs["memory"].call_count == 1
    assert stubs["memory"].last_kwargs == {"slug": "foo", "path": "bar.html"}


def test_dispatch_memory_view_with_named_groups() -> None:
    """(d) GET /memory-view/foo/bar.html invokes memory_view with slug="foo", path="bar.html"."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

    _dispatch(handler_class, "/memory-view/foo/bar.html")

    assert stubs["memory_view"].call_count == 1
    assert stubs["memory_view"].last_kwargs == {"slug": "foo", "path": "bar.html"}


def test_dispatch_static_with_named_group() -> None:
    """(e) GET /static/panel.css invokes static view with name="panel.css"."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

    _dispatch(handler_class, "/static/panel.css")

    assert stubs["static"].call_count == 1
    assert stubs["static"].last_kwargs == {"name": "panel.css"}


def test_dispatch_unknown_returns_404_with_error_contract_body() -> None:
    """(f) GET /unknown returns HTTP 404 with the error-contract body (T-2.3)."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

    status, body = _dispatch(handler_class, "/unknown")

    assert status == 404
    assert body == _NOT_FOUND_BODY

    # No view stub should have been called.
    for stub in stubs.values():
        assert stub.call_count == 0, f"Stub '{stub.name}' was unexpectedly called"


def test_dispatch_strips_query_string_before_matching() -> None:
    """Route matching strips query string so /api/panel-status?x=1 still dispatches."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

    _dispatch(handler_class, "/api/panel-status?refresh=1")

    assert stubs["api_panel_status"].call_count == 1


def test_dispatch_health_returns_200() -> None:
    """(g) GET /health returns HTTP 200 with JSON body containing status=ok (public, no auth)."""
    import json

    stubs = _make_stubs()
    # Override health stub to return a realistic JSON body.
    stubs["health"].content_type = "application/json"
    stubs["health"].body = json.dumps({"status": "ok", "version": "0.1.2"}).encode()
    stubs["health"].status = 200
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

    status, body = _dispatch(handler_class, "/health")

    assert status == 200
    assert stubs["health"].call_count == 1
    data = json.loads(body)
    assert data["status"] == "ok"


def test_dispatch_memory_nested_path() -> None:
    """Memory route captures multi-segment paths: /memory/foo/dir/file.html."""
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs, token=_ROUTING_TOKEN)  # type: ignore[arg-type]

    _dispatch(handler_class, "/memory/foo/dir/file.html")

    assert stubs["memory"].call_count == 1
    assert stubs["memory"].last_kwargs == {"slug": "foo", "path": "dir/file.html"}


# ---------------------------------------------------------------------------
# T-WH-18 — POST /api/workflows/<name>/run handler tests
# ---------------------------------------------------------------------------


_POST_TOKEN = "test-post-token"


@dataclass
class _PostStubView:
    name: str
    call_count: int = 0
    last_kwargs: dict[str, str] = field(default_factory=dict)
    status: int = 202
    content_type: str = "application/json"
    body: bytes = b'{"status":"started","workflow":"test","pid":1}'

    def __call__(self, **kwargs: str) -> tuple[int, str, bytes]:
        self.call_count += 1
        self.last_kwargs = dict(kwargs)
        return (self.status, self.content_type, self.body)


def _dispatch_post(
    handler_class: type[BaseHTTPRequestHandler],
    path: str,
    token: str | None = None,
) -> tuple[int, bytes]:
    auth_line = f"Authorization: Bearer {token}\r\n" if token else ""
    raw_request = f"POST {path} HTTP/1.1\r\nHost: localhost\r\n{auth_line}\r\n".encode()
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = fake_sock._wfile.getvalue()
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


def test_post_workflow_run_requires_auth() -> None:
    """POST /api/workflows/<name>/run without token returns 401."""
    run_view = _PostStubView(name="api_workflow_run")
    stubs = _make_stubs()
    stubs["api_workflow_run"] = run_view  # type: ignore[assignment]
    handler_class = make_handler_class(stubs, token=_POST_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_post(handler_class, "/api/workflows/my-workflow/run")

    assert status == 401
    assert run_view.call_count == 0


def test_post_workflow_run_rejects_invalid_name() -> None:
    """POST /api/workflows/<name>/run with shell-unsafe name returns 400."""
    run_view = _PostStubView(name="api_workflow_run")
    stubs = _make_stubs()
    stubs["api_workflow_run"] = run_view  # type: ignore[assignment]
    handler_class = make_handler_class(stubs, token=_POST_TOKEN)  # type: ignore[arg-type]

    # Shell-unsafe: contains semicolon
    status, body = _dispatch_post(handler_class, "/api/workflows/bad;name/run", token=_POST_TOKEN)

    assert status == 400
    assert run_view.call_count == 0


def test_post_workflow_run_dispatches_view_with_valid_token() -> None:
    """POST /api/workflows/<name>/run with valid token dispatches to api_workflow_run."""
    run_view = _PostStubView(name="api_workflow_run")
    stubs = _make_stubs()
    stubs["api_workflow_run"] = run_view  # type: ignore[assignment]
    handler_class = make_handler_class(stubs, token=_POST_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_post(handler_class, "/api/workflows/my-workflow/run", token=_POST_TOKEN)

    assert status == 202
    assert run_view.call_count == 1
    assert run_view.last_kwargs == {"workflow_name": "my-workflow"}


# ---------------------------------------------------------------------------
# T-010-21 R7c — panel loopback auth (sec F-3): the loopback bypass is removed.
# A tokenless request to a sensitive API returns 401 even on 127.0.0.1.
# ---------------------------------------------------------------------------

_BYPASS_TOKEN = "test-bypass-token"


def _make_stubs_with_api_reports() -> dict[str, _StubView]:
    """Return stubs that include an api_reports entry.

    ``api_reports`` is in ``_BEARER_AUTH_ROUTE_NAMES`` (exercises the auth
    branch) AND in ``_BEARER_ONLY_ROUTES`` (no telemetry stub required), making
    it the ideal route for loopback_bypass unit tests.
    """
    stubs = _make_stubs()
    stubs["api_reports"] = _StubView(
        name="api_reports",
        status=200,
        content_type="application/json",
        body=b'{"reports": []}',
    )
    return stubs


def _dispatch_get_with_auth(
    handler_class: type[BaseHTTPRequestHandler],
    path: str,
    token: str | None = None,
) -> tuple[int, bytes]:
    """Drive a single GET request with an optional Authorization header."""
    auth_line = f"Authorization: Bearer {token}\r\n" if token else ""
    raw_request = f"GET {path} HTTP/1.1\r\nHost: localhost\r\n{auth_line}\r\n".encode()
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = fake_sock._wfile.getvalue()
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


def test_tokenless_loopback_request_to_sensitive_api_returns_401() -> None:
    """(F-3 contract pin) GET /api/* with no Authorization header returns 401.

    There is no loopback bypass: a tokenless request to a sensitive API is
    rejected even when the panel is bound to 127.0.0.1.  Uses ``/api/reports``
    (bearer-only, no telemetry required) so the auth branch runs end-to-end.
    """
    stubs = _make_stubs_with_api_reports()
    handler_class = make_handler_class(stubs, token=_BYPASS_TOKEN)  # type: ignore[arg-type]

    status, body = _dispatch_get_with_auth(handler_class, "/api/reports")

    assert status == 401
    assert b"unauthorized" in body
    assert stubs["api_reports"].call_count == 0


def test_tokenless_request_to_bearer_second_loop_route_returns_401() -> None:
    """(F-3) BEARER_SECOND_LOOP routes (sensitive data) also require a token.

    ``/api/panel-status`` and ``/api/contexts`` expose workspace state; the old
    code waived their auth on loopback. They must now 401 without a Bearer token.
    """
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs, token=_BYPASS_TOKEN)  # type: ignore[arg-type]

    for path in ("/api/panel-status", "/api/contexts"):
        status, body = _dispatch_get_with_auth(handler_class, path)
        assert status == 401, f"{path} must 401 without a token"
        assert b"unauthorized" in body
    assert stubs["api_panel_status"].call_count == 0
    assert stubs["api_contexts"].call_count == 0


def test_no_bypass_rejects_invalid_token_for_api_get() -> None:
    """GET /api/* with an invalid Bearer token returns 401."""
    stubs = _make_stubs_with_api_reports()
    handler_class = make_handler_class(stubs, token=_BYPASS_TOKEN)  # type: ignore[arg-type]

    status, body = _dispatch_get_with_auth(handler_class, "/api/reports", token="wrong-token")

    assert status == 401
    assert b"unauthorized" in body
    assert stubs["api_reports"].call_count == 0


def test_valid_token_works_for_sensitive_api() -> None:
    """A valid Bearer token grants access to a sensitive API."""
    stubs = _make_stubs_with_api_reports()
    handler_class = make_handler_class(stubs, token=_BYPASS_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_get_with_auth(handler_class, "/api/reports", token=_BYPASS_TOKEN)

    assert status == 200
    assert stubs["api_reports"].call_count == 1


def test_public_routes_stay_tokenless() -> None:
    """PUBLIC routes (index, health, static) remain reachable without a token.

    Removing the loopback bypass must NOT lock out the static/landing surface;
    only sensitive APIs require auth.
    """
    stubs = _make_stubs()
    handler_class = make_handler_class(stubs, token=_BYPASS_TOKEN)  # type: ignore[arg-type]

    for path, route in (("/", "index"), ("/health", "health"), ("/static/x.css", "static")):
        status, _ = _dispatch_get_with_auth(handler_class, path)
        assert status == 200, f"PUBLIC route {path} must serve without a token"
        assert stubs[route].call_count == 1


# ---------------------------------------------------------------------------
# T-011-13 — panel launch token exchange (ADR-10 / AC-W4-02)
#
# The launch URL carries ONLY a single-use launch token (`?launch=<tok>`).  On
# first GET of the shell the server consumes the token and sets the session
# cookie (SameSite=Strict; HttpOnly), carrying the Bearer.  The token is then
# invalidated — replay / expiry ⇒ 401.  Sensitive APIs stay Bearer-only (the
# cookie gates only the UI shell).
# ---------------------------------------------------------------------------

_LAUNCH_BEARER = "launch-bearer-token"


def _dispatch_get_full(
    handler_class: type[BaseHTTPRequestHandler],
    path: str,
    token: str | None = None,
) -> tuple[int, dict[str, list[str]], bytes]:
    """GET *path*; return (status, headers, body). Headers map name→list of values."""
    auth_line = f"Authorization: Bearer {token}\r\n" if token else ""
    raw_request = f"GET {path} HTTP/1.1\r\nHost: localhost\r\n{auth_line}\r\n".encode()
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = fake_sock._wfile.getvalue()
    head, _, body = response.partition(b"\r\n\r\n")
    head_lines = head.split(b"\r\n")
    status_code = int(head_lines[0].split(b" ")[1])
    headers: dict[str, list[str]] = {}
    for line in head_lines[1:]:
        if b":" in line:
            name, _, value = line.partition(b":")
            headers.setdefault(name.decode().strip().lower(), []).append(value.decode().strip())
    return status_code, headers, body


def _make_launch_store():
    from dadaia_workspace.features.panel.auth import LaunchTokenStore

    return LaunchTokenStore(ttl_seconds=60)


def test_launch_token_first_use_sets_session_cookie() -> None:
    """First GET /?launch=<tok> sets the SameSite=Strict; HttpOnly session cookie."""
    store = _make_launch_store()
    launch_tok = store.mint()
    stubs = _make_stubs()
    handler_class = make_handler_class(
        stubs,  # type: ignore[arg-type]
        token=_LAUNCH_BEARER,
        launch_token_store=store,
    )

    status, headers, _ = _dispatch_get_full(handler_class, f"/?launch={launch_tok}")

    assert status == 200
    assert stubs["index"].call_count == 1
    cookies = headers.get("set-cookie", [])
    assert cookies, "first launch-token use must emit a Set-Cookie header"
    cookie = cookies[0].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    # The cookie carries the Bearer as the session credential.
    assert _LAUNCH_BEARER in cookies[0]


def test_launch_token_replay_is_401() -> None:
    """A consumed launch token replayed ⇒ 401 (single-use; the binding contract)."""
    store = _make_launch_store()
    launch_tok = store.mint()
    stubs = _make_stubs()
    handler_class = make_handler_class(
        stubs,  # type: ignore[arg-type]
        token=_LAUNCH_BEARER,
        launch_token_store=store,
    )

    first, _, _ = _dispatch_get_full(handler_class, f"/?launch={launch_tok}")
    assert first == 200

    status, headers, _ = _dispatch_get_full(handler_class, f"/?launch={launch_tok}")
    assert status == 401, "replay of a consumed launch token must be rejected"
    assert "set-cookie" not in headers, "replay must not mint a session cookie"


def test_expired_launch_token_is_401() -> None:
    """A launch token used after TTL expiry ⇒ 401."""
    from dadaia_workspace.features.panel.auth import LaunchTokenStore

    now = [1000.0]
    store = LaunchTokenStore(ttl_seconds=60, clock=lambda: now[0])
    launch_tok = store.mint()
    stubs = _make_stubs()
    handler_class = make_handler_class(
        stubs,  # type: ignore[arg-type]
        token=_LAUNCH_BEARER,
        launch_token_store=store,
    )

    now[0] = 1061.0  # past the 60s TTL
    status, _, _ = _dispatch_get_full(handler_class, f"/?launch={launch_tok}")
    assert status == 401


def test_index_without_launch_token_stays_public_no_cookie() -> None:
    """GET / with no launch token serves the public shell and sets no cookie.

    loopback-tokenless-GET precedence: PUBLIC routes serve without a launch
    token; the launch token only adds the cookie-mint side effect on first use.
    """
    store = _make_launch_store()
    stubs = _make_stubs()
    handler_class = make_handler_class(
        stubs,  # type: ignore[arg-type]
        token=_LAUNCH_BEARER,
        launch_token_store=store,
    )

    status, headers, _ = _dispatch_get_full(handler_class, "/")
    assert status == 200
    assert stubs["index"].call_count == 1
    assert "set-cookie" not in headers


def test_launch_token_does_not_relax_sensitive_api_auth() -> None:
    """ADR-10: the launch token / cookie gates only the UI shell.

    A sensitive API GET still requires the Bearer header — a (bogus) launch
    query param on an API path must not grant access.
    """
    store = _make_launch_store()
    launch_tok = store.mint()
    stubs = _make_stubs_with_api_reports()
    handler_class = make_handler_class(
        stubs,  # type: ignore[arg-type]
        token=_LAUNCH_BEARER,
        launch_token_store=store,
    )

    status, headers, body = _dispatch_get_full(handler_class, f"/api/reports?launch={launch_tok}")
    assert status == 401, "launch token must not authorize a sensitive API"
    assert b"unauthorized" in body
    assert "set-cookie" not in headers
    assert stubs["api_reports"].call_count == 0


def test_invalid_launch_token_on_index_is_401() -> None:
    """An unknown launch token on the shell route ⇒ 401 (not a silent public serve)."""
    store = _make_launch_store()
    stubs = _make_stubs()
    handler_class = make_handler_class(
        stubs,  # type: ignore[arg-type]
        token=_LAUNCH_BEARER,
        launch_token_store=store,
    )

    status, headers, _ = _dispatch_get_full(handler_class, "/?launch=never-minted")
    assert status == 401
    assert "set-cookie" not in headers


def test_make_handler_class_rejects_loopback_bypass_kwarg() -> None:
    """The loopback_bypass parameter is removed; passing it is a TypeError.

    Pins that the insecure bypass cannot be re-enabled by a caller.
    """
    stubs = _make_stubs_with_api_reports()
    with pytest.raises(TypeError):
        make_handler_class(stubs, token=_BYPASS_TOKEN, loopback_bypass=True)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Second-loop auth gate (F-01 / F-02 / F-04)
#
# Routes that expose workspace-sensitive data — server registry/ports, repo
# filesystem paths, and report/memory file contents — are dispatched by the
# non-telemetry loop. They require Bearer auth unconditionally; there is no
# loopback exemption (sec F-3 / T-010-21 R7c).
# ---------------------------------------------------------------------------

_SENSITIVE_ROUTE_CASES = [
    ("/api/panel-status", "api_panel_status"),
    ("/api/contexts", "api_contexts"),
    ("/reports/sub/report.html", "reports_serve"),
    ("/memory/foo/bar.html", "memory"),
    ("/memory-view/foo/bar.html", "memory_view"),
]


def _make_stubs_with_reports_serve() -> dict[str, _StubView]:
    stubs = _make_stubs()
    stubs["reports_serve"] = _StubView(name="reports_serve")
    return stubs


@pytest.mark.parametrize(("path", "route_name"), _SENSITIVE_ROUTE_CASES)
def test_sensitive_route_requires_token(path: str, route_name: str) -> None:
    stubs = _make_stubs_with_reports_serve()
    handler_class = make_handler_class(stubs, token=_BYPASS_TOKEN)  # type: ignore[arg-type]

    status, body = _dispatch_get_with_auth(handler_class, path)

    assert status == 401
    assert b"unauthorized" in body
    assert stubs[route_name].call_count == 0


@pytest.mark.parametrize(("path", "route_name"), _SENSITIVE_ROUTE_CASES)
def test_sensitive_route_rejects_invalid_token(path: str, route_name: str) -> None:
    stubs = _make_stubs_with_reports_serve()
    handler_class = make_handler_class(stubs, token=_BYPASS_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_get_with_auth(handler_class, path, token="wrong-token")

    assert status == 401
    assert stubs[route_name].call_count == 0


@pytest.mark.parametrize(("path", "route_name"), _SENSITIVE_ROUTE_CASES)
def test_sensitive_route_allows_valid_token(path: str, route_name: str) -> None:
    stubs = _make_stubs_with_reports_serve()
    handler_class = make_handler_class(stubs, token=_BYPASS_TOKEN)  # type: ignore[arg-type]

    status, _ = _dispatch_get_with_auth(handler_class, path, token=_BYPASS_TOKEN)

    assert status == 200
    assert stubs[route_name].call_count == 1
