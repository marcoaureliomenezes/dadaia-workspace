"""Integration tests for /api/sessions and /api/sessions/<runtime>/<session_id>.

Panel-r5-v1 FR3 / PR5-B4.

Uses a deterministic seeded SQLite fixture at
tests/fixtures/telemetry/sessions_seeded.sqlite (created by _seed_sessions.py).

Spins up a ThreadingHTTPServer on port 0 with the real TelemetryAggregator
wired against the fixture.  Exercises:
  - Runtime filter: ?runtime=claude returns only Claude rows
  - Runtime filter: ?runtime=codex returns only Codex rows with
    cumulative_cost_usd=None and cost_known=False
  - Project filter: ?project=<slug> narrows to sessions in that project
  - Detail endpoint: returns full SessionDetail with event_timestamps
  - Detail miss: unknown session_id → 404
  - Auth: missing/wrong token → 401
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

from dadaia_workspace.features.telemetry.aggregator.models import (
    SessionDetail,
    SessionListResult,
)
from dadaia_workspace.features.telemetry.aggregator.queries import TelemetryAggregator
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

_FIXTURE_DB = (
    pathlib.Path(__file__).parents[1] / "fixtures" / "telemetry" / "sessions_seeded.sqlite"
)

# ---------------------------------------------------------------------------
# Minimal DAO / spec-context stubs for TelemetryAggregator
# ---------------------------------------------------------------------------


class _FakeSpecContextService:
    """Returns empty context list — sessions are 'unassigned' but still returned."""

    def list_all(self) -> list:
        return []


class _NoPricingModule:
    """Minimal pricing stub that returns zero cost age."""

    PRICING_TABLE: dict = {}

    def pricing_age_days(self, models: list, when: Any = None) -> None:
        return None

    def compute_cost(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _FixtureTelemetry:
    """Wraps TelemetryAggregator over the seeded fixture database.

    Implements the minimal interface needed by render_api_sessions /
    render_api_session_detail:  list_sessions() + get_session().
    """

    def __init__(self, db_path: pathlib.Path) -> None:
        # check_same_thread=False is needed because ThreadingHTTPServer dispatches
        # requests in worker threads different from the thread that opened the
        # connection. The fixture database is read-only in tests.
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        dao = TelemetryDao(self._conn)
        self._aggregator = TelemetryAggregator(
            dao=dao,
            spec_context_service=_FakeSpecContextService(),
            pricing_module=_NoPricingModule(),
            workspace_root=None,
        )

    def list_sessions(
        self,
        runtime: str,
        project: str | None = None,
        limit: int | None = None,
    ) -> SessionListResult:
        return self._aggregator.list_sessions(
            runtime=runtime,
            project=project,
            limit=limit,
        )

    def get_session(
        self,
        runtime: str,
        session_id: str,
    ) -> SessionDetail | None:
        return self._aggregator.get_session(
            runtime=runtime,
            session_id=session_id,
        )

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# Server fixture
# ---------------------------------------------------------------------------


def _build_server(token: str, telemetry: _FixtureTelemetry):
    """Build a ThreadingHTTPServer with the panel handler + sessions views."""
    from dadaia_workspace.features.panel.handler import make_handler_class
    from dadaia_workspace.features.panel.service import PanelService
    from dadaia_workspace.features.panel.views.api import (
        render_api_session_detail,
        render_api_sessions,
    )

    class _FakeRegistry:
        def list_entries(self, project=None, include_stale=True):
            return []

    class _FakeSCS:
        def list_all(self):
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
        "api_session_detail": render_api_session_detail(service),
    }

    HandlerClass = make_handler_class(stub_views, token=token, telemetry=telemetry)
    server = ThreadingHTTPServer(("127.0.0.1", 0), HandlerClass)
    return server


@pytest.fixture(scope="module")
def sessions_server():
    """Start panel with fixture telemetry; yield (base_url, token, telemetry)."""
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

    thread = threading.Thread(target=server.serve_forever, daemon=True)
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
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestSessionsAuth:
    def test_sessions_list_401_without_token(self, sessions_server) -> None:
        """GET /api/sessions without token → 401."""
        base, token, _ = sessions_server
        status, _ = _get(f"{base}/api/sessions")
        assert status == 401

    def test_sessions_list_401_wrong_token(self, sessions_server) -> None:
        """GET /api/sessions with wrong token → 401."""
        base, _, _ = sessions_server
        status, _ = _get(f"{base}/api/sessions", token="wrong-token")
        assert status == 401

    def test_sessions_detail_401_without_token(self, sessions_server) -> None:
        """GET /api/sessions/claude/<id> without token → 401."""
        base, token, _ = sessions_server
        status, _ = _get(f"{base}/api/sessions/claude/any-id")
        assert status == 401


# ---------------------------------------------------------------------------
# Runtime filter tests
# ---------------------------------------------------------------------------


class TestSessionsRuntimeFilter:
    def test_claude_filter_returns_claude_rows_only(self, sessions_server) -> None:
        """?runtime=claude returns only sessions with runtime='claude'."""
        base, token, _ = sessions_server
        status, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
        assert status == 200
        data = json.loads(body)
        assert "sessions" in data
        for row in data["sessions"]:
            assert row["runtime"] == "claude", (
                f"Non-claude row in runtime=claude response: {row['runtime']}"
            )

    def test_codex_filter_returns_codex_rows_only(self, sessions_server) -> None:
        """?runtime=codex returns only sessions with runtime='codex'."""
        base, token, _ = sessions_server
        status, body = _get(f"{base}/api/sessions?runtime=codex", token=token)
        assert status == 200
        data = json.loads(body)
        assert "sessions" in data
        for row in data["sessions"]:
            assert row["runtime"] == "codex", (
                f"Non-codex row in runtime=codex response: {row['runtime']}"
            )

    def test_claude_returns_at_least_3_sessions(self, sessions_server) -> None:
        """Fixture has ≥3 Claude sessions."""
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
        data = json.loads(body)
        assert len(data["sessions"]) >= 3, (
            f"Expected ≥3 Claude sessions, got {len(data['sessions'])}"
        )

    def test_codex_returns_at_least_2_sessions(self, sessions_server) -> None:
        """Fixture has ≥2 Codex sessions."""
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=codex", token=token)
        data = json.loads(body)
        assert len(data["sessions"]) >= 2, (
            f"Expected ≥2 Codex sessions, got {len(data['sessions'])}"
        )

    def test_codex_rows_have_null_cost(self, sessions_server) -> None:
        """All Codex rows must have cumulative_cost_usd=None and cost_known=False.

        Per SPEC FR3, FR6, NFR: Codex cost is not tracked; CodexRuntimeAdapter
        forces cumulative_cost_usd=None and cost_known=False.
        """
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=codex", token=token)
        data = json.loads(body)
        assert data["sessions"], "Expected Codex sessions but got empty list"
        for row in data["sessions"]:
            assert row["cumulative_cost_usd"] is None, (
                f"Codex row should have cumulative_cost_usd=None, got {row['cumulative_cost_usd']}"
            )
            assert row["cost_known"] is False, (
                f"Codex row should have cost_known=False, got {row['cost_known']}"
            )

    def test_default_runtime_is_claude(self, sessions_server) -> None:
        """GET /api/sessions with no ?runtime= param defaults to claude."""
        base, token, _ = sessions_server
        status, body = _get(f"{base}/api/sessions", token=token)
        assert status == 200
        data = json.loads(body)
        # All returned rows must be claude (default runtime = claude)
        for row in data["sessions"]:
            assert row["runtime"] == "claude"

    def test_codex_rows_have_null_cost_and_cost_known_false(self, sessions_server) -> None:
        """PR5-E4: every Codex row has cumulative_cost_usd=None and cost_known=False.

        Sourced from tests/fixtures/telemetry/sessions_seeded.sqlite Codex rows
        (≥2 rows per PR5-B4 requirement, verified in test_codex_returns_at_least_2_sessions).

        SPEC FR3, FR6, NFR: Codex cost tracking is not supported; the
        CodexRuntimeAdapter must force cumulative_cost_usd=None and cost_known=False
        regardless of any event-level data. This test asserts that invariant
        end-to-end: fixture DB → aggregator → HTTP response.
        """
        base, token, _ = sessions_server
        status, body = _get(f"{base}/api/sessions?runtime=codex", token=token)
        assert status == 200
        data = json.loads(body)
        codex_rows = data["sessions"]
        assert codex_rows, "Expected ≥1 Codex session in fixture (PR5-B4 placed ≥2)"
        for row in codex_rows:
            assert row["cumulative_cost_usd"] is None, (
                f"PR5-E4: Codex row {row['session_id']!r} must have "
                f"cumulative_cost_usd=None, got {row['cumulative_cost_usd']!r}"
            )
            assert row["cost_known"] is False, (
                f"PR5-E4: Codex row {row['session_id']!r} must have "
                f"cost_known=False, got {row['cost_known']!r}"
            )


# ---------------------------------------------------------------------------
# Project filter test
# ---------------------------------------------------------------------------


class TestSessionsProjectFilter:
    def test_project_filter_narrows_results(self, sessions_server) -> None:
        """?project=dadaia-workspace returns only sessions for that project."""
        base, token, _ = sessions_server
        _, body = _get(
            f"{base}/api/sessions?runtime=claude&project=dadaia-workspace",
            token=token,
        )
        data = json.loads(body)
        assert data["sessions"], "Expected sessions for dadaia-workspace"
        for row in data["sessions"]:
            assert row["project"] == "dadaia-workspace", (
                f"Wrong project in response: {row['project']}"
            )

    def test_project_filter_redacted-slug_games(self, sessions_server) -> None:
        """?project=redacted-slug returns only sessions for that project."""
        base, token, _ = sessions_server
        _, body = _get(
            f"{base}/api/sessions?runtime=claude&project=redacted-slug",
            token=token,
        )
        data = json.loads(body)
        assert data["sessions"], "Expected sessions for redacted-slug"
        for row in data["sessions"]:
            assert row["project"] == "redacted-slug"

    def test_unknown_project_returns_empty(self, sessions_server) -> None:
        """?project=nonexistent returns empty sessions list (not an error)."""
        base, token, _ = sessions_server
        status, body = _get(
            f"{base}/api/sessions?runtime=claude&project=nonexistent-project",
            token=token,
        )
        assert status == 200
        data = json.loads(body)
        assert data["sessions"] == []


# ---------------------------------------------------------------------------
# Detail endpoint tests
# ---------------------------------------------------------------------------

_CLAUDE_SESSION_ID = "claude-session-aaa111bbb222ccc3"
# First Codex session from tests/fixtures/telemetry/sessions_seeded.sqlite
# (PR5-B4 placed ≥2 Codex rows; verified by test_codex_returns_at_least_2_sessions)
_CODEX_SESSION_ID = "codex-session-jjj000kkk111lll2"


class TestSessionDetail:
    def test_detail_hit_returns_200(self, sessions_server) -> None:
        """GET /api/sessions/claude/<id> with valid id → 200."""
        base, token, _ = sessions_server
        status, body = _get(
            f"{base}/api/sessions/claude/{_CLAUDE_SESSION_ID}",
            token=token,
        )
        assert status == 200

    def test_detail_has_required_keys(self, sessions_server) -> None:
        """Detail response has all SessionRow keys plus event_timestamps."""
        base, token, _ = sessions_server
        _, body = _get(
            f"{base}/api/sessions/claude/{_CLAUDE_SESSION_ID}",
            token=token,
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

    def test_detail_event_timestamps_non_empty(self, sessions_server) -> None:
        """event_timestamps is a non-empty list of ISO strings."""
        base, token, _ = sessions_server
        _, body = _get(
            f"{base}/api/sessions/claude/{_CLAUDE_SESSION_ID}",
            token=token,
        )
        data = json.loads(body)
        assert isinstance(data["event_timestamps"], list)
        assert len(data["event_timestamps"]) > 0

    def test_detail_session_id_matches_request(self, sessions_server) -> None:
        """Detail response session_id matches requested session_id."""
        base, token, _ = sessions_server
        _, body = _get(
            f"{base}/api/sessions/claude/{_CLAUDE_SESSION_ID}",
            token=token,
        )
        data = json.loads(body)
        assert data["session_id"] == _CLAUDE_SESSION_ID

    def test_detail_context_size_tokens_non_zero(self, sessions_server) -> None:
        """context_size_tokens is non-trivially computed (> 0) for seeded events."""
        base, token, _ = sessions_server
        _, body = _get(
            f"{base}/api/sessions/claude/{_CLAUDE_SESSION_ID}",
            token=token,
        )
        data = json.loads(body)
        # Most recent event: tokens_input=12000 + cache_create=4000 + cache_read=22000 = 38000
        assert data["context_size_tokens"] > 0, (
            "context_size_tokens should be non-trivially computed from event rows"
        )

    def test_detail_miss_returns_404(self, sessions_server) -> None:
        """GET /api/sessions/claude/nonexistent → 404."""
        base, token, _ = sessions_server
        status, body = _get(
            f"{base}/api/sessions/claude/nonexistent-session-id-xyz",
            token=token,
        )
        assert status == 404
        data = json.loads(body)
        assert data.get("error") == "not_found"

    def test_detail_wrong_runtime_returns_404(self, sessions_server) -> None:
        """Querying a Claude session_id with runtime=codex → 404."""
        base, token, _ = sessions_server
        status, _ = _get(
            f"{base}/api/sessions/codex/{_CLAUDE_SESSION_ID}",
            token=token,
        )
        assert status == 404


# ---------------------------------------------------------------------------
# PR5-E4 — Codex detail endpoint assertions
# ---------------------------------------------------------------------------


class TestCodexDetailEndpoint:
    """PR5-E4: /api/sessions/codex/<id> must return cumulative_cost_usd=None
    and cost_known=False.

    Picks one Codex session_id from the seeded fixture and asserts the
    cost contract end-to-end: fixture DB → aggregator → HTTP response.
    """

    def test_codex_detail_endpoint_returns_none_cost(self, sessions_server) -> None:
        """PR5-E4: GET /api/sessions/codex/<id> → cumulative_cost_usd is None
        and cost_known is False.

        SPEC FR3, FR6: cost tracking is disabled for Codex.  The
        CodexRuntimeAdapter must set both fields to None/False even on the
        single-session detail path, not only on the list path.
        """
        base, token, _ = sessions_server
        status, body = _get(
            f"{base}/api/sessions/codex/{_CODEX_SESSION_ID}",
            token=token,
        )
        assert status == 200, f"Expected 200 for Codex detail {_CODEX_SESSION_ID!r}, got {status}"
        data = json.loads(body)

        # Core PR5-E4 assertions
        assert data["cumulative_cost_usd"] is None, (
            f"PR5-E4: Codex detail must have cumulative_cost_usd=None, "
            f"got {data['cumulative_cost_usd']!r}"
        )
        assert data["cost_known"] is False, (
            f"PR5-E4: Codex detail must have cost_known=False, got {data['cost_known']!r}"
        )

    def test_codex_detail_has_all_required_keys(self, sessions_server) -> None:
        """GET /api/sessions/codex/<id> response carries all SessionDetail keys."""
        base, token, _ = sessions_server
        _, body = _get(
            f"{base}/api/sessions/codex/{_CODEX_SESSION_ID}",
            token=token,
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
        assert not missing, f"Missing Codex detail keys: {missing}"

    def test_codex_detail_runtime_is_codex(self, sessions_server) -> None:
        """GET /api/sessions/codex/<id> returns runtime='codex'."""
        base, token, _ = sessions_server
        _, body = _get(
            f"{base}/api/sessions/codex/{_CODEX_SESSION_ID}",
            token=token,
        )
        data = json.loads(body)
        assert data["runtime"] == "codex", f"Expected runtime='codex', got {data['runtime']!r}"

    def test_codex_detail_session_id_matches(self, sessions_server) -> None:
        """Detail response session_id matches the requested Codex session_id."""
        base, token, _ = sessions_server
        _, body = _get(
            f"{base}/api/sessions/codex/{_CODEX_SESSION_ID}",
            token=token,
        )
        data = json.loads(body)
        assert data["session_id"] == _CODEX_SESSION_ID


# ---------------------------------------------------------------------------
# Envelope shape tests
# ---------------------------------------------------------------------------


class TestSessionsEnvelope:
    def test_envelope_top_level_keys(self, sessions_server) -> None:
        """List response has all required top-level envelope keys."""
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
        data = json.loads(body)
        required = {"generated_at", "runtime", "project", "limit", "total_count", "sessions"}
        missing = required - set(data.keys())
        assert not missing, f"Missing envelope keys: {missing}"

    def test_session_row_has_required_keys(self, sessions_server) -> None:
        """Each session row in the list has all required SessionRow keys."""
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
        data = json.loads(body)
        assert data["sessions"]
        row = data["sessions"][0]
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
        }
        missing = required - set(row.keys())
        assert not missing, f"Missing session row keys: {missing}"

    def test_total_count_reflects_all_matches(self, sessions_server) -> None:
        """total_count reports unfiltered matching row count."""
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=claude", token=token)
        data = json.loads(body)
        assert data["total_count"] >= len(data["sessions"])
        assert data["total_count"] >= 3  # fixture has ≥3 Claude sessions

    def test_limit_respected(self, sessions_server) -> None:
        """?limit=1 returns at most 1 session."""
        base, token, _ = sessions_server
        _, body = _get(f"{base}/api/sessions?runtime=claude&limit=1", token=token)
        data = json.loads(body)
        assert len(data["sessions"]) <= 1

    def test_content_type_is_json(self, sessions_server) -> None:
        """Content-Type is application/json; charset=utf-8."""
        base, token, _ = sessions_server
        req = urllib.request.Request(f"{base}/api/sessions?runtime=claude")
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct
