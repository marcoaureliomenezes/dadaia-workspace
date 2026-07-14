"""Integration tests for corrupt-SQLite graceful degradation (T-AM-21) + filesystem
permission hardening (T-AM-20, folded in — same TelemetryService target, same stubs).

Merged per plan-integration.md (11 -> 2), plus the T-AM-20 permissions fn folded in:
  1. corruption: integrity-check -> quarantine rename (+wal/shm siblings) -> is_degraded;
     healthy negative.
  2. degraded HTTP: agents/sessions 503 with an actionable body,
     non-telemetry route unaffected (table).
  3. permission hardening: state_dir 0o700 + db 0o600, idempotent on drift (POSIX-only).

Uses tmp_path to avoid touching real state. The stub readers and aggregator ensure no
real operator data is read.
"""

from __future__ import annotations

import fnmatch
import json
import os
import pathlib
import sqlite3
import sys
import threading
import urllib.error
import urllib.request
from datetime import date
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.features.telemetry.service import TelemetryService  # noqa: E402
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao


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

    def list_sessions_by_agent(self, agent_id: str, **kwargs: Any) -> list:
        return []


class _StubSCS:
    def list_all(self) -> list:
        return []


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


def _build_panel_server(token: str, svc: TelemetryService) -> ThreadingHTTPServer:
    from dadaia_workspace.features.panel.handler import make_handler_class

    def _stub_view(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "text/html; charset=utf-8", b"<html>ok</html>")

    def _stub_json(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "application/json", b"{}")

    stub_views = {
        "index": _stub_view,
        "api_panel_status": _stub_json,
        "api_contexts": _stub_json,
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


def test_corrupt_db_detection_quarantine_siblings_and_healthy_negative(
    tmp_path: pathlib.Path,
) -> None:
    """Corruption: integrity-check -> quarantine rename (+wal/shm) -> is_degraded; healthy negative."""
    state_dir = tmp_path / "telemetry"
    state_dir.mkdir(parents=True)
    db_path = state_dir / "telemetry.sqlite"
    wal_path = state_dir / "telemetry.sqlite-wal"
    shm_path = state_dir / "telemetry.sqlite-shm"

    # Corrupt main DB + real-looking WAL/SHM siblings (invalid SQLite header).
    db_path.write_bytes(b"\x00" * 16)
    wal_path.write_bytes(b"WAL-FRAME-BYTES")
    shm_path.write_bytes(b"SHM-INDEX-BYTES")

    svc = _make_service(state_dir, tmp_path)
    assert not svc.is_degraded  # clean before refresh

    svc.refresh()

    assert svc.is_degraded, "service.is_degraded must be True after refresh() with a corrupt DB."
    assert not db_path.exists(), "telemetry.sqlite must be quarantined"
    assert not wal_path.exists(), "telemetry.sqlite-wal sibling must be quarantined too"
    assert not shm_path.exists(), "telemetry.sqlite-shm sibling must be quarantined too"

    main_q = [
        p
        for p in state_dir.glob("telemetry.sqlite.corrupt.*")
        if not p.name.endswith(("-wal", "-shm"))
    ]
    wal_q = list(state_dir.glob("telemetry.sqlite.corrupt.*-wal"))
    shm_q = list(state_dir.glob("telemetry.sqlite.corrupt.*-shm"))
    assert main_q, "no quarantined main DB file found"
    assert wal_q, "no quarantined -wal sibling found"
    assert shm_q, "no quarantined -shm sibling found"
    for qf in main_q + wal_q + shm_q:
        assert fnmatch.fnmatch(qf.name, "telemetry.sqlite.corrupt.*"), (
            f"Unexpected quarantine filename pattern: {qf.name}"
        )

    # Healthy negative: a normal (non-corrupt) DB does not set is_degraded.
    healthy_state_dir = tmp_path / "telemetry-healthy"
    healthy_svc = _make_service(healthy_state_dir, tmp_path)
    healthy_svc.refresh()
    assert not healthy_svc.is_degraded


@pytest.mark.skipif(sys.platform == "win32", reason="os.chmod mode bits are no-op on Windows")
def test_state_dir_0700_db_0600_and_idempotent_on_drift(tmp_path: pathlib.Path) -> None:
    """Filesystem permission hardening (T-AM-20): state_dir 0o700 (created + corrected
    from 0o755) + db 0o600 (idempotent on drift), own workspace."""
    state_dir = tmp_path / "perm-telemetry"
    assert not state_dir.exists()

    _make_service(state_dir, tmp_path)
    assert state_dir.exists(), "state_dir was not created"
    mode = state_dir.stat().st_mode & 0o777
    assert mode == 0o700, f"state_dir has mode 0o{mode:o} — expected 0o700."

    # Pre-existing dir with permissive mode is corrected to 0o700 by the constructor.
    other_state_dir = tmp_path / "perm-telemetry-existing"
    other_state_dir.mkdir(parents=True)
    os.chmod(other_state_dir, 0o755)
    _make_service(other_state_dir, tmp_path)
    mode = other_state_dir.stat().st_mode & 0o777
    assert mode == 0o700, f"state_dir mode was not corrected — got 0o{mode:o}, expected 0o700."

    # SQLite file created with 0o600 after refresh().
    svc = _make_service(state_dir, tmp_path)
    svc.refresh()
    db_path = state_dir / "telemetry.sqlite"
    assert db_path.exists(), "telemetry.sqlite was not created after refresh()"
    mode = db_path.stat().st_mode & 0o777
    assert mode == 0o600, f"telemetry.sqlite has mode 0o{mode:o} — expected 0o600."

    # Idempotent: external drift is corrected back to 0o600 on the next refresh.
    os.chmod(db_path, 0o644)
    svc._last_refresh = 0.0
    svc.refresh()
    mode = db_path.stat().st_mode & 0o777
    assert mode == 0o600, (
        f"telemetry.sqlite mode reverted to 0o{mode:o} — expected 0o600 "
        "after second refresh corrected drift."
    )


class TestHandlerDegradedResponses:
    """Panel handler returns 503 when service is degraded; non-telemetry routes unaffected."""

    @pytest.fixture(scope="class")
    @staticmethod
    def degraded_panel(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[misc]
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

        thread = threading.Thread(
            target=lambda: server.serve_forever(poll_interval=0.05), daemon=True
        )
        thread.start()

        yield base_url, test_token

        server.shutdown()

    @pytest.mark.parametrize(
        ("path", "with_token", "expected_status"),
        [
            ("/api/agents", True, 503),
            ("/api/agents", False, 503),  # no-auth: degraded check gates, not auth
            ("/api/agents/some-agent/sessions", True, 503),
            ("/api/agents/some-agent/sessions", False, 503),
            ("/", False, 200),  # non-telemetry route stays up
        ],
    )
    def test_degraded_http_status_table(
        self,
        degraded_panel: Any,
        path: str,
        with_token: bool,
        expected_status: int,
    ) -> None:
        base, token = degraded_panel
        status, body = _get(f"{base}{path}", token=token if with_token else None)
        assert status == expected_status, (
            f"Expected {expected_status} for {path} (with_token={with_token}), got {status}. "
            f"Body: {body!r}"
        )
        if path == "/api/agents" and with_token:
            # 503 body carries the degraded message + a quarantine-location hint, so the
            # operator can find the corrupt file (folded companion assertion, same fixture).
            data = json.loads(body)
            assert data.get("error") == "telemetry_degraded"
            body_text = body.decode("utf-8", errors="replace")
            assert "telemetry_degraded" in body_text
            assert "corrupt" in body_text.lower(), (
                "503 message should mention the quarantine location so the operator "
                "can find the corrupt file."
            )
