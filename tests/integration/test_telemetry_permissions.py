"""Integration tests for TelemetryService filesystem permission hardening (T-AM-20).

Verifies that:
  1. The state directory is created with mode 0o700 (owner rwx only).
  2. The SQLite database file is created with mode 0o600 (owner rw only).

Uses tmp_path to avoid touching the real ~/.dadaia/state/telemetry/ directory.
All readers and the aggregator are replaced with in-process stubs so no real
operator data is read and no network calls are made.
"""
from __future__ import annotations

import pathlib
import sqlite3
from datetime import date
from typing import Any

import pytest

from dadaia_workspace.features.telemetry.store.schema import apply_migrations
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.service import TelemetryService


# ---------------------------------------------------------------------------
# Stubs — same pattern as tests/unit/features/telemetry/test_service.py
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
        pass  # no-op


class _StubCodexReader:
    def read_sessions(self, path: Any, dao: Any, now_iso: str) -> None:
        pass  # no-op


class _StubWorkflowsReader:
    def read_workflows(self, root: Any, dao: Any, agents: list, now_iso: str) -> None:
        pass  # no-op


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
# Helper to build a TelemetryService backed by a real on-disk SQLite DB
# under tmp_path (so chmod effects are visible).
# ---------------------------------------------------------------------------

def _make_service_on_disk(
    state_dir: pathlib.Path,
    workspace_root: pathlib.Path,
) -> TelemetryService:
    """Build a TelemetryService that writes its DB to ``state_dir``."""
    db_path = state_dir / "telemetry.sqlite"

    def _dao_factory() -> TelemetryDao:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        return TelemetryDao(conn)

    return TelemetryService(
        dao_factory=_dao_factory,
        aggregator=_StubAggregator(),
        reader_factory=lambda: (_StubClaudeReader(), _StubCodexReader(), _StubWorkflowsReader()),
        pricing_module=_StubPricing(),
        workspace_root=workspace_root,
        state_dir=state_dir,
        spec_context_service=_StubSCS(),
        # Ensure we never block on uid=0 check in CI environments.
        _getuid_fn=lambda: 1000,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTelemetryDirectoryPermissions:
    def test_state_dir_created_with_0o700(self, tmp_path: pathlib.Path) -> None:
        """After construction, state_dir mode must be 0o700 (owner rwx only)."""
        state_dir = tmp_path / "telemetry"
        assert not state_dir.exists()

        _make_service_on_disk(state_dir, tmp_path)

        assert state_dir.exists(), "state_dir was not created"
        mode = state_dir.stat().st_mode & 0o777
        assert mode == 0o700, (
            f"state_dir has mode 0o{mode:o} — expected 0o700. "
            "Directory must be restricted to owning user only."
        )

    def test_state_dir_mode_after_existing_dir(self, tmp_path: pathlib.Path) -> None:
        """If state_dir already exists with wrong perms, constructor fixes them to 0o700."""
        state_dir = tmp_path / "telemetry"
        # Pre-create with permissive mode.
        state_dir.mkdir(parents=True)
        import os
        os.chmod(state_dir, 0o755)

        _make_service_on_disk(state_dir, tmp_path)

        mode = state_dir.stat().st_mode & 0o777
        assert mode == 0o700, (
            f"state_dir mode was not corrected — got 0o{mode:o}, expected 0o700."
        )


class TestTelemetrySQLitePermissions:
    def test_sqlite_file_created_with_0o600(self, tmp_path: pathlib.Path) -> None:
        """After refresh(), the SQLite DB file must have mode 0o600 (owner rw only)."""
        state_dir = tmp_path / "telemetry"
        svc = _make_service_on_disk(state_dir, tmp_path)

        svc.refresh()

        db_path = state_dir / "telemetry.sqlite"
        assert db_path.exists(), "telemetry.sqlite was not created after refresh()"
        mode = db_path.stat().st_mode & 0o777
        assert mode == 0o600, (
            f"telemetry.sqlite has mode 0o{mode:o} — expected 0o600. "
            "Database file must be restricted to owning user only."
        )

    def test_sqlite_mode_idempotent_on_second_refresh(self, tmp_path: pathlib.Path) -> None:
        """Calling refresh() twice keeps the SQLite file at 0o600."""
        import os
        state_dir = tmp_path / "telemetry"
        svc = _make_service_on_disk(state_dir, tmp_path)

        svc.refresh()
        db_path = state_dir / "telemetry.sqlite"
        # Simulate drift: another process relaxed the mode.
        os.chmod(db_path, 0o644)

        # Force another refresh cycle by resetting last_refresh.
        svc._last_refresh = 0.0
        svc.refresh()

        mode = db_path.stat().st_mode & 0o777
        assert mode == 0o600, (
            f"telemetry.sqlite mode reverted to 0o{mode:o} — expected 0o600 "
            "after second refresh corrected drift."
        )
