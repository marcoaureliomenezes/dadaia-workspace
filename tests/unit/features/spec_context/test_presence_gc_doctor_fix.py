"""``DoctorService.fix()`` delegates presence/marker reclamation to ``presence.gc()``
(release 0.5.1 K2 — "callers: doctor --fix and the post-gate on its throttle").

Intent: CONTRACT — release 0.5.1 K2

Split out of ``test_presence_gc.py`` (not merged in): ``DoctorService.fix()`` calls
``presence.gc(..., now=datetime.now(tz=UTC))`` — no injectable clock at that boundary —
so every fixture here ages against the REAL wall clock, with NO frozen datetime constant
anywhere in this file (the frozen-clock-vs-real-clock combination
``tests/contract/test_frozen_clock_aging_ratchet.py`` forbids). Staleness margins are
generous (100s / 1h over TTL) so ordinary test wall-clock jitter never flips a verdict.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.features.spec_context.doctor import DoctorService
from tests.fakes import FakeContextStore, FakeGitClient

pytestmark = pytest.mark.unit

_PRESENCE_TTL = kernel_tunables.PRESENCE_TTL_SECONDS
_MARKER_TTL = kernel_tunables.SENTINEL_GC_TTL_SECONDS


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / "repos").mkdir()
    return ws


def _make_doctor(ws: Path) -> DoctorService:
    return DoctorService(
        context_store=FakeContextStore(), git_client=FakeGitClient(), workspace_root=ws
    )


def _presence_path(ws: Path, ctx: str, sid: str) -> Path:
    return ws / ".dadaia" / "states" / "presence" / ctx / f"{sid}.json"


def _write_presence(ws: Path, ctx: str, sid: str, *, age_seconds: float = 0.0) -> Path:
    path = _presence_path(ws, ctx, sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = (datetime.now(tz=UTC) - timedelta(seconds=age_seconds)).isoformat()
    record = {"session_id": sid, "runtime": "claude", "pid": 1, "last_seen_at": seen}
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _write_marker(ws: Path, name: str, *, age_seconds: float) -> Path:
    path = ws / ".dadaia" / "tmp" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("marker", encoding="utf-8")
    mtime = datetime.now(tz=UTC).timestamp() - age_seconds
    os.utime(path, (mtime, mtime))
    return path


def test_doctor_fix_reaps_stale_presence_via_gc(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    stale = _write_presence(ws, "myctx", "sess-stale", age_seconds=_PRESENCE_TTL + 100)

    actions = _make_doctor(ws).fix()

    assert not stale.exists()
    assert any("PRESENCE-GC" in a and "sess-stale" in a for a in actions), actions


def test_doctor_fix_reaps_stale_marker_via_gc(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    marker = _write_marker(ws, "reconciler-last-ghost", age_seconds=_MARKER_TTL + 3600)

    actions = _make_doctor(ws).fix()

    assert not marker.exists()
    assert any("PRESENCE-GC" in a and "reconciler-last-ghost" in a for a in actions), actions


def test_doctor_fix_leaves_fresh_presence_untouched(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    fresh = _write_presence(ws, "myctx", "sess-fresh", age_seconds=0.0)

    actions = _make_doctor(ws).fix()

    assert fresh.exists()
    assert not any("PRESENCE-GC" in a for a in actions)
