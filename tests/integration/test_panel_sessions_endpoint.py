"""Integration tests for GET /api/sessions — the server-side aggregate (v0.1.52 FR1).

Uses the deterministic seeded SQLite fixture at
tests/fixtures/telemetry/sessions_seeded.sqlite (created by _seed_sessions.py).

Merged per plan-integration.md (12 -> 2): (1) claude aggregate (envelope keys, values,
top_agent, no sessions array, default runtime, no-auth); (2) codex aggregate (cost
null/unknown, counts, operator top-agent) + deleted detail route 404.

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
from tests.fakes import shared_connection_factory

_FIXTURE_DB = (
    pathlib.Path(__file__).parents[1] / "fixtures" / "telemetry" / "sessions_seeded.sqlite"
)

_CLAUDE_SESSION_ID = "claude-session-aaa111bbb222ccc3"

_CLAUDE_TOTAL_SESSIONS = 3
_CLAUDE_ACTIVE_SESSIONS = 1
_CLAUDE_TOTAL_MESSAGES = 7
_CLAUDE_TOTAL_COST_USD = (178000 + 84000 + 43000) / 1_000_000  # 0.305

_CODEX_TOTAL_SESSIONS = 2
_CODEX_TOTAL_MESSAGES = 3


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
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._aggregator = TelemetryAggregator(
            connection_factory=shared_connection_factory(self._conn),
            spec_context_service=_FakeSpecContextService(),
            pricing_module=_NoPricingModule(),
            workspace_root=None,
        )

    def aggregate_sessions(self, runtime: str) -> Any:
        return self._aggregator.aggregate_sessions(runtime=runtime)

    def close(self) -> None:
        self._conn.close()


def _build_server(token: str, telemetry: _FixtureTelemetry) -> ThreadingHTTPServer:
    from dadaia_workspace.features.panel.handler import make_handler_class
    from dadaia_workspace.features.panel.service import PanelService
    from dadaia_workspace.features.panel.views.api_sessions import render_api_sessions

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


def _get(url: str, token: str | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310 — loopback test server
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_claude_aggregate_envelope_no_auth_codex_aggregate_and_deleted_detail_route(
    sessions_server: Any,
) -> None:
    """Claude aggregate: envelope keys, values, top_agent, no sessions array, default
    runtime, no-auth (credential-less GET still 200). Plus codex aggregate (cost
    null/unknown, counts, operator top-agent) + deleted /api/sessions/<runtime>/<id>
    detail route -> standard 404 (same seeded-fixture server)."""
    base, token, _ = sessions_server

    status, body = _get(f"{base}/api/sessions")
    assert status == 200

    status, body = _get(f"{base}/api/sessions", token="wrong-token")
    assert status == 200

    status, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
    assert status == 200
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
    assert data["runtime"] == "claude"
    assert data["total_sessions"] == _CLAUDE_TOTAL_SESSIONS
    assert data["active_sessions"] == _CLAUDE_ACTIVE_SESSIONS
    assert data["total_messages"] == _CLAUDE_TOTAL_MESSAGES
    assert data["cost_known"] is True
    assert data["total_cost_usd"] == pytest.approx(_CLAUDE_TOTAL_COST_USD)
    assert data["top_agent"] is not None
    assert data["top_agent"]["session_count"] == 1

    # Default runtime (no ?runtime=) is also claude.
    status, body = _get(f"{base}/api/sessions", token=token)
    assert status == 200
    data = json.loads(body)
    assert data["runtime"] == "claude"
    assert data["total_sessions"] == _CLAUDE_TOTAL_SESSIONS

    # Codex aggregate (cost null/unknown, counts, operator top-agent).
    status, body = _get(f"{base}/api/sessions?runtime=codex", token=token)
    assert status == 200
    data = json.loads(body)
    assert data["runtime"] == "codex"
    assert data["total_cost_usd"] is None
    assert data["cost_known"] is False
    assert data["total_sessions"] == _CODEX_TOTAL_SESSIONS
    assert data["active_sessions"] == 0
    assert data["total_messages"] == _CODEX_TOTAL_MESSAGES
    assert data["top_agent"] == {"name": "operator", "session_count": 2}

    status, body = _get(f"{base}/api/sessions/claude/{_CLAUDE_SESSION_ID}", token=token)
    assert status == 404
    assert b"Route not found" in body

    status, _ = _get(f"{base}/api/sessions/claude/nonexistent-id", token=token)
    assert status == 404
