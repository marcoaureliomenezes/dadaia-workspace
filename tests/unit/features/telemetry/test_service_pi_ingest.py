"""Service-level test for PI ingestion wiring (T-30-B-04 / A12).

Proves TelemetryService._do_refresh calls the PI reader (3rd tuple element) with
the resolved sessions dir, and that a legacy 2-tuple reader factory still works
(PI ingestion skipped, no crash) — back-compat.
"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import Any

from dadaia_workspace.features.telemetry.service import TelemetryService
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations


class _NoopClaude:
    def read_session_file(self, *_a: Any, **_k: Any) -> None:
        return None


class _NoopCodex:
    def read_codex_db(self, *_a: Any, **_k: Any) -> None:
        return None


class _RecordingPi:
    def __init__(self) -> None:
        self.calls: list[pathlib.Path] = []

    def read_pi_sessions(self, sessions_dir: pathlib.Path, _dao: Any, _now_iso: str) -> None:
        self.calls.append(sessions_dir)


class _FakeAggregator:
    pass


class _FakeSCS:
    pass


def _build(reader_factory: Any, state_dir: pathlib.Path, ws: pathlib.Path) -> TelemetryService:
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    dao = TelemetryDao(conn)

    return TelemetryService(
        dao_factory=lambda: dao,
        aggregator=_FakeAggregator(),
        reader_factory=reader_factory,
        pricing_module=type("_P", (), {"compute_cost": staticmethod(lambda *_a, **_k: None)})(),
        workspace_root=ws,
        state_dir=state_dir,
        spec_context_service=_FakeSCS(),
        _getuid_fn=lambda: 1000,
    )


def test_pi_reader_invoked_with_env_override(tmp_path: pathlib.Path, monkeypatch: Any) -> None:
    """The 3rd reader (pi) is called with DADAIA_PI_SESSIONS_DIR when set."""
    pi_dir = tmp_path / "pi-sessions"
    pi_dir.mkdir()
    monkeypatch.setenv("DADAIA_PI_SESSIONS_DIR", str(pi_dir))

    pi = _RecordingPi()
    svc = _build(
        lambda: (_NoopClaude(), _NoopCodex(), pi),
        tmp_path / "state",
        tmp_path / "ws",
    )
    svc.refresh()

    assert pi.calls == [pi_dir]


def test_legacy_two_tuple_skips_pi(tmp_path: pathlib.Path) -> None:
    """A legacy 2-tuple reader factory still refreshes without error (no PI)."""
    svc = _build(
        lambda: (_NoopClaude(), _NoopCodex()),
        tmp_path / "state",
        tmp_path / "ws",
    )
    # Must not raise — PI ingestion simply skipped.
    svc.refresh()


def test_pi_reader_error_degrades(tmp_path: pathlib.Path, monkeypatch: Any) -> None:
    """A PI reader that raises does not crash the refresh (graceful degradation)."""
    monkeypatch.setenv("DADAIA_PI_SESSIONS_DIR", str(tmp_path / "absent"))

    class _BoomPi:
        def read_pi_sessions(self, *_a: Any, **_k: Any) -> None:
            raise OSError("boom")

    svc = _build(
        lambda: (_NoopClaude(), _NoopCodex(), _BoomPi()),
        tmp_path / "state",
        tmp_path / "ws",
    )
    svc.refresh()  # must not raise
