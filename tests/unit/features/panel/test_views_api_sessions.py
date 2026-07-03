"""Unit tests for GET /api/sessions — the server-side aggregate (v0.1.52 FR1).

The endpoint no longer returns a session *list*: it returns a single aggregate
cost-summary envelope built server-side by ``TelemetryService.aggregate_sessions``.
The per-session detail view (``render_api_session_detail``) was DELETED.

Aggregate envelope (SPEC §FR1):
    {
        "runtime":         str,
        "total_sessions":  int,
        "active_sessions": int,
        "total_cost_usd":  float | null,
        "cost_known":      bool,
        "total_messages":  int,
        "top_agent":       {"name": str, "session_count": int} | null,
        "generated_at":    str,           # ISO-8601
    }

Security notes (OWASP A03, A06):
- No content fields leak through the envelope.
- Error bodies are generic; no user input is reflected verbatim.
"""

from __future__ import annotations

import io
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views import api_sessions as api_module
from dadaia_workspace.features.panel.views.api_sessions import render_api_sessions
from dadaia_workspace.features.telemetry.aggregator.runtimes import ADAPTER_REGISTRY

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeServerRegistryService:
    def list_entries(self, project: Any = None, include_stale: bool = True) -> list[Any]:
        return []


class _FakeSpecContextService:
    def list_all(self) -> list[Any]:
        return []


def _make_service(telemetry_stub: Any = None) -> PanelService:
    return PanelService(
        registry=_FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=_FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
        telemetry=telemetry_stub,
        adapter_registry=dict(ADAPTER_REGISTRY),
    )


def _aggregate(
    runtime: str,
    *,
    total_sessions: int,
    active_sessions: int,
    total_cost_usd: float | None,
    cost_known: bool,
    total_messages: int,
    top_agent: SimpleNamespace | None,
    generated_at: str = "2026-05-19T10:00:00Z",
) -> SimpleNamespace:
    """Duck-typed SessionAggregate stand-in (the view reads attributes only)."""
    return SimpleNamespace(
        runtime=runtime,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        total_cost_usd=total_cost_usd,
        cost_known=cost_known,
        total_messages=total_messages,
        top_agent=top_agent,
        generated_at=generated_at,
    )


_AGG_CLAUDE = _aggregate(
    "claude",
    total_sessions=5,
    active_sessions=2,
    total_cost_usd=0.42,
    cost_known=True,
    total_messages=87,
    top_agent=SimpleNamespace(name="software-engineer", session_count=3),
)

_AGG_CODEX = _aggregate(
    "codex",
    total_sessions=4,
    active_sessions=1,
    total_cost_usd=None,
    cost_known=False,
    total_messages=30,
    top_agent=SimpleNamespace(name="operator", session_count=4),
)


class _FakeTelemetry:
    """Returns a canned SessionAggregate per runtime and records the call."""

    def __init__(self, aggregate: SimpleNamespace | None = None) -> None:
        self._override = aggregate
        self._by_runtime = {"claude": _AGG_CLAUDE, "codex": _AGG_CODEX}
        self.last_kwargs: dict[str, Any] = {}

    def aggregate_sessions(self, runtime: str) -> SimpleNamespace:
        self.last_kwargs = {"runtime": runtime}
        if self._override is not None:
            return self._override
        return self._by_runtime.get(
            runtime,
            _aggregate(
                runtime,
                total_sessions=0,
                active_sessions=0,
                total_cost_usd=None,
                cost_known=False,
                total_messages=0,
                top_agent=None,
            ),
        )


class _RaisingTelemetry:
    def aggregate_sessions(self, **_kw: Any) -> SimpleNamespace:
        raise RuntimeError("db unavailable")


# ---------------------------------------------------------------------------
# Handler-level access (no credential; Host guard only)
# ---------------------------------------------------------------------------


def _build_minimal_handler(telemetry: Any) -> type[BaseHTTPRequestHandler]:
    service = _make_service(telemetry_stub=telemetry)
    stub_views: dict[str, Any] = {
        "index": lambda **kw: (200, "text/html; charset=utf-8", b"<html>ok</html>"),
        "api_servers": lambda **kw: (200, "application/json", b"{}"),
        "api_contexts": lambda **kw: (200, "application/json", b"{}"),
        "api_workflows": lambda **kw: (200, "application/json", b'{"workflows":[]}'),
        "memory": lambda **kw: (200, "text/html; charset=utf-8", b"ok"),
        "memory_view": lambda **kw: (200, "text/html; charset=utf-8", b"ok"),
        "static": lambda **kw: (200, "text/plain; charset=utf-8", b"ok"),
        "api_sessions": render_api_sessions(service),
    }
    return make_handler_class(stub_views, telemetry=telemetry)


class _FakeSocket:
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
    path: str,
    *,
    host: str = "localhost",
) -> tuple[int, bytes]:
    raw_request = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n").encode()
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = fake_sock._wfile.getvalue()
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


class TestSessionRouteAccess:
    def test_sessions_serves_without_credential(self) -> None:
        """GET /api/sessions serves 200 with NO credential (telemetry present)."""
        handler = _build_minimal_handler(_FakeTelemetry())
        status, _ = _dispatch(handler, "/api/sessions?runtime=claude")
        assert status == 200

    def test_sessions_foreign_host_is_403(self) -> None:
        """A foreign Host on /api/sessions ⇒ 403 (DNS-rebinding guard)."""
        handler = _build_minimal_handler(_FakeTelemetry())
        status, body = _dispatch(handler, "/api/sessions", host="evil.example.com")
        assert status == 403
        assert b"forbidden host" in body


# ---------------------------------------------------------------------------
# 503 when telemetry unavailable
# ---------------------------------------------------------------------------


class TestTelemetryUnavailable:
    def test_503_when_no_telemetry(self) -> None:
        service = _make_service(telemetry_stub=None)
        status, _content_type, body = render_api_sessions(service)()
        assert status == 503
        assert "error" in json.loads(body)

    def test_503_when_telemetry_raises(self) -> None:
        service = _make_service(telemetry_stub=_RaisingTelemetry())
        status, _content_type, _body = render_api_sessions(service)(qs={})
        assert status == 503


# ---------------------------------------------------------------------------
# Aggregate envelope
# ---------------------------------------------------------------------------


class TestAggregateEnvelope:
    def test_returns_200_json(self) -> None:
        service = _make_service(telemetry_stub=_FakeTelemetry())
        status, content_type, _body = render_api_sessions(service)(qs={"runtime": ["claude"]})
        assert status == 200
        assert content_type == "application/json; charset=utf-8"

    def test_envelope_is_aggregate_with_no_sessions_array(self) -> None:
        service = _make_service(telemetry_stub=_FakeTelemetry())
        _, _, body = render_api_sessions(service)(qs={"runtime": ["claude"]})
        data = json.loads(body)
        assert set(data.keys()) == {
            "runtime",
            "total_sessions",
            "active_sessions",
            "total_cost_usd",
            "cost_known",
            "total_messages",
            "top_agent",
            "generated_at",
        }
        assert "sessions" not in data

    def test_aggregate_values_passthrough(self) -> None:
        service = _make_service(telemetry_stub=_FakeTelemetry())
        _, _, body = render_api_sessions(service)(qs={"runtime": ["claude"]})
        data = json.loads(body)
        assert data["runtime"] == "claude"
        assert data["total_sessions"] == 5
        assert data["active_sessions"] == 2
        assert data["total_cost_usd"] == 0.42
        assert data["cost_known"] is True
        assert data["total_messages"] == 87
        assert data["generated_at"] == "2026-05-19T10:00:00Z"

    def test_top_agent_shape(self) -> None:
        service = _make_service(telemetry_stub=_FakeTelemetry())
        _, _, body = render_api_sessions(service)(qs={"runtime": ["claude"]})
        data = json.loads(body)
        assert data["top_agent"] == {"name": "software-engineer", "session_count": 3}

    def test_top_agent_null_passthrough(self) -> None:
        agg = _aggregate(
            "claude",
            total_sessions=0,
            active_sessions=0,
            total_cost_usd=None,
            cost_known=False,
            total_messages=0,
            top_agent=None,
        )
        service = _make_service(telemetry_stub=_FakeTelemetry(aggregate=agg))
        _, _, body = render_api_sessions(service)(qs={"runtime": ["claude"]})
        data = json.loads(body)
        assert data["top_agent"] is None

    def test_codex_cost_fields_null_and_unknown(self) -> None:
        service = _make_service(telemetry_stub=_FakeTelemetry())
        _, _, body = render_api_sessions(service)(qs={"runtime": ["codex"]})
        data = json.loads(body)
        assert data["runtime"] == "codex"
        assert data["total_cost_usd"] is None
        assert data["cost_known"] is False

    def test_default_runtime_is_claude(self) -> None:
        tel = _FakeTelemetry()
        service = _make_service(telemetry_stub=tel)
        render_api_sessions(service)(qs={})
        assert tel.last_kwargs["runtime"] == "claude"

    def test_runtime_param_forwarded(self) -> None:
        tel = _FakeTelemetry()
        service = _make_service(telemetry_stub=tel)
        render_api_sessions(service)(qs={"runtime": ["codex"]})
        assert tel.last_kwargs["runtime"] == "codex"


# ---------------------------------------------------------------------------
# Detail view is gone
# ---------------------------------------------------------------------------


def test_session_detail_view_removed() -> None:
    """render_api_session_detail must no longer exist in the api view module."""
    assert not hasattr(api_module, "render_api_session_detail")
