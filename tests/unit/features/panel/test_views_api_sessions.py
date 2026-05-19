"""Unit tests for panel-r5-v1 FR3: /api/sessions and /api/sessions/<runtime>/<session_id>.

Coverage per TASKS.md PR5-B3:
- envelope shape on success (list + detail)
- auth-missing → 401 (via handler dispatch with a fake socket)
- telemetry-unavailable → 503
- successful list with mocked aggregator (runtime filter, project filter, limit)
- detail hit (200 with event_timestamps)
- detail miss → 404

Security notes (OWASP A03, A06):
- No content fields leak through the envelope.
- 404 message is generic: "Session not found." only.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api import (
    render_api_session_detail,
    render_api_sessions,
)
from dadaia_workspace.features.telemetry.aggregator.models import (
    SessionDetail,
    SessionListResult,
    SessionRow,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeServerRegistryService:
    def list_entries(self, project=None, include_stale=True):
        return []


class _FakeSpecContextService:
    def list_all(self):
        return []


def _make_service(telemetry_stub: Any = None) -> PanelService:
    svc = PanelService(
        registry=_FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=_FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
        telemetry=telemetry_stub,
    )
    return svc


# ---------------------------------------------------------------------------
# Session fixtures
# ---------------------------------------------------------------------------

_SESSION_ROW_CLAUDE = SessionRow(
    session_id="aaaa1111bbbb2222cccc3333dddd4444",
    runtime="claude",
    project="dadaia-workspace",
    cwd="/home/user/workspace/dadaia",
    model="claude-sonnet-4-6",
    started_at="2026-05-19T08:00:00Z",
    last_activity_at="2026-05-19T09:30:00Z",
    message_count=12,
    context_size_tokens=45000,
    cumulative_cost_usd=0.15,
    cost_known=True,
    status="idle",
    agent_name="software-engineer",
    ai_title="Panel r5 Phase B",
)

_SESSION_ROW_CODEX = SessionRow(
    session_id="eeee5555ffff6666aaaa7777bbbb8888",
    runtime="codex",
    project="dadaia-workspace",
    cwd="/home/user/workspace/dadaia",
    model="gpt-4o",
    started_at="2026-05-19T07:00:00Z",
    last_activity_at="2026-05-19T07:45:00Z",
    message_count=5,
    context_size_tokens=12000,
    cumulative_cost_usd=None,
    cost_known=False,
    status="ended",
    agent_name=None,
    ai_title=None,
)

_SESSION_DETAIL_CLAUDE = SessionDetail(
    session_id="aaaa1111bbbb2222cccc3333dddd4444",
    runtime="claude",
    project="dadaia-workspace",
    cwd="/home/user/workspace/dadaia",
    model="claude-sonnet-4-6",
    started_at="2026-05-19T08:00:00Z",
    last_activity_at="2026-05-19T09:30:00Z",
    message_count=12,
    context_size_tokens=45000,
    cumulative_cost_usd=0.15,
    cost_known=True,
    status="idle",
    agent_name="software-engineer",
    ai_title="Panel r5 Phase B",
    event_timestamps=(
        "2026-05-19T08:01:00Z",
        "2026-05-19T08:15:00Z",
        "2026-05-19T09:30:00Z",
    ),
)


# ---------------------------------------------------------------------------
# Stub telemetry services
# ---------------------------------------------------------------------------


class _FakeTelemetry:
    """Returns canned sessions results."""

    def __init__(
        self,
        sessions: list[SessionRow] | None = None,
        detail: SessionDetail | None = None,
    ) -> None:
        self._sessions = sessions or [_SESSION_ROW_CLAUDE]
        self._detail = detail
        self.last_list_kwargs: dict[str, Any] = {}
        self.last_get_kwargs: dict[str, Any] = {}

    def list_sessions(
        self,
        runtime: str,
        project: str | None = None,
        limit: int | None = None,
    ) -> SessionListResult:
        self.last_list_kwargs = {"runtime": runtime, "project": project, "limit": limit}
        rows = [r for r in self._sessions if r.runtime == runtime]
        if project is not None:
            rows = [r for r in rows if r.project == project]
        if limit is not None:
            rows = rows[:limit]
        return SessionListResult(
            sessions=rows,
            runtime=runtime,
            project=project,
            limit=limit,
            generated_at="2026-05-19T10:00:00Z",
            total_count=len(rows),
        )

    def get_session(self, runtime: str, session_id: str) -> SessionDetail | None:
        self.last_get_kwargs = {"runtime": runtime, "session_id": session_id}
        if (
            self._detail
            and self._detail.session_id == session_id
            and self._detail.runtime == runtime
        ):
            return self._detail
        return None


class _RaisingTelemetry:
    """Simulates a telemetry service that always raises."""

    def list_sessions(self, **_kw: Any) -> SessionListResult:
        raise RuntimeError("db unavailable")

    def get_session(self, **_kw: Any) -> SessionDetail | None:
        raise RuntimeError("db unavailable")


# ---------------------------------------------------------------------------
# Handler-level auth tests (401)
# ---------------------------------------------------------------------------

_EXPECTED_TOKEN = "panel-unit-test-token-xyz"


def _build_minimal_handler(token: str, telemetry: Any) -> type[BaseHTTPRequestHandler]:
    """Build a minimal PanelHandler with sessions views injected."""
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
        "api_session_detail": render_api_session_detail(service),
    }
    return make_handler_class(stub_views, token=token, telemetry=telemetry)


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
    path: str,
    token: str | None = None,
) -> tuple[int, bytes]:
    """Drive a single GET request through handler_class for path."""
    auth_header = f"Authorization: Bearer {token}\r\n" if token else ""
    raw_request = (f"GET {path} HTTP/1.1\r\nHost: localhost\r\n{auth_header}\r\n").encode()
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = fake_sock._wfile.getvalue()
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


# ---------------------------------------------------------------------------
# Tests — auth (401 via handler)
# ---------------------------------------------------------------------------


class TestAuth:
    def test_sessions_list_401_without_token(self) -> None:
        """GET /api/sessions without Authorization header → 401."""
        handler = _build_minimal_handler(_EXPECTED_TOKEN, _FakeTelemetry())
        status, body = _dispatch(handler, "/api/sessions")
        assert status == 401

    def test_sessions_detail_401_without_token(self) -> None:
        """GET /api/sessions/<runtime>/<id> without Authorization header → 401."""
        handler = _build_minimal_handler(_EXPECTED_TOKEN, _FakeTelemetry())
        status, body = _dispatch(
            handler,
            f"/api/sessions/claude/{_SESSION_ROW_CLAUDE.session_id}",
        )
        assert status == 401

    def test_sessions_list_401_wrong_token(self) -> None:
        """GET /api/sessions with wrong token → 401."""
        handler = _build_minimal_handler(_EXPECTED_TOKEN, _FakeTelemetry())
        status, body = _dispatch(handler, "/api/sessions", token="wrong-token")
        assert status == 401

    def test_sessions_list_200_valid_token(self) -> None:
        """GET /api/sessions with valid token → 200."""
        handler = _build_minimal_handler(_EXPECTED_TOKEN, _FakeTelemetry())
        status, body = _dispatch(handler, "/api/sessions?runtime=claude", token=_EXPECTED_TOKEN)
        assert status == 200


# ---------------------------------------------------------------------------
# Tests — 503 when telemetry unavailable
# ---------------------------------------------------------------------------


class TestTelemetryUnavailable:
    def test_list_sessions_503_when_no_telemetry(self) -> None:
        """render_api_sessions with telemetry=None → 503."""
        service = _make_service(telemetry_stub=None)
        view = render_api_sessions(service)
        status, content_type, body = view()
        assert status == 503
        data = json.loads(body)
        assert "error" in data

    def test_list_sessions_503_when_telemetry_raises(self) -> None:
        """render_api_sessions when service.telemetry raises → 503."""
        service = _make_service(telemetry_stub=_RaisingTelemetry())
        view = render_api_sessions(service)
        status, content_type, body = view(qs={})
        assert status == 503

    def test_detail_503_when_no_telemetry(self) -> None:
        """render_api_session_detail with telemetry=None → 503."""
        service = _make_service(telemetry_stub=None)
        view = render_api_session_detail(service)
        status, content_type, body = view(runtime="claude", session_id="doesnotmatter")
        assert status == 503
        data = json.loads(body)
        assert "error" in data

    def test_detail_503_when_telemetry_raises(self) -> None:
        """render_api_session_detail when service.telemetry raises → 503."""
        service = _make_service(telemetry_stub=_RaisingTelemetry())
        view = render_api_session_detail(service)
        status, content_type, body = view(runtime="claude", session_id="doesnotmatter")
        assert status == 503


# ---------------------------------------------------------------------------
# Tests — successful list
# ---------------------------------------------------------------------------


class TestSessionsList:
    def test_list_returns_200(self) -> None:
        """render_api_sessions with working telemetry → 200."""
        service = _make_service(telemetry_stub=_FakeTelemetry())
        view = render_api_sessions(service)
        status, content_type, body = view(qs={"runtime": ["claude"]})
        assert status == 200
        assert "application/json" in content_type

    def test_list_envelope_shape(self) -> None:
        """Response envelope has required top-level keys."""
        service = _make_service(telemetry_stub=_FakeTelemetry())
        view = render_api_sessions(service)
        _, _, body = view(qs={"runtime": ["claude"]})
        data = json.loads(body)
        required = {"generated_at", "runtime", "project", "limit", "total_count", "sessions"}
        missing = required - set(data.keys())
        assert not missing, f"Missing envelope keys: {missing}"

    def test_list_session_row_keys(self) -> None:
        """Each session item in the list has all required SessionRow keys."""
        service = _make_service(telemetry_stub=_FakeTelemetry())
        view = render_api_sessions(service)
        _, _, body = view(qs={"runtime": ["claude"]})
        data = json.loads(body)
        assert len(data["sessions"]) >= 1
        row = data["sessions"][0]
        required_keys = {
            "session_id",
            "runtime",
            "project",
            "cwd",
            "model",
            "started_at",
            "last_activity_at",
            "message_count",
            "context_size_tokens",
            "cumulative_cost_usd",
            "cost_known",
            "status",
            "agent_name",
            "ai_title",
        }
        missing = required_keys - set(row.keys())
        assert not missing, f"Missing session row keys: {missing}"

    def test_list_default_runtime_is_claude(self) -> None:
        """When qs has no 'runtime' key, default is 'claude'."""
        tel = _FakeTelemetry()
        service = _make_service(telemetry_stub=tel)
        view = render_api_sessions(service)
        view(qs={})
        assert tel.last_list_kwargs["runtime"] == "claude"

    def test_list_runtime_filter_applied(self) -> None:
        """Only sessions matching the requested runtime are returned."""
        tel = _FakeTelemetry(sessions=[_SESSION_ROW_CLAUDE, _SESSION_ROW_CODEX])
        service = _make_service(telemetry_stub=tel)
        view = render_api_sessions(service)
        _, _, body = view(qs={"runtime": ["codex"]})
        data = json.loads(body)
        for row in data["sessions"]:
            assert row["runtime"] == "codex", "Non-codex row returned for runtime=codex"

    def test_list_project_filter_forwarded(self) -> None:
        """Project filter is forwarded to the aggregator."""
        tel = _FakeTelemetry()
        service = _make_service(telemetry_stub=tel)
        view = render_api_sessions(service)
        view(qs={"runtime": ["claude"], "project": ["my-project"]})
        assert tel.last_list_kwargs["project"] == "my-project"

    def test_list_limit_parsed_and_forwarded(self) -> None:
        """Limit is parsed as int and forwarded."""
        tel = _FakeTelemetry()
        service = _make_service(telemetry_stub=tel)
        view = render_api_sessions(service)
        view(qs={"runtime": ["claude"], "limit": ["5"]})
        assert tel.last_list_kwargs["limit"] == 5

    def test_list_limit_invalid_uses_none(self) -> None:
        """Non-integer limit falls back to None (no cap)."""
        tel = _FakeTelemetry()
        service = _make_service(telemetry_stub=tel)
        view = render_api_sessions(service)
        view(qs={"runtime": ["claude"], "limit": ["notanint"]})
        assert tel.last_list_kwargs["limit"] is None

    def test_list_codex_cost_is_none_via_adapter(self) -> None:
        """Codex rows have cumulative_cost_usd=None after adapter enrichment."""
        tel = _FakeTelemetry(sessions=[_SESSION_ROW_CODEX])
        service = _make_service(telemetry_stub=tel)
        view = render_api_sessions(service)
        _, _, body = view(qs={"runtime": ["codex"]})
        data = json.loads(body)
        for row in data["sessions"]:
            assert row["cumulative_cost_usd"] is None
            assert row["cost_known"] is False

    def test_list_content_type(self) -> None:
        """Content-Type is application/json; charset=utf-8."""
        service = _make_service(telemetry_stub=_FakeTelemetry())
        view = render_api_sessions(service)
        _, content_type, _ = view(qs={"runtime": ["claude"]})
        assert content_type == "application/json; charset=utf-8"


# ---------------------------------------------------------------------------
# Tests — session detail
# ---------------------------------------------------------------------------


class TestSessionDetail:
    def test_detail_hit_returns_200(self) -> None:
        """render_api_session_detail with valid runtime+session_id → 200."""
        tel = _FakeTelemetry(detail=_SESSION_DETAIL_CLAUDE)
        service = _make_service(telemetry_stub=tel)
        view = render_api_session_detail(service)
        status, content_type, body = view(
            runtime="claude",
            session_id=_SESSION_DETAIL_CLAUDE.session_id,
        )
        assert status == 200
        assert "application/json" in content_type

    def test_detail_hit_has_event_timestamps(self) -> None:
        """Detail response includes event_timestamps list."""
        tel = _FakeTelemetry(detail=_SESSION_DETAIL_CLAUDE)
        service = _make_service(telemetry_stub=tel)
        view = render_api_session_detail(service)
        _, _, body = view(
            runtime="claude",
            session_id=_SESSION_DETAIL_CLAUDE.session_id,
        )
        data = json.loads(body)
        assert "event_timestamps" in data
        assert isinstance(data["event_timestamps"], list)
        assert len(data["event_timestamps"]) == len(_SESSION_DETAIL_CLAUDE.event_timestamps)

    def test_detail_hit_shape(self) -> None:
        """Detail response has all SessionRow keys plus event_timestamps."""
        tel = _FakeTelemetry(detail=_SESSION_DETAIL_CLAUDE)
        service = _make_service(telemetry_stub=tel)
        view = render_api_session_detail(service)
        _, _, body = view(
            runtime="claude",
            session_id=_SESSION_DETAIL_CLAUDE.session_id,
        )
        data = json.loads(body)
        required = {
            "session_id",
            "runtime",
            "project",
            "cwd",
            "model",
            "started_at",
            "last_activity_at",
            "message_count",
            "context_size_tokens",
            "cumulative_cost_usd",
            "cost_known",
            "status",
            "agent_name",
            "ai_title",
            "event_timestamps",
        }
        missing = required - set(data.keys())
        assert not missing, f"Missing detail keys: {missing}"

    def test_detail_miss_returns_404(self) -> None:
        """render_api_session_detail when session not found → 404."""
        tel = _FakeTelemetry(detail=None)
        service = _make_service(telemetry_stub=tel)
        view = render_api_session_detail(service)
        status, content_type, body = view(
            runtime="claude",
            session_id="nonexistent-session-id",
        )
        assert status == 404
        data = json.loads(body)
        assert "error" in data
        assert data["error"] == "not_found"

    def test_detail_wrong_runtime_returns_404(self) -> None:
        """Querying a Claude session with runtime=codex → 404."""
        tel = _FakeTelemetry(detail=_SESSION_DETAIL_CLAUDE)
        service = _make_service(telemetry_stub=tel)
        view = render_api_session_detail(service)
        # The fake telemetry will return None because runtime != detail.runtime.
        status, _, body = view(
            runtime="codex",
            session_id=_SESSION_DETAIL_CLAUDE.session_id,
        )
        assert status == 404

    def test_detail_content_type(self) -> None:
        """Content-Type is application/json; charset=utf-8 on hit."""
        tel = _FakeTelemetry(detail=_SESSION_DETAIL_CLAUDE)
        service = _make_service(telemetry_stub=tel)
        view = render_api_session_detail(service)
        _, content_type, _ = view(
            runtime="claude",
            session_id=_SESSION_DETAIL_CLAUDE.session_id,
        )
        assert content_type == "application/json; charset=utf-8"
