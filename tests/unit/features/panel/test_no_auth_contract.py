"""Contract pins for the no-auth loopback panel (operator decision 2026-06-11).

Panel auth was removed in full: no Bearer, no launch token, no session cookie.
The panel is a loopback-only (127.0.0.1-bound) local dev tool that serves every
route WITHOUT a credential.  The only residual guard is a silent Host-header
allowlist (``_is_allowed_host``) returning 403 for a foreign ``Host`` value —
DNS-rebinding protection, NOT authentication.  See ``handler.py``'s module
docstring for the full rationale.

This file is the SINGLE OWNER of Host-guard/no-auth coverage — every other
panel test file's foreign-host duplicate was deleted in its favor. Four
survivors, one per real decision:
  1. Every route class serves its contract status credential-free (200 param +
     telemetry-503 param).
  2. Foreign Host 403 on every route class, view never runs.
  3. Loopback/missing-Host pass + the ``_is_allowed_host`` predicate table.
  4. No dead auth symbol + auth module gone + no launch-store kwargs.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler

import pytest

from dadaia_workspace.features.panel import handler as handler_module
from dadaia_workspace.features.panel.handler import make_handler_class

pytestmark = pytest.mark.unit


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
    "api_reports",
    "api_report_delete",
    "api_report_mark_important",
    "api_agent_prompt",
    "api_workflow_run",
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
# 1. Every route class serves its contract status credential-free
# ---------------------------------------------------------------------------

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
    ("/api/reports", "api_reports"),
    ("/api/agents/software-engineer/prompt", "api_agent_prompt"),
]

_TELEMETRY_ROUTE_PATHS = [
    "/api/agents",
    "/api/agents/software-engineer/sessions",
    "/api/sessions",
]


@pytest.mark.parametrize(
    ("path", "route_name"),
    [(p, r) for p, r in _VIEW_ROUTE_CASES] + [(p, None) for p in _TELEMETRY_ROUTE_PATHS],
    ids=[f"200-{r}" for _, r in _VIEW_ROUTE_CASES]
    + [f"503-telemetry-{p}" for p in _TELEMETRY_ROUTE_PATHS],
)
def test_route_serves_its_contract_status_without_any_credential(
    path: str, route_name: str | None
) -> None:
    """Every route class serves its contract status credential-free.

    Formerly-Bearer / PUBLIC / second-loop routes serve 200; telemetry routes
    503 (not 401/403) when telemetry is None — the residual behaviour of the
    BEARER_TELEMETRY class is the 503-when-unavailable contract, NOT a
    credential check. No request in this file ever sends a credential header.
    """
    if route_name is not None:
        stubs = _make_all_stubs()
        handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

        status, _ = _dispatch(handler_class, path)

        assert status == 200, f"{path} must serve 200 with no credential, got {status}"
        assert stubs[route_name].call_count == 1
    else:
        stubs = _make_all_stubs()
        handler_class = make_handler_class(stubs, telemetry=None)  # type: ignore[arg-type]

        status, body = _dispatch(handler_class, path)

        assert status == 503, f"{path} must 503 without telemetry, got {status}"
        assert b"telemetry not configured" in body


# ---------------------------------------------------------------------------
# 2. Foreign Host 403 on every route class, view never runs
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
    """A foreign Host => 403 on every route class, including PUBLIC (DNS-rebinding)."""
    stubs = _make_all_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    status, body = _dispatch(handler_class, path, host="evil.example.com")

    assert status == 403, f"{path} with foreign Host must 403, got {status}"
    assert b"forbidden host" in body
    if path in {"/", "/health", "/api/panel-status", "/api/reports"}:
        for stub in stubs.values():
            assert stub.call_count == 0


# ---------------------------------------------------------------------------
# 3. Loopback/missing-Host pass + the _is_allowed_host predicate table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "host",
    ["127.0.0.1:3742", "localhost:9999", "[::1]:80", "127.0.0.1", "localhost", "[::1]", None],
)
def test_loopback_and_missing_host_pass_and_predicate_table(host: str | None) -> None:
    """Loopback Host variants (with or without a port) AND a missing Host both pass,
    matching the ``_is_allowed_host`` predicate table directly.

    A missing Host header passes (``_is_allowed_host`` returns True for an
    absent/empty Host): the threat model is a browser tricked into sending a
    foreign Host, which always sets the header — a curl/HTTP-1.0 client without
    a Host is not the threat.
    """
    stubs = _make_all_stubs()
    handler_class = make_handler_class(stubs)  # type: ignore[arg-type]

    status, _ = _dispatch(handler_class, "/", host=host)

    assert status == 200, f"Host {host!r} must pass, got {status}"
    assert stubs["index"].call_count == 1

    # Direct unit pin of the Host allowlist predicate (run once, on the first param row).
    if host != "127.0.0.1:3742":
        return
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
# 4. No dead auth symbol + auth module gone + no launch-store kwargs
# ---------------------------------------------------------------------------

_FORBIDDEN_HANDLER_SYMBOLS = [
    "LaunchTokenStore",
    "build_session_cookie",
    "ensure_token",
    "validate",
    "SESSION_COOKIE_NAME",
    "_consume_launch_token",
]


def test_no_dead_auth_surface() -> None:
    for symbol in _FORBIDDEN_HANDLER_SYMBOLS:
        assert not hasattr(handler_module, symbol), (
            f"handler module still exposes dead auth symbol {symbol!r} — "
            "panel auth was removed by operator decision 2026-06-11"
        )

    with pytest.raises(ModuleNotFoundError):
        import dadaia_workspace.features.panel.auth  # type: ignore[import-not-found]  # noqa: F401

    stubs = _make_all_stubs()
    with pytest.raises(TypeError):
        make_handler_class(stubs, launch_token_store=object())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        make_handler_class(stubs, loopback_bypass=True)  # type: ignore[call-arg]
