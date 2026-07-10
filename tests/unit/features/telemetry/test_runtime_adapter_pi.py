"""Unit tests for PiRuntimeAdapter + the "pi" ADAPTER_REGISTRY entry (T-30-B-04).

WS-PI-6 acceptance A10/A12:
- get_adapter("pi") returns a PiRuntimeAdapter, registered under ADAPTER_REGISTRY["pi"],
  and satisfies the RuntimeAdapter protocol.
- The adapter classifies liveness from ~/.pi/agent/sessions/<slug>/*.jsonl mtime
  (active/idle/ended) and degrades to "idle"/"ended" on IO failure / absence.
- Cost posture: cumulative_cost_usd=None, cost_known=False (never faked).

Liveness uses only file mtime (metadata) — T1: no session content is read. Tests
patch _PI_SESSIONS_DIR to a tmp dir and use os.utime to set deterministic mtimes.
"""

from __future__ import annotations

import os
import pathlib
from datetime import UTC, datetime, timedelta

import pytest

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


@pytest.mark.parametrize(
    ("case", "setup", "expected"),
    [
        pytest.param(
            "active-recent-mtime",
            lambda tp: _seed_session_file(tp, "--home-marco-workspace-dadaia--", _SESSION_ID, 1),
            "active",
            id="active-recent-mtime",
        ),
        pytest.param(
            "idle-mid-mtime",
            lambda tp: _seed_session_file(tp, "--slug--", _SESSION_ID, 30),
            "idle",
            id="idle-mid-mtime",
        ),
        pytest.param(
            "ended-old-mtime",
            lambda tp: _seed_session_file(tp, "--slug--", _SESSION_ID, 120),
            "ended",
            id="ended-old-mtime",
        ),
        pytest.param("ended-file-absent", lambda tp: None, "ended", id="ended-when-file-absent"),
        pytest.param(
            "ended-sessions-dir-absent",
            None,  # handled specially below (points _PI_SESSIONS_DIR at a nonexistent dir)
            "ended",
            id="ended-when-sessions-dir-absent",
        ),
    ],
)
def test_liveness_mtime_thresholds(  # type: ignore[no-untyped-def]
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, case: str, setup, expected: str
) -> None:
    if case == "ended-sessions-dir-absent":
        monkeypatch.setattr(rt, "_PI_SESSIONS_DIR", tmp_path / "nope")
    else:
        monkeypatch.setattr(rt, "_PI_SESSIONS_DIR", tmp_path)
        setup(tmp_path)
    assert PiRuntimeAdapter().liveness(_SESSION_ID, "/x") == expected


def test_liveness_resolution_matches_by_session_id_suffix(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The file is resolved by stem ending with the session id, across slug dirs
    (A10: registered under ADAPTER_REGISTRY["pi"], protocol-conformant, and never
    fakes a cost — cumulative_cost_usd=None, cost_known=False on enrich)."""
    monkeypatch.setattr(rt, "_PI_SESSIONS_DIR", tmp_path)
    _seed_session_file(tmp_path, "--other--", "unrelated-uuid", 1)
    _seed_session_file(tmp_path, "--target--", _SESSION_ID, 1)
    assert PiRuntimeAdapter().liveness(_SESSION_ID, "/x") == "active"

    adapter = get_adapter("pi")
    assert isinstance(adapter, PiRuntimeAdapter)
    assert isinstance(adapter, RuntimeAdapter)
    assert "pi" in rt.ADAPTER_REGISTRY

    row_out = PiRuntimeAdapter().enrich_row(_make_row())
    assert row_out.cumulative_cost_usd is None
    assert row_out.cost_known is False

    detail_out = PiRuntimeAdapter().enrich_detail(_make_detail())
    assert detail_out.cumulative_cost_usd is None
    assert detail_out.cost_known is False
