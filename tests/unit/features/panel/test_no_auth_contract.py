"""Contract pins for the no-auth loopback panel (operator decision 2026-06-11).

Panel auth was removed in full: no Bearer, no launch token, no session cookie.
The panel is a loopback-only (127.0.0.1-bound) local dev tool that serves every
route WITHOUT a credential.  The only residual guard is a silent Host-header
allowlist (``_is_allowed_host``) returning 403 for a foreign ``Host`` value —
DNS-rebinding protection, NOT authentication.  See ``handler.py``'s module
docstring for the full rationale.

This file is the permanent pin of that contract:
  (a) every formerly-Bearer route serves its contractual status (200, or 503 for
      telemetry routes when telemetry is None) with NO credential header on the
      request;
  (b) ``Host`` allowlist — a foreign Host ⇒ 403 on every route class (including
      PUBLIC); loopback Host variants pass; a missing Host passes (per the
      handler implementation, which allows non-browser clients);
  (c) the handler module exposes NO launch / cookie / token-validation symbols
      (import-level assert that the dead surface cannot be re-introduced).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler

import pytest

from dadaia_workspace.features.panel import handler as handler_module
from dadaia_workspace.features.panel.handler import make_handler_class

# ---------------------------------------------------------------------------
# In-process driver (no credential headers ever sent)
# ---------------------------------------------------------------------------


@dataclass
class _StubView:
    name: str
    call_count: int = 0
    last_kwargs: dict[str, str] = field(default_factory=dict)
    status: int = 200
    content_type: str = "application/json"
    body: bytes = b'{"ok": true}'

    def __call__(self, **kwargs: str) -> tuple[int, str, bytes]:
        self.call_count += 1
        self.last_kwargs = dict(kwargs)
        return (self.status, self.content_type, self.body)


class _FakeSocket:
    def __init__(self, request_bytes: bytes) -> None:
        self._rfile = io.BytesIO(request_bytes)
        self._wfile = io.BytesIO()

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        return self._rfile if "r" in mode else self._wfile

    def getsockname(self) -> tuple[str, int]:
        return ("127.0.0.1", 3742)

    def getpeername(self) -> tuple[str, int]:
        return ("127.0.0.1", 12345)

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)

    def recv(self, n: int) -> bytes:
        return self._rfile.read(n)


# A full view set covering every route name in the route table so that no route
# falls through to a 404 for a missing-view reason — the only non-200 we expect
# is a deliberate 403 (foreign Host) or 503 (telemetry routes with no telemetry).
_ALL_VIEW_NAMES = [
    "index",
    "health",
    "static",
    "api_panel_status",
    "api_contexts",
    "memory",
    "memory_view",
    "reports_serve",
    "api_academy",
    "api_kanban",
    "api_reports",
    "api_report_delete",
    "api_report_mark_important",
    "api_agent_prompt",
    "api_workflow_run",
    "api_workflow_detail",
    "api_workflows",
]


def _make_all_stubs() -> dict[str, _StubView]:
    return {n: _StubView(name=n) for n in _ALL_VIEW_NAMES}


def _dispatch(
    handler_class: type[BaseHTTPRequestHandler],
    path: str,
    *,
    host: str | None = "localhost",
) -> tuple[int, bytes]:
    """GET *path* with the given (or no) Host header and NO credential header."""
    host_line = f"Host: {host}\r\n" if host is not None else ""
    raw_request = f"GET {path} HTTP/1.1\r\n{host_line}\r\n".encode()
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = fake_sock._wfile.getvalue()
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


# ---------------------------------------------------------------------------
# (a) Every formerly-Bearer route serves 200 with NO credential header.
# ---------------------------------------------------------------------------

# (path, route_name) for routes that dispatch directly through a view (200).
_VIEW_ROUTE_CASES = [
    ("/", "index"),
    ("/health", "health"),
    ("/static/panel.css", "static"),
    ("/api/panel-status", "api_panel_status"),
    ("/api/contexts", "api_contexts"),
    ("/memory/foo/bar.md", "memory"),
    ("/memory-view/foo/bar.md", "memory_view"),
    ("/reports/sub/report.html", "reports_serve"),
    ("/api/academy", "api_academy"),
    ("/api/kanban", "api_kanban"),
    ("/api/reports", "api_reports"),
    ("/api/agents/software-engineer/prompt", "api_agent_prompt"),
    ("/api/workflows", "api_workflows"),
    ("/api/workflows/audit-fanout", "api_workflow_detail"),
]


@pytest.mark.parametrize(("path", "route_name"), _VIEW_ROUTE_CASES)
def test_route_serves_200_without_any_credential(path: str, route_name: str) -> None:
    """Every formerly-Bearer / PUBLIC / second-loop route serves 200 with no credential."""
    stubs = _make_all_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    status, _ = _dispatch(handler_class, path)

    assert status == 200, f"{path} must serve 200 with no credential, got {status}"
    assert stubs[route_name].call_count == 1


_TELEMETRY_ROUTE_PATHS = [
    "/api/agents",
    "/api/agents/software-engineer/sessions",
    "/api/sessions",
]


@pytest.mark.parametrize("path", _TELEMETRY_ROUTE_PATHS)
def test_telemetry_route_503_when_telemetry_absent_no_credential(path: str) -> None:
    """Telemetry routes 503 (not 401/403) when telemetry is None — credential-free.

    The residual behaviour of the BEARER_TELEMETRY class is the 503-when-unavailable
    contract, NOT a credential check.
    """
    stubs = _make_all_stubs()
    handler_class = make_handler_class(stubs, telemetry=None)  # type: ignore[arg-type]

    status, body = _dispatch(handler_class, path)

    assert status == 503, f"{path} must 503 without telemetry, got {status}"
    assert b"telemetry not configured" in body


# ---------------------------------------------------------------------------
# (b) Host-header allowlist (DNS-rebinding guard — applies to EVERY route).
# ---------------------------------------------------------------------------

_ALL_ROUTE_CLASS_PATHS = [
    "/",  # PUBLIC
    "/health",  # PUBLIC
    "/api/panel-status",  # BEARER_SECOND_LOOP
    "/api/reports",  # BEARER
    "/api/agents",  # BEARER_TELEMETRY
]


@pytest.mark.parametrize("path", _ALL_ROUTE_CLASS_PATHS)
def test_foreign_host_is_403_on_every_route_class(path: str) -> None:
    """A foreign Host ⇒ 403 on every route class, including PUBLIC (DNS-rebinding)."""
    stubs = _make_all_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    status, body = _dispatch(handler_class, path, host="evil.example.com")

    assert status == 403, f"{path} with foreign Host must 403, got {status}"
    assert b"forbidden host" in body
    # The view must not have run for the foreign-host request on view routes.
    if path in {"/", "/health", "/api/panel-status", "/api/reports"}:
        for stub in stubs.values():
            assert stub.call_count == 0


@pytest.mark.parametrize(
    "host",
    ["127.0.0.1:3742", "localhost:9999", "[::1]:80", "127.0.0.1", "localhost", "[::1]"],
)
def test_loopback_host_variants_pass(host: str) -> None:
    """Loopback Host variants (with or without a port) reach the route."""
    stubs = _make_all_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    status, _ = _dispatch(handler_class, "/", host=host)

    assert status == 200, f"loopback Host {host!r} must pass, got {status}"
    assert stubs["index"].call_count == 1


def test_missing_host_passes() -> None:
    """A missing Host header passes (handler allows non-browser clients).

    Pinned from the handler implementation (``_is_allowed_host`` returns True for
    an absent/empty Host): the threat model is a browser tricked into sending a
    foreign Host, which always sets the header — a curl/HTTP-1.0 client without a
    Host is not the threat.
    """
    stubs = _make_all_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    status, _ = _dispatch(handler_class, "/", host=None)

    assert status == 200
    assert stubs["index"].call_count == 1


def test_is_allowed_host_unit_contract() -> None:
    """Direct unit pin of the Host allowlist predicate."""
    allowed = handler_module._is_allowed_host
    assert allowed("127.0.0.1") is True
    assert allowed("127.0.0.1:3742") is True
    assert allowed("localhost") is True
    assert allowed("localhost:9999") is True
    assert allowed("[::1]") is True
    assert allowed("[::1]:80") is True
    assert allowed(None) is True
    assert allowed("") is True
    assert allowed("evil.example.com") is False
    assert allowed("evil.example.com:3742") is False
    assert allowed("10.0.0.5") is False
    assert allowed("[::1") is False  # malformed IPv6 literal


# ---------------------------------------------------------------------------
# (c) The handler module exposes NO launch / cookie / token-validation surface.
# ---------------------------------------------------------------------------

_FORBIDDEN_HANDLER_SYMBOLS = [
    "LaunchTokenStore",
    "build_session_cookie",
    "ensure_token",
    "validate",
    "SESSION_COOKIE_NAME",
    "_consume_launch_token",
]


@pytest.mark.parametrize("symbol", _FORBIDDEN_HANDLER_SYMBOLS)
def test_handler_module_has_no_dead_auth_symbol(symbol: str) -> None:
    """The handler module must not expose any launch/cookie/token-validation symbol."""
    assert not hasattr(handler_module, symbol), (
        f"handler module still exposes dead auth symbol {symbol!r} — "
        "panel auth was removed by operator decision 2026-06-11"
    )


def test_deleted_auth_module_is_gone() -> None:
    """``dadaia_workspace.features.panel.auth`` must no longer be importable."""
    with pytest.raises(ModuleNotFoundError):
        import dadaia_workspace.features.panel.auth  # type: ignore[import-not-found]  # noqa: F401


def test_make_handler_class_takes_no_launch_store_kwarg() -> None:
    """The launch-token-store / loopback-bypass kwargs are gone (cannot re-enable)."""
    stubs = _make_all_stubs()
    with pytest.raises(TypeError):
        make_handler_class(stubs, launch_token_store=object())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        make_handler_class(stubs, loopback_bypass=True)  # type: ignore[call-arg]
