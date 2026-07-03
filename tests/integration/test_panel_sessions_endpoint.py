"""Integration tests for GET /api/sessions — the server-side aggregate (v0.1.52 FR1).

Uses the deterministic seeded SQLite fixture at
tests/fixtures/telemetry/sessions_seeded.sqlite (created by _seed_sessions.py).

Spins up a ThreadingHTTPServer on port 0 with the real TelemetryAggregator wired
against the fixture and exercises the aggregate envelope end-to-end:
  - claude aggregate figures (sessions / active / messages / cost)
  - codex aggregate (cost forced null + cost_known false)
  - default runtime = claude
  - the DELETED detail route /api/sessions/<runtime>/<id> ⇒ standard 404

Fixture facts (see _seed_sessions.py):
  claude: 3 sessions — 1 active, 1 idle(open), 1 ended(closed); 3+2+2 = 7 events,
          all fully cost-known; cost_sum micro = 178000 + 84000 + 43000 = 305000.
  codex:  2 sessions — 0 active; 2+1 = 3 events, all cost NULL; agent_name None.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

from dadaia_workspace.features.telemetry.aggregator.queries import TelemetryAggregator
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

_FIXTURE_DB = (
    pathlib.Path(__file__).parents[1] / "fixtures" / "telemetry" / "sessions_seeded.sqlite"
)

_CLAUDE_SESSION_ID = "claude-session-aaa111bbb222ccc3"

# Expected claude aggregate (fixture-derived).
_CLAUDE_TOTAL_SESSIONS = 3
_CLAUDE_ACTIVE_SESSIONS = 1
_CLAUDE_TOTAL_MESSAGES = 7
_CLAUDE_TOTAL_COST_USD = (178000 + 84000 + 43000) / 1_000_000  # 0.305

# Expected codex aggregate (fixture-derived).
_CODEX_TOTAL_SESSIONS = 2
_CODEX_TOTAL_MESSAGES = 3


# ---------------------------------------------------------------------------
# Minimal DAO / spec-context stubs for TelemetryAggregator
# ---------------------------------------------------------------------------


class _FakeSpecContextService:
    def list_all(self) -> list[Any]:
        return []


class _NoPricingModule:
    PRICING_TABLE: dict[str, Any] = {}

    def pricing_age_days(self, models: list[str], when: Any = None) -> None:
        return None

    def compute_cost(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _FixtureTelemetry:
    """Wraps TelemetryAggregator over the seeded fixture DB.

    Implements the minimal interface render_api_sessions needs: aggregate_sessions().
    """

    def __init__(self, db_path: pathlib.Path) -> None:
        # check_same_thread=False because ThreadingHTTPServer dispatches requests on
        # worker threads. The fixture DB is read-only in tests.
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys=ON")
        dao = TelemetryDao(self._conn)
        self._aggregator = TelemetryAggregator(
            dao=dao,
            spec_context_service=_FakeSpecContextService(),
            pricing_module=_NoPricingModule(),
            workspace_root=None,
        )

    def aggregate_sessions(self, runtime: str) -> Any:
        return self._aggregator.aggregate_sessions(runtime=runtime)

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# Server fixture
# ---------------------------------------------------------------------------


def _build_server(token: str, telemetry: _FixtureTelemetry) -> ThreadingHTTPServer:
    from dadaia_workspace.features.panel.handler import make_handler_class
    from dadaia_workspace.features.panel.service import PanelService
    from dadaia_workspace.features.panel.views.api import render_api_sessions

    class _FakeRegistry:
        def list_entries(self, project: Any = None, include_stale: bool = True) -> list[Any]:
            return []

    class _FakeSCS:
        def list_all(self) -> list[Any]:
            return []

    service = PanelService(
        registry=_FakeRegistry(),  # type: ignore[arg-type]
        spec_context=_FakeSCS(),  # type: ignore[arg-type]
        workspace_root=pathlib.Path("/workspace"),
        telemetry=telemetry,
    )

    stub_views: dict[str, Any] = {
        "index": lambda **kw: (200, "text/html; charset=utf-8", b"<html>ok</html>"),
        "api_panel_status": lambda **kw: (200, "application/json", b"{}"),
        "api_contexts": lambda **kw: (200, "application/json", b"{}"),
        "api_workflows": lambda **kw: (
            200,
            "application/json; charset=utf-8",
            b'{"generated_at":"2026-01-01T00:00:00+00:00","source_hint":".dadaia/agentic/workflows/","workflows":[]}',
        ),
        "memory": lambda **kw: (200, "text/html; charset=utf-8", b"ok"),
        "memory_view": lambda **kw: (200, "text/html; charset=utf-8", b"ok"),
        "static": lambda **kw: (200, "text/plain; charset=utf-8", b"ok"),
        "api_sessions": render_api_sessions(service),
    }

    HandlerClass = make_handler_class(stub_views, token=token, telemetry=telemetry)
    return ThreadingHTTPServer(("127.0.0.1", 0), HandlerClass)


@pytest.fixture(scope="module")
def sessions_server() -> Any:
    if not _FIXTURE_DB.exists():
        pytest.fail(
            f"Fixture database not found: {_FIXTURE_DB}\n"
            "Run: .dadaia/.venv/bin/python tests/fixtures/telemetry/_seed_sessions.py"
        )

    tel = _FixtureTelemetry(_FIXTURE_DB)
    test_token = "integration-test-token-r5b4"

    server = _build_server(test_token, tel)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
    thread.start()

    yield base_url, test_token, tel

    server.shutdown()
    tel.close()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get(url: str, token: str | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310 — loopback test server
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


# ---------------------------------------------------------------------------
# No-auth contract
# ---------------------------------------------------------------------------


class TestSessionsAuth:
    def test_sessions_200_without_token(self, sessions_server: Any) -> None:
        base, _token, _ = sessions_server
        status, _ = _get(f"{base}/api/sessions")
        assert status == 200

    def test_stray_auth_header_ignored(self, sessions_server: Any) -> None:
        base, _token, _ = sessions_server
        status, _ = _get(f"{base}/api/sessions", token="wrong-token")
        assert status == 200


# ---------------------------------------------------------------------------
# Claude aggregate
# ---------------------------------------------------------------------------


class TestClaudeAggregate:
    def test_envelope_keys(self, sessions_server: Any) -> None:
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
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

    def test_no_sessions_array(self, sessions_server: Any) -> None:
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
        assert "sessions" not in json.loads(body)

    def test_claude_aggregate_values(self, sessions_server: Any) -> None:
        base, token, _ = sessions_server
        status, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
        assert status == 200
        data = json.loads(body)
        assert data["runtime"] == "claude"
        assert data["total_sessions"] == _CLAUDE_TOTAL_SESSIONS
        assert data["active_sessions"] == _CLAUDE_ACTIVE_SESSIONS
        assert data["total_messages"] == _CLAUDE_TOTAL_MESSAGES
        assert data["cost_known"] is True
        assert data["total_cost_usd"] == pytest.approx(_CLAUDE_TOTAL_COST_USD)

    def test_claude_top_agent(self, sessions_server: Any) -> None:
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
        data = json.loads(body)
        assert data["top_agent"] is not None
        assert data["top_agent"]["session_count"] == 1


# ---------------------------------------------------------------------------
# Codex aggregate
# ---------------------------------------------------------------------------


class TestCodexAggregate:
    def test_codex_cost_null_and_unknown(self, sessions_server: Any) -> None:
        base, token, _ = sessions_server
        status, body = _get(f"{base}/api/sessions?runtime=codex", token=token)
        assert status == 200
        data = json.loads(body)
        assert data["runtime"] == "codex"
        assert data["total_cost_usd"] is None
        assert data["cost_known"] is False

    def test_codex_counts(self, sessions_server: Any) -> None:
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=codex", token=token)
        data = json.loads(body)
        assert data["total_sessions"] == _CODEX_TOTAL_SESSIONS
        assert data["active_sessions"] == 0
        assert data["total_messages"] == _CODEX_TOTAL_MESSAGES

    def test_codex_top_agent_is_operator(self, sessions_server: Any) -> None:
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=codex", token=token)
        data = json.loads(body)
        assert data["top_agent"] == {"name": "operator", "session_count": 2}


# ---------------------------------------------------------------------------
# Default runtime
# ---------------------------------------------------------------------------


class TestDefaultRuntime:
    def test_default_runtime_is_claude(self, sessions_server: Any) -> None:
        base, token, _ = sessions_server
        status, body = _get(f"{base}/api/sessions", token=token)
        assert status == 200
        data = json.loads(body)
        assert data["runtime"] == "claude"
        assert data["total_sessions"] == _CLAUDE_TOTAL_SESSIONS


# ---------------------------------------------------------------------------
# Deleted detail route
# ---------------------------------------------------------------------------


class TestDeletedDetailRoute:
    def test_detail_route_returns_standard_404(self, sessions_server: Any) -> None:
        """GET /api/sessions/<runtime>/<id> is no longer a route ⇒ standard 404."""
        base, token, _ = sessions_server
        status, body = _get(
            f"{base}/api/sessions/claude/{_CLAUDE_SESSION_ID}",
            token=token,
        )
        assert status == 404
        assert b"Route not found" in body

    def test_detail_route_unknown_id_also_404(self, sessions_server: Any) -> None:
        base, token, _ = sessions_server
        status, _ = _get(f"{base}/api/sessions/claude/nonexistent-id", token=token)
        assert status == 404
