"""Unit tests for PiRuntimeAdapter + the "pi" ADAPTER_REGISTRY entry (T-30-B-04).

WS-PI-6 acceptance A10/A12:
- get_adapter("pi") returns a PiRuntimeAdapter.
- The adapter classifies liveness from ~/.pi/agent/sessions/<slug>/*.jsonl mtime
  (active/idle/ended) and degrades to "idle" on IO failure.
- Cost posture: cumulative_cost_usd=None, cost_known=False (never faked).

Liveness uses only file mtime (metadata) — T1: no session content is read. Tests
patch _PI_SESSIONS_DIR to a tmp dir and use os.utime to set deterministic mtimes.
"""

from __future__ import annotations

import os
import pathlib
from datetime import UTC, datetime, timedelta

from dadaia_workspace.features.telemetry.aggregator import runtimes as rt
from dadaia_workspace.features.telemetry.aggregator.models import (
    SessionDetail,
    SessionRow,
)
from dadaia_workspace.features.telemetry.aggregator.runtimes import (
    PiRuntimeAdapter,
    RuntimeAdapter,
    get_adapter,
)

_NOW_ISO = datetime.now(tz=UTC).isoformat()
_SESSION_ID = "019f01a5-3d7b-789a-9d58-9609039392cf"


def _make_row() -> SessionRow:
    return SessionRow(
        session_id=_SESSION_ID,
        runtime="pi",
        project="dadaia",
        cwd="/home/marco/workspace/dadaia",
        model="gpt-5.5",
        started_at=_NOW_ISO,
        last_activity_at=_NOW_ISO,
        message_count=2,
        context_size_tokens=900,
        cumulative_cost_usd=0.04,
        cost_known=True,
        status="ended",
        agent_name="pi (main)",
        ai_title=None,
    )


def _make_detail() -> SessionDetail:
    return SessionDetail(
        session_id=_SESSION_ID,
        runtime="pi",
        project="dadaia",
        cwd="/home/marco/workspace/dadaia",
        model="gpt-5.5",
        started_at=_NOW_ISO,
        last_activity_at=_NOW_ISO,
        message_count=2,
        context_size_tokens=900,
        cumulative_cost_usd=0.04,
        cost_known=True,
        status="ended",
        agent_name="pi (main)",
        ai_title=None,
        event_timestamps=(_NOW_ISO,),
    )


def _seed_session_file(
    sessions_dir: pathlib.Path, slug: str, session_id: str, mtime_delta_min: float
) -> pathlib.Path:
    slug_dir = sessions_dir / slug
    slug_dir.mkdir(parents=True, exist_ok=True)
    f = slug_dir / f"2026-06-26T01-57-14-236Z_{session_id}.jsonl"
    f.write_text("{}\n", encoding="utf-8")
    when = (datetime.now(tz=UTC) - timedelta(minutes=mtime_delta_min)).timestamp()
    os.utime(f, (when, when))
    return f


class TestRegistry:
    def test_get_adapter_pi_returns_pi_adapter(self) -> None:
        """A10: get_adapter("pi") returns a PiRuntimeAdapter."""
        adapter = get_adapter("pi")
        assert isinstance(adapter, PiRuntimeAdapter)

    def test_pi_adapter_satisfies_protocol(self) -> None:
        assert isinstance(PiRuntimeAdapter(), RuntimeAdapter)

    def test_registry_has_pi_key(self) -> None:
        assert "pi" in rt.ADAPTER_REGISTRY


class TestCostPosture:
    def test_enrich_row_cost_unknown(self) -> None:
        out = PiRuntimeAdapter().enrich_row(_make_row())
        assert out.cumulative_cost_usd is None
        assert out.cost_known is False

    def test_enrich_detail_cost_unknown(self) -> None:
        out = PiRuntimeAdapter().enrich_detail(_make_detail())
        assert out.cumulative_cost_usd is None
        assert out.cost_known is False


class TestLiveness:
    def test_active_recent_mtime(self, tmp_path: pathlib.Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(rt, "_PI_SESSIONS_DIR", tmp_path)
        _seed_session_file(tmp_path, "--home-marco-workspace-dadaia--", _SESSION_ID, 1)
        assert PiRuntimeAdapter().liveness(_SESSION_ID, "/x") == "active"

    def test_idle_mid_mtime(self, tmp_path: pathlib.Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(rt, "_PI_SESSIONS_DIR", tmp_path)
        _seed_session_file(tmp_path, "--slug--", _SESSION_ID, 30)
        assert PiRuntimeAdapter().liveness(_SESSION_ID, "/x") == "idle"

    def test_ended_old_mtime(self, tmp_path: pathlib.Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(rt, "_PI_SESSIONS_DIR", tmp_path)
        _seed_session_file(tmp_path, "--slug--", _SESSION_ID, 120)
        assert PiRuntimeAdapter().liveness(_SESSION_ID, "/x") == "ended"

    def test_ended_when_file_absent(self, tmp_path: pathlib.Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(rt, "_PI_SESSIONS_DIR", tmp_path)
        # No file seeded for this session id.
        assert PiRuntimeAdapter().liveness(_SESSION_ID, "/x") == "ended"

    def test_ended_when_sessions_dir_absent(self, tmp_path: pathlib.Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(rt, "_PI_SESSIONS_DIR", tmp_path / "nope")
        assert PiRuntimeAdapter().liveness(_SESSION_ID, "/x") == "ended"

    def test_resolution_matches_by_session_id_suffix(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:  # type: ignore[no-untyped-def]
        """The file is resolved by stem ending with the session id, across slug dirs."""
        monkeypatch.setattr(rt, "_PI_SESSIONS_DIR", tmp_path)
        _seed_session_file(tmp_path, "--other--", "unrelated-uuid", 1)
        _seed_session_file(tmp_path, "--target--", _SESSION_ID, 1)
        assert PiRuntimeAdapter().liveness(_SESSION_ID, "/x") == "active"
