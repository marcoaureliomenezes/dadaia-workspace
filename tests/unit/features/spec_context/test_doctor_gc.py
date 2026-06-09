"""Unit tests for DoctorService GC operations (T-016-06).

Acceptance criteria (SPEC §8 AC-08):
    - Stale ctx_locks/<ctx>.lock.json absent after doctor --fix.
    - TTL-expired .dadaia/sessions/<id>.json absent after doctor --fix.
    - Orphan ctx_locks/<ctx>.lock.sentinel (mtime > 30s) absent after doctor --fix.
    - No stale records: doctor --fix exits 0, nothing deleted.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import json  # noqa: E402
import os  # noqa: E402
import time  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (ws / "repos").mkdir()
    return ws


def _make_doctor(ws: Path, store: FakeContextStore | None = None) -> DoctorService:
    if store is None:
        store = FakeContextStore()
    return DoctorService(
        context_store=store,
        git_client=FakeGitClient(),
        workspace_root=ws,
    )


def _stale_iso(ttl: int = 300, extra_seconds: int = 60) -> str:
    """Return an ISO timestamp TTL+extra_seconds in the past (guaranteed stale)."""
    dt = datetime.now(tz=UTC) - timedelta(seconds=ttl + extra_seconds)
    return dt.isoformat()


def _fresh_iso() -> str:
    """Return a current ISO timestamp (guaranteed fresh for default TTL=1800)."""
    return datetime.now(tz=UTC).isoformat()


# ---------------------------------------------------------------------------
# T-016-06 AC-08a: stale ctx_locks/<ctx>.lock.json deleted by --fix
# ---------------------------------------------------------------------------


def test_stale_lock_json_deleted_after_fix(tmp_path: Path) -> None:
    """Stale ctx_locks/myctx.lock.json written to tmp workspace; doctor --fix deletes it."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"

    lock_file = ctx_locks_dir / "myctx.lock.json"
    stale_rec = {
        "context": "myctx",
        "release": "v0.1.6",
        "session_id": "old-sess",
        "mode": "BOUND_IMPLEMENTATION",
        "acquired_at": _stale_iso(ttl=1800),
        "heartbeat": _stale_iso(ttl=1800),
        "ttl": 1800,
    }
    lock_file.write_text(json.dumps(stale_rec, indent=2), encoding="utf-8")
    assert lock_file.exists(), "Precondition: lock file must exist before fix"

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not lock_file.exists(), (
        f"Stale lock file should be deleted after doctor fix, but still exists. Actions: {actions}"
    )
    assert any("LOCK-NEW" in a and "myctx.lock.json" in a for a in actions), (
        f"Expected LOCK-NEW action for myctx.lock.json, got: {actions}"
    )


# ---------------------------------------------------------------------------
# T-016-06 AC-08b: TTL-expired session file deleted by --fix
# ---------------------------------------------------------------------------


def test_expired_session_file_deleted_after_fix(tmp_path: Path) -> None:
    """TTL-expired .dadaia/sessions/<id>.json deleted by doctor --fix (graveyard GC)."""
    ws = _make_workspace(tmp_path)
    sessions_dir = ws / ".dadaia" / "sessions"

    sess_file = sessions_dir / "old-sess-001.json"
    expired_sess = {
        "session_id": "old-sess-001",
        "context": "myctx",
        "mode": "BOUND_IMPLEMENTATION",
        "release": "v0.1.6",
        "runtime": "test",
        "last_seen_at": _stale_iso(ttl=300),
        "ttl_seconds": 300,
    }
    sess_file.write_text(json.dumps(expired_sess, indent=2), encoding="utf-8")
    assert sess_file.exists(), "Precondition: session file must exist before fix"

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not sess_file.exists(), (
        f"Expired session file should be deleted after doctor fix, but still exists. "
        f"Actions: {actions}"
    )
    assert any("GRAVEYARD-GC" in a and "old-sess-001.json" in a for a in actions), (
        f"Expected GRAVEYARD-GC action for old-sess-001.json, got: {actions}"
    )


# ---------------------------------------------------------------------------
# T-016-06 AC-08c: orphan sentinel (mtime > 30s) deleted by --fix
# ---------------------------------------------------------------------------


def test_orphan_sentinel_deleted_after_fix(tmp_path: Path) -> None:
    """Orphan ctx_locks/<ctx>.lock.sentinel with mtime > 30s deleted by doctor --fix."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"

    sentinel = ctx_locks_dir / "myctx.lock.sentinel"
    sentinel.write_text("", encoding="utf-8")
    assert sentinel.exists()

    # Backdate mtime to 60 seconds ago to make it "orphaned"
    old_mtime = time.time() - 60.0
    os.utime(str(sentinel), (old_mtime, old_mtime))

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not sentinel.exists(), (
        f"Orphan sentinel should be deleted after doctor fix, but still exists. Actions: {actions}"
    )
    assert any("SENTINEL-GC" in a and "myctx.lock.sentinel" in a for a in actions), (
        f"Expected SENTINEL-GC action for myctx.lock.sentinel, got: {actions}"
    )


# ---------------------------------------------------------------------------
# T-016-06 AC-08d: no stale records → --fix exits 0, nothing deleted
# ---------------------------------------------------------------------------


def test_no_stale_records_fix_exits_clean(tmp_path: Path) -> None:
    """No stale records: doctor fix exits 0, no files deleted."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"
    sessions_dir = ws / ".dadaia" / "sessions"

    # Write a FRESH lock record (well within TTL)
    lock_file = ctx_locks_dir / "freshctx.lock.json"
    fresh_rec = {
        "context": "freshctx",
        "release": "v0.1.6",
        "session_id": "live-sess",
        "mode": "BOUND_IMPLEMENTATION",
        "acquired_at": _fresh_iso(),
        "heartbeat": _fresh_iso(),
        "ttl": 1800,
    }
    lock_file.write_text(json.dumps(fresh_rec, indent=2), encoding="utf-8")

    # Write a FRESH session file
    sess_file = sessions_dir / "live-sess.json"
    fresh_sess = {
        "session_id": "live-sess",
        "context": "freshctx",
        "mode": "BOUND_IMPLEMENTATION",
        "release": "v0.1.6",
        "runtime": "test",
        "last_seen_at": _fresh_iso(),
        "ttl_seconds": 1800,
    }
    sess_file.write_text(json.dumps(fresh_sess, indent=2), encoding="utf-8")

    # Write a FRESH sentinel (mtime = now, age < 30s)
    sentinel = ctx_locks_dir / "freshctx.lock.sentinel"
    sentinel.write_text("", encoding="utf-8")

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    # Nothing should be deleted
    assert lock_file.exists(), "Fresh lock file should NOT be deleted"
    assert sess_file.exists(), "Fresh session file should NOT be deleted"
    assert sentinel.exists(), "Fresh sentinel should NOT be deleted (age < 30s)"

    gc_actions = [a for a in actions if "GC" in a or "LOCK-NEW" in a]
    assert gc_actions == [], f"Expected no GC actions for fresh records, got: {gc_actions}"


# ---------------------------------------------------------------------------
# T-016-06: invalid/missing-fields lock file deleted by --fix
# ---------------------------------------------------------------------------


def test_invalid_lock_file_deleted_after_fix(tmp_path: Path) -> None:
    """Invalid JSON lock file is deleted by doctor --fix."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"

    bad_lock = ctx_locks_dir / "badctx.lock.json"
    bad_lock.write_text("NOT JSON {{{", encoding="utf-8")

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not bad_lock.exists(), "Invalid JSON lock file should be deleted by fix"
    assert any("LOCK-NEW" in a and "badctx.lock.json" in a for a in actions), (
        f"Expected LOCK-NEW action for badctx.lock.json, got: {actions}"
    )


def test_missing_fields_lock_file_deleted_after_fix(tmp_path: Path) -> None:
    """Lock file missing required fields is deleted by doctor --fix."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"

    incomplete_lock = ctx_locks_dir / "incompletectx.lock.json"
    incomplete_rec = {
        "context": "incompletectx",
        # Missing: release, session_id, mode, acquired_at, heartbeat, ttl
    }
    incomplete_lock.write_text(json.dumps(incomplete_rec, indent=2), encoding="utf-8")

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not incomplete_lock.exists(), "Incomplete lock file should be deleted by fix"
    assert any("LOCK-NEW" in a and "incompletectx.lock.json" in a for a in actions), (
        f"Expected LOCK-NEW action for incompletectx.lock.json, got: {actions}"
    )
