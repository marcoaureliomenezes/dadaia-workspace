"""DoctorService PRESENCE-GC: stale advisory presence-record GC (v0.1.76 T-4, FR7).

The lease's ``ctx_locks/*.lock.json`` heartbeat is no longer the concurrency signal —
``features/spec_context/presence.py`` (``.dadaia/states/presence/<ctx>/<sid>.json``) is
the ONLY concurrency-signal surface post-doctrine (FR2). ``presence.sweep()`` (T-2) already
implements the GC predicate (TTL-only staleness, corrupt-record removal) but had zero
production consumers until this task wires it into the workspace doctor's ``check()``/
``fix()`` — the doctor's documented GC surface (LOCK-GC/SENTINEL-GC/GRAVEYARD-GC/PTR-GC
siblings).

``check()`` reports ``PRESENCE-GC`` for every stale/corrupt presence record found (WARN-
severity by construction — presence is advisory, never a security concern); ``--fix``
sweeps them via ``presence.sweep()``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.core import kernel_tunables  # noqa: E402
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

TTL = kernel_tunables.LEASE_TTL_SECONDS


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / "repos").mkdir()
    return ws


def _make_doctor(ws: Path) -> DoctorService:
    return DoctorService(
        context_store=FakeContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )


def _presence_path(ws: Path, ctx: str, sid: str) -> Path:
    return ws / ".dadaia" / "states" / "presence" / ctx / f"{sid}.json"


def _write_presence(
    ws: Path, ctx: str, sid: str, *, heartbeat_age_s: float = 0.0, corrupt: bool = False
) -> Path:
    path = _presence_path(ws, ctx, sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    if corrupt:
        path.write_text("{not-json", encoding="utf-8")
        return path
    now = datetime.now(tz=UTC) - timedelta(seconds=heartbeat_age_s)
    record = {
        "session_id": sid,
        "runtime": "claude",
        "pid": 4242,
        "started_at": now.isoformat(),
        "last_seen_at": now.isoformat(),
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def test_check_reports_presence_gc_for_stale_record(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _write_presence(ws, "myctx", "sess-stale", heartbeat_age_s=TTL + 100)

    doctor = _make_doctor(ws)
    issues = [i for i in doctor.check() if i.code == "PRESENCE-GC"]

    assert issues, "expected PRESENCE-GC for a stale presence record"
    assert any("sess-stale" in i.description for i in issues)
    assert all(i.fixable for i in issues)


def test_check_reports_presence_gc_for_corrupt_record(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _write_presence(ws, "myctx", "sess-corrupt", corrupt=True)

    doctor = _make_doctor(ws)
    issues = [i for i in doctor.check() if i.code == "PRESENCE-GC"]

    assert issues, "expected PRESENCE-GC for a corrupt presence record"


def test_check_does_not_report_fresh_presence_record(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _write_presence(ws, "myctx", "sess-fresh", heartbeat_age_s=0.0)

    doctor = _make_doctor(ws)
    issues = [i for i in doctor.check() if i.code == "PRESENCE-GC"]

    assert issues == [], "a fresh presence record must never be flagged"


def test_fix_sweeps_stale_and_corrupt_presence_records(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    stale_path = _write_presence(ws, "myctx", "sess-stale", heartbeat_age_s=TTL + 100)
    corrupt_path = _write_presence(ws, "myctx", "sess-corrupt", corrupt=True)
    fresh_path = _write_presence(ws, "myctx", "sess-fresh", heartbeat_age_s=0.0)

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not stale_path.exists()
    assert not corrupt_path.exists()
    assert fresh_path.exists()
    assert any("PRESENCE-GC" in a and "sess-stale" in a for a in actions), actions
    assert any("PRESENCE-GC" in a and "sess-corrupt" in a for a in actions), actions


def test_fix_leaves_no_presence_gc_action_when_all_fresh(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _write_presence(ws, "myctx", "sess-fresh", heartbeat_age_s=0.0)

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not any("PRESENCE-GC" in a for a in actions)


def test_check_never_raises_on_missing_presence_root(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    doctor = _make_doctor(ws)
    assert [i for i in doctor.check() if i.code == "PRESENCE-GC"] == []
