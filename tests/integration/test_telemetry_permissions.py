"""Integration test for TelemetryService filesystem permission hardening (T-AM-20).

Merged per plan-integration.md into one fn (posix-only): dir 0700 + db 0600 +
idempotent-on-re-refresh (state_dir corrected from a permissive 0o755, and the SQLite
file corrected back to 0o600 after external drift).

Uses tmp_path to avoid touching the real ~/.dadaia/state/telemetry/ directory. All
readers and the aggregator are replaced with in-process stubs so no real operator data
is read and no network calls are made. Mode-bit assertions are POSIX-only
(``os.chmod`` is a no-op on Windows).
"""

from __future__ import annotations

import os
import sys

import pytest

pytest.importorskip("fcntl")

import pathlib  # noqa: E402
import sqlite3  # noqa: E402
from datetime import date  # noqa: E402
from typing import Any  # noqa: E402

from dadaia_workspace.features.telemetry.service import TelemetryService  # noqa: E402
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao  # noqa: E402


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


def _make_service_on_disk(
    state_dir: pathlib.Path, workspace_root: pathlib.Path
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
        reader_factory=lambda: (_StubClaudeReader(), _StubCodexReader()),
        pricing_module=_StubPricing(),
        workspace_root=workspace_root,
        state_dir=state_dir,
        spec_context_service=_StubSCS(),
        _getuid_fn=lambda: 1000,
    )


@pytest.mark.skipif(sys.platform == "win32", reason="os.chmod mode bits are no-op on Windows")
def test_state_dir_0700_db_0600_and_idempotent_on_drift(tmp_path: pathlib.Path) -> None:
    """state_dir 0o700 (created + corrected from 0o755) + db 0o600 (idempotent on drift)."""
    state_dir = tmp_path / "telemetry"
    assert not state_dir.exists()

    _make_service_on_disk(state_dir, tmp_path)
    assert state_dir.exists(), "state_dir was not created"
    mode = state_dir.stat().st_mode & 0o777
    assert mode == 0o700, f"state_dir has mode 0o{mode:o} — expected 0o700."

    # Pre-existing dir with permissive mode is corrected to 0o700 by the constructor.
    other_state_dir = tmp_path / "telemetry-existing"
    other_state_dir.mkdir(parents=True)
    os.chmod(other_state_dir, 0o755)
    _make_service_on_disk(other_state_dir, tmp_path)
    mode = other_state_dir.stat().st_mode & 0o777
    assert mode == 0o700, f"state_dir mode was not corrected — got 0o{mode:o}, expected 0o700."

    # SQLite file created with 0o600 after refresh().
    svc = _make_service_on_disk(state_dir, tmp_path)
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
