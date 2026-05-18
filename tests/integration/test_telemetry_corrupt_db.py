"""Integration tests for corrupt-SQLite graceful degradation (T-AM-21).

Verifies that when the telemetry database file is corrupt (invalid SQLite header):
  1. TelemetryService detects the corruption via PRAGMA integrity_check.
  2. The corrupt file is renamed to telemetry.sqlite.corrupt.<utc_ts>.
  3. service.is_degraded is True after refresh().
  4. /api/agents with a valid Bearer token returns 503 with JSON body containing
     "telemetry_degraded".
  5. /api/agents WITHOUT a Bearer token returns 401 (auth check precedes
     degraded check — ordering invariant).

Uses tmp_path to avoid touching real state. The stub readers and aggregator
ensure no real operator data is read.
"""

from __future__ import annotations

import fnmatch
import json
import pathlib
import sqlite3
import threading
import urllib.error
import urllib.request
from datetime import date
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

from dadaia_workspace.features.telemetry.service import TelemetryService
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubPricing:
    PRICING_TABLE: dict[str, list] = {}

    @staticmethod
    def compute_cost(usage: dict, model: str, when: date) -> int | None:
        return None

    @staticmethod
    def pricing_age_days(models_used: list[str], when: Any = None) -> int | None:
        return None


class _StubClaudeReader:
    def read_session_file(self, path: Any, dao: Any, now_iso: str) -> None:
        pass


class _StubCodexReader:
    def read_sessions(self, path: Any, dao: Any, now_iso: str) -> None:
        pass


class _StubAggregator:
    def list_agents(self, **kwargs: Any) -> list:
        return []

    def list_workflows(self) -> list:
        return []

    def list_sessions_by_agent(self, agent_id: str, **kwargs: Any) -> list:
        return []


class _StubSCS:
    def list_all(self) -> list:
        return []


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------


def _make_service(state_dir: pathlib.Path, workspace_root: pathlib.Path) -> TelemetryService:
    """Build a TelemetryService using a real on-disk SQLite path under state_dir."""
    db_path = state_dir / "telemetry.sqlite"

    def _dao_factory() -> TelemetryDao:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        return TelemetryDao(conn)

    return TelemetryService(
        dao_factory=_dao_factory,
        aggregator=_StubAggregator(),
        reader_factory=lambda: (_StubClaudeReader(), _StubCodexReader()),
        pricing_module=_StubPricing(),
        workspace_root=workspace_root,
        state_dir=state_dir,
        spec_context_service=_StubSCS(),
        _getuid_fn=lambda: 1000,
    )


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


def _build_panel_server(token: str, svc: TelemetryService) -> ThreadingHTTPServer:
    from dadaia_workspace.features.panel.handler import make_handler_class

    def _stub_view(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "text/html; charset=utf-8", b"<html>ok</html>")

    def _stub_json(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "application/json", b"{}")

    stub_views = {
        "index": _stub_view,
        "api_servers": _stub_json,
        "api_contexts": _stub_json,
        "api_workflows": _stub_json,
        "memory": _stub_view,
        "memory_view": _stub_view,
        "static": lambda **kw: (200, "text/plain; charset=utf-8", b"ok"),
    }
    HandlerClass = make_handler_class(stub_views, token=token, telemetry=svc)
    return ThreadingHTTPServer(("127.0.0.1", 0), HandlerClass)


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
# Tests: degraded service (corrupt file fixture)
# ---------------------------------------------------------------------------


class TestCorruptDatabaseDegradation:
    """Service detects a corrupt DB, quarantines it, and enters degraded mode."""

    def test_corrupt_file_triggers_is_degraded(self, tmp_path: pathlib.Path) -> None:
        """After refresh() with a corrupt DB, service.is_degraded is True."""
        state_dir = tmp_path / "telemetry"
        state_dir.mkdir(parents=True)
        db_path = state_dir / "telemetry.sqlite"
        # Write 16 bytes of garbage (not a valid SQLite header: must start with
        # "SQLite format 3\x00").
        db_path.write_bytes(b"\x00" * 16)

        svc = _make_service(state_dir, tmp_path)
        assert not svc.is_degraded  # clean before refresh

        svc.refresh()

        assert svc.is_degraded, (
            "service.is_degraded must be True after refresh() with a corrupt DB."
        )

    def test_corrupt_file_renamed_to_quarantine(self, tmp_path: pathlib.Path) -> None:
        """The corrupt file is renamed to telemetry.sqlite.corrupt.<utc_ts>."""
        state_dir = tmp_path / "telemetry"
        state_dir.mkdir(parents=True)
        db_path = state_dir / "telemetry.sqlite"
        db_path.write_bytes(b"NOT_A_VALID_SQLITE_FILE_HEADER_HERE!")

        svc = _make_service(state_dir, tmp_path)
        svc.refresh()

        # Original file must be gone.
        assert not db_path.exists(), (
            "telemetry.sqlite must be renamed away after corruption is detected."
        )

        # A quarantine file matching the expected pattern must exist.
        quarantine_files = list(state_dir.glob("telemetry.sqlite.corrupt.*"))
        assert quarantine_files, (
            "No quarantine file found — corrupt DB must be renamed to "
            "telemetry.sqlite.corrupt.<utc_ts>."
        )
        # File name must match telemetry.sqlite.corrupt.<ts> where ts is like 20260517T123456Z.
        for qf in quarantine_files:
            assert fnmatch.fnmatch(qf.name, "telemetry.sqlite.corrupt.*"), (
                f"Unexpected quarantine filename pattern: {qf.name}"
            )
            # The timestamp suffix must be a valid UTC ISO datetime with 'Z'.
            suffix = qf.name.split("telemetry.sqlite.corrupt.", 1)[1]
            assert suffix.endswith("Z"), f"Timestamp suffix must end with 'Z': {suffix!r}"

    def test_degraded_not_triggered_for_healthy_db(self, tmp_path: pathlib.Path) -> None:
        """Normal (healthy) DB does not set is_degraded = True."""
        state_dir = tmp_path / "telemetry"
        svc = _make_service(state_dir, tmp_path)
        svc.refresh()
        assert not svc.is_degraded


# ---------------------------------------------------------------------------
# Tests: handler returns correct HTTP status codes
# ---------------------------------------------------------------------------


class TestHandlerDegradedResponses:
    """Panel handler returns 503 when service is degraded, 401 when unauthenticated."""

    @pytest.fixture(scope="class")
    def degraded_panel(self, tmp_path_factory: pytest.TempPathFactory):  # type: ignore[override]
        """Start a panel server backed by a degraded TelemetryService."""
        tmp_path = tmp_path_factory.mktemp("corrupt_test")
        state_dir = tmp_path / "telemetry"
        state_dir.mkdir(parents=True)
        db_path = state_dir / "telemetry.sqlite"
        db_path.write_bytes(b"\xff" * 32)  # invalid SQLite header

        svc = _make_service(state_dir, tmp_path)
        svc.refresh()
        assert svc.is_degraded  # pre-condition

        test_token = "test-token-corrupt-xyz"
        server = _build_panel_server(test_token, svc)
        port = server.server_address[1]
        base_url = f"http://127.0.0.1:{port}"

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        yield base_url, test_token

        server.shutdown()

    def test_api_agents_with_token_returns_503(self, degraded_panel: Any) -> None:
        """GET /api/agents with valid Bearer → 503 when service is degraded."""
        base, token = degraded_panel
        status, body = _get(f"{base}/api/agents", token=token)
        assert status == 503, f"Expected 503 for degraded service but got {status}. Body: {body!r}"
        data = json.loads(body)
        assert data.get("error") == "telemetry_degraded", (
            f"Response body must have error='telemetry_degraded', got: {data}"
        )

    def test_api_agents_without_token_returns_401(self, degraded_panel: Any) -> None:
        """GET /api/agents WITHOUT Bearer → 401 (auth check precedes degraded check)."""
        base, token = degraded_panel
        status, body = _get(f"{base}/api/agents")
        assert status == 401, (
            f"Expected 401 for missing token but got {status}. "
            "Auth must be checked before the degraded-mode 503."
        )

    def test_api_workflows_with_token_returns_200(self, degraded_panel: Any) -> None:
        """GET /api/workflows with valid Bearer → 200 even when telemetry is degraded.

        api_workflows is a bearer-only route (PR3-14) backed by the canonical
        WorkflowsService — it does NOT go through the telemetry service, so
        corrupt-DB degradation does not affect it.
        """
        base, token = degraded_panel
        status, body = _get(f"{base}/api/workflows", token=token)
        assert status == 200

    def test_api_sessions_with_token_returns_503(self, degraded_panel: Any) -> None:
        """GET /api/agents/{id}/sessions with valid Bearer → 503 when degraded."""
        base, token = degraded_panel
        status, body = _get(f"{base}/api/agents/some-agent/sessions", token=token)
        assert status == 503

    def test_api_sessions_without_token_returns_401(self, degraded_panel: Any) -> None:
        """GET /api/agents/{id}/sessions without token → 401 regardless of degraded."""
        base, token = degraded_panel
        status, body = _get(f"{base}/api/agents/some-agent/sessions")
        assert status == 401

    def test_503_body_contains_message(self, degraded_panel: Any) -> None:
        """503 response body must mention 'telemetry_degraded' and quarantine path."""
        base, token = degraded_panel
        status, body = _get(f"{base}/api/agents", token=token)
        assert status == 503
        body_text = body.decode("utf-8", errors="replace")
        assert "telemetry_degraded" in body_text
        assert "corrupt" in body_text.lower(), (
            "503 message should mention the quarantine location so the operator "
            "can find the corrupt file."
        )

    def test_non_telemetry_endpoint_unaffected(self, degraded_panel: Any) -> None:
        """GET / still returns 200 even when telemetry is degraded (panel stays up)."""
        base, token = degraded_panel
        status, body = _get(f"{base}/")
        assert status == 200, f"GET / should return 200 even in degraded mode, got {status}."
