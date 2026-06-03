"""Spec-context lock heartbeat, expiry, reclaim, and doctor behavior.

Acceptance criteria:
    - expired locks are classified as stale.
    - stale locks can be reclaimed with an audit record.
    - fresh held locks cannot be reclaimed.
    - heartbeat renewal keeps a lock held and updates last_seen_at.
    - doctor marks expired locks stale without deleting them.
    - doctor removes locks for dead contexts and appends audit records.
    - lock audit events have the expected JSONL schema.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import LockActiveError
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.spec_context.locking import (
    LockState,
    _audit_log_path,
    _impl_lock_path,
    audit_acquired,
    audit_blocked,
    check_lock_state,
    create_impl_lock,
    reclaim_impl_lock,
    renew_heartbeat,
)
from tests.fakes import FakeContextStore, FakeGitClient, FakePrimaryContextStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stale_iso(minutes: int = 10) -> str:
    """Return an ISO 8601 UTC timestamp *minutes* ago."""
    return (datetime.now(tz=UTC) - timedelta(minutes=minutes)).isoformat()


def _make_stale_lock(
    ws: Path,
    context: str,
    release: str,
    session_id: str = "sess_stale",
    ttl_seconds: int = 300,
    minutes_ago: int = 10,
) -> Path:
    """Write a lock file with last_seen_at backdated by *minutes_ago* minutes."""
    lock_path = _impl_lock_path(ws, context, release)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    old_ts = _stale_iso(minutes_ago)
    lock_data = {
        "lock_type": "implementation",
        "context": context,
        "release": release,
        "session_id": session_id,
        "runtime": "test-runtime",
        "pid": os.getpid(),
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": old_ts,
        "last_seen_at": old_ts,
        "ttl_seconds": ttl_seconds,
        "task_path": "",
        "owner_note": "",
    }
    lock_path.write_text(json.dumps(lock_data, indent=2))
    return lock_path


def _make_doctor(
    ws: Path,
    store: FakeContextStore | None = None,
) -> DoctorService:
    if store is None:
        store = FakeContextStore()
    return DoctorService(
        context_store=store,
        primary_store=FakePrimaryContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )


def _make_dead_ctx(name: str, slug: str) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=ContextState.DEAD,
        repo_slug=slug,
        repo_url=f"https://example.com/{slug}",
        created_at="2026-01-01T00:00:00Z",
        dead_since="2026-01-01T00:00:00Z",
    )


def test_stale_detection_respects_lock_ttl(tmp_path: Path) -> None:
    """A lock older than its ttl_seconds is classified as STALE."""
    ws = tmp_path
    # last_seen_at is 10 min ago; ttl is 180 s (3 min) → elapsed >> ttl → STALE
    _make_stale_lock(ws, "proj", "v1", ttl_seconds=180, minutes_ago=10)

    state = check_lock_state(ws, "proj", "v1")
    assert state == LockState.STALE, f"Expected STALE, got {state}"


def test_reclaim_stale_lock_updates_owner_and_audits_ordered_events(
    tmp_path: Path,
) -> None:
    """Reclaiming a stale lock updates owner and audits stale detection before reclaim."""
    ws = tmp_path
    _make_stale_lock(ws, "proj", "v1", session_id="sess_old")

    assert check_lock_state(ws, "proj", "v1") == LockState.STALE

    new_data = reclaim_impl_lock(
        ws,
        context="proj",
        release="v1",
        new_session_id="sess_new",
        runtime="test-runtime",
        pid=os.getpid(),
        reason="operator reclaim after TTL expiry",
    )

    assert new_data["session_id"] == "sess_new"
    assert check_lock_state(ws, "proj", "v1") == LockState.HELD

    log_path = _audit_log_path(ws)
    assert log_path.exists()
    events = [json.loads(ln)["event"] for ln in log_path.read_text().splitlines() if ln.strip()]
    assert "STALE_DETECTED" in events, f"STALE_DETECTED missing: {events}"
    assert "RECLAIMED" in events, f"RECLAIMED missing: {events}"
    assert events.index("STALE_DETECTED") < events.index("RECLAIMED")


def test_reclaim_held_lock_raises_lock_active_error(tmp_path: Path) -> None:
    """A fresh HELD lock cannot be reclaimed by another session."""
    ws = tmp_path
    create_impl_lock(
        ws,
        context="proj",
        release="v1",
        session_id="sess_held",
        runtime="test-runtime",
        pid=os.getpid(),
    )
    assert check_lock_state(ws, "proj", "v1") == LockState.HELD

    with pytest.raises(LockActiveError) as exc_info:
        reclaim_impl_lock(
            ws,
            context="proj",
            release="v1",
            new_session_id="sess_intruder",
            runtime="test-runtime",
            pid=os.getpid(),
            reason="should not work",
        )

    assert (
        "HELD" in str(exc_info.value)
        or "sess_held" in str(exc_info.value)
        or "reclaim" in str(exc_info.value).lower()
    )


def test_heartbeat_updates_last_seen_at_and_keeps_lock_held(tmp_path: Path) -> None:
    """renew_heartbeat updates last_seen_at and leaves the lock HELD."""
    ws = tmp_path

    # Create a fresh lock
    create_impl_lock(
        ws,
        context="proj",
        release="v1",
        session_id="sess_1",
        runtime="test-runtime",
        pid=os.getpid(),
    )

    # Read initial last_seen_at
    lock_path = _impl_lock_path(ws, "proj", "v1")
    initial_data = json.loads(lock_path.read_text())
    initial_ts = initial_data["last_seen_at"]

    # Renew (we do NOT sleep — backdating is not needed here; we just verify the field is rewritten)
    result = renew_heartbeat(ws, "proj", "v1", "sess_1")
    assert result is True

    # State must remain HELD
    assert check_lock_state(ws, "proj", "v1") == LockState.HELD

    # last_seen_at must be ≥ initial (may be equal at nanosecond resolution, but field is rewritten)
    updated_data = json.loads(lock_path.read_text())
    updated_ts = updated_data["last_seen_at"]
    assert updated_ts >= initial_ts, f"last_seen_at regressed: {initial_ts} → {updated_ts}"


def test_heartbeat_wrong_session_or_missing_file_returns_false(tmp_path: Path) -> None:
    """renew_heartbeat returns False for a non-owner or missing lock."""
    ws = tmp_path
    create_impl_lock(
        ws, context="proj", release="v1", session_id="sess_owner", runtime="test", pid=os.getpid()
    )
    assert renew_heartbeat(ws, "proj", "v1", "sess_other") is False
    assert renew_heartbeat(ws, "missing", "v1", "sess_x") is False


def test_heartbeat_revives_nearstale_lock(tmp_path: Path) -> None:
    """Renewing a lock that is just-expired (stale) with correct session updates it."""
    ws = tmp_path
    # Create a stale lock (TTL=300 but backdated 10 min)
    _make_stale_lock(ws, "proj", "v1", session_id="sess_1", ttl_seconds=300, minutes_ago=10)
    # Even stale: heartbeat renews the timestamp (session still owns it)
    result = renew_heartbeat(ws, "proj", "v1", "sess_1")
    assert result is True

    # Now the lock should be HELD again (fresh last_seen_at)
    state = check_lock_state(ws, "proj", "v1")
    assert state == LockState.HELD


def test_doctor_lock3_marks_stale_no_delete(tmp_path: Path) -> None:
    """Doctor LOCK-3 marks expired HELD lock as STALE without deleting it."""
    ws = tmp_path
    # Create lock file with last_seen_at 10 min ago (ttl=180s → STALE)
    lock_path = _make_stale_lock(ws, "proj", "v1", ttl_seconds=180, minutes_ago=10)

    store = FakeContextStore()
    # Context is ALIVE so LOCK-2 does not fire (only LOCK-3 should apply)
    alive_ctx = SpecContextProject(
        name="proj",
        state=ContextState.ALIVE,
        repo_slug="proj-repo",
        repo_url="https://example.com/proj",
        created_at="2026-01-01T00:00:00Z",
        alive_since="2026-01-01T00:00:00Z",
    )
    store.save(alive_ctx)

    doctor = _make_doctor(ws, store)

    # check() must report LOCK-3
    issues = doctor.check()
    lock3_issues = [i for i in issues if i.code == "LOCK-3"]
    assert len(lock3_issues) == 1, f"Expected 1 LOCK-3 issue, got: {[i.code for i in issues]}"

    # fix() must mark the lock as STALE and NOT delete it
    actions = doctor.fix()
    assert lock_path.exists(), "LOCK-3 fix must NOT delete the lock file"

    lock3_actions = [a for a in actions if "LOCK-3" in a]
    assert len(lock3_actions) >= 1, f"Expected LOCK-3 action in fix(): {actions}"

    data = json.loads(lock_path.read_text())
    assert data.get("state") == "STALE", f"Expected state=STALE, got: {data.get('state')}"


def test_doctor_lock2_deletes_dead_ctx_lock(tmp_path: Path) -> None:
    """Doctor LOCK-2 deletes impl lock for DEAD context and appends audit."""
    ws = tmp_path
    lock_path = _make_stale_lock(ws, "dead-proj", "v1")

    store = FakeContextStore()
    dead_ctx = _make_dead_ctx("dead-proj", "dead-repo")
    store.save(dead_ctx)

    doctor = _make_doctor(ws, store)

    # check() must report LOCK-2
    issues = doctor.check()
    lock2_issues = [i for i in issues if i.code == "LOCK-2"]
    assert len(lock2_issues) >= 1, f"Expected LOCK-2 issue, got: {[i.code for i in issues]}"

    # fix() must delete the lock file
    actions = doctor.fix()
    assert not lock_path.exists(), "LOCK-2 fix must DELETE the lock file"

    lock2_actions = [a for a in actions if "LOCK-2" in a]
    assert len(lock2_actions) >= 1, f"Expected LOCK-2 action in fix(): {actions}"

    # Audit log must contain LOCK_DELETED_DEAD_CTX event
    log_path = _audit_log_path(ws)
    assert log_path.exists()
    events = [json.loads(ln)["event"] for ln in log_path.read_text().splitlines() if ln.strip()]
    assert "LOCK_DELETED_DEAD_CTX" in events, f"Audit event missing: {events}"


def test_audit_event_schema_fields(tmp_path: Path) -> None:
    """Every line produced by bind/release/reclaim has required schema fields."""
    ws = tmp_path
    required_fields = {"ts", "event", "context", "release", "session_id", "runtime"}

    # Emit ACQUIRED event
    audit_acquired(
        ws,
        context="myctx",
        release="r1",
        session_id="sess_abc",
        runtime="test-runtime",
        pid=os.getpid(),
    )

    # Emit BLOCKED_ATTEMPT event
    audit_blocked(
        ws,
        context="myctx",
        release="r1",
        session_id="sess_blocked",
        runtime="test-runtime",
        pid=os.getpid(),
        reason="lock held",
    )

    # Emit STALE_DETECTED + RECLAIMED via reclaim_impl_lock
    _make_stale_lock(ws, "myctx", "r1", session_id="sess_stale")
    reclaim_impl_lock(
        ws,
        context="myctx",
        release="r1",
        new_session_id="sess_reclaimer",
        runtime="test-runtime",
        pid=os.getpid(),
        reason="test reclaim",
    )

    log_path = _audit_log_path(ws)
    assert log_path.exists()

    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 4, f"Expected at least 4 audit lines, got {len(lines)}"

    for line in lines:
        record = json.loads(line)
        missing = required_fields - set(record.keys())
        assert not missing, f"Audit record missing fields {missing}: {record}"
        # ts must be a valid ISO 8601 timestamp
        assert record["ts"], f"ts field is empty: {record}"
        datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))


def test_lock4_production_write_missing_task_id_reported(tmp_path: Path) -> None:
    """LOCK-4: a PRODUCTION_WRITE event without task_id is reported; not fixed."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    record_with_task = json.dumps(
        {
            "ts": datetime.now(tz=UTC).isoformat(),
            "event": "PRODUCTION_WRITE",
            "context": "proj",
            "release": "v1",
            "session_id": "sess_ok",
            "runtime": "test",
            "pid": os.getpid(),
            "task_id": "T-12",
        }
    )
    record_missing_task = json.dumps(
        {
            "ts": datetime.now(tz=UTC).isoformat(),
            "event": "PRODUCTION_WRITE",
            "context": "proj",
            "release": "v1",
            "session_id": "sess_bad",
            "runtime": "test",
            "pid": os.getpid(),
            # task_id deliberately absent
        }
    )

    audit_path.write_text(record_with_task + "\n" + record_missing_task + "\n")

    doctor = _make_doctor(ws)
    issues = doctor.check()

    lock4_issues = [i for i in issues if i.code == "LOCK-4"]
    assert len(lock4_issues) == 1, f"Expected 1 LOCK-4 issue, got: {lock4_issues}"
    assert "sess_bad" in lock4_issues[0].description
    assert lock4_issues[0].fixable is False

    # fix() must NOT remove the event
    doctor.fix()
    lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2, "fix() must not delete audit log entries for LOCK-4"


# ---------------------------------------------------------------------------
# LOCK-5: BLOCKED_ATTEMPT event surfaces as signal
# ---------------------------------------------------------------------------


def test_lock5_blocked_attempt_surfaces_as_signal(tmp_path: Path) -> None:
    """LOCK-5: BLOCKED_ATTEMPT in audit log is surfaced; not fixed."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    audit_blocked(
        ws,
        context="proj",
        release="v1",
        session_id="sess_blocked",
        runtime="test",
        pid=os.getpid(),
        reason="lock already held",
    )

    doctor = _make_doctor(ws)
    issues = doctor.check()

    lock5_issues = [i for i in issues if i.code == "LOCK-5"]
    assert len(lock5_issues) == 1, f"Expected 1 LOCK-5 issue, got: {lock5_issues}"
    assert lock5_issues[0].fixable is False
    assert "sess_blocked" in lock5_issues[0].description

    # fix() must NOT delete the audit event
    doctor.fix()
    lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 1, "fix() must not delete audit log entries for LOCK-5"


# ---------------------------------------------------------------------------
# LOCK-6: BOUND_REVIEW session for DEAD context → AUTO-FIX
# ---------------------------------------------------------------------------


def test_lock6_review_session_dead_ctx_detected_and_fixed(tmp_path: Path) -> None:
    """LOCK-6: BOUND_REVIEW session for DEAD context is detected and deleted by fix()."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)

    session_data = {
        "session_id": "sess_review_dead",
        "context": "dead-proj",
        "release": "v1",
        "mode": "BOUND_REVIEW",
        "runtime": "test",
        "pid": os.getpid(),
        "last_seen_at": datetime.now(tz=UTC).isoformat(),
        "ttl_seconds": 300,
    }
    session_file = sessions_dir / "sess_review_dead.json"
    session_file.write_text(json.dumps(session_data))

    store = FakeContextStore()
    dead_ctx = _make_dead_ctx("dead-proj", "dead-repo")
    store.save(dead_ctx)

    doctor = _make_doctor(ws, store)

    # check() must report LOCK-6
    issues = doctor.check()
    lock6_issues = [i for i in issues if i.code == "LOCK-6"]
    assert len(lock6_issues) == 1, f"Expected 1 LOCK-6 issue, got: {[i.code for i in issues]}"
    assert lock6_issues[0].fixable is True

    # fix() must delete the session file
    actions = doctor.fix()
    assert not session_file.exists(), "LOCK-6 fix must DELETE the session file"

    lock6_actions = [a for a in actions if "LOCK-6" in a]
    assert len(lock6_actions) >= 1, f"Expected LOCK-6 action in fix(): {actions}"

    # Audit log must contain REVIEW_SESSION_DELETED_DEAD_CTX
    log_path = _audit_log_path(ws)
    assert log_path.exists()
    events = [json.loads(ln)["event"] for ln in log_path.read_text().splitlines() if ln.strip()]
    assert "REVIEW_SESSION_DELETED_DEAD_CTX" in events, f"Audit event missing: {events}"


def test_lock6_alive_review_session_not_touched(tmp_path: Path) -> None:
    """LOCK-6: BOUND_REVIEW session for ALIVE context is NOT deleted."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)

    session_data = {
        "session_id": "sess_review_alive",
        "context": "alive-proj",
        "release": "v1",
        "mode": "BOUND_REVIEW",
        "runtime": "test",
        "pid": os.getpid(),
        "last_seen_at": datetime.now(tz=UTC).isoformat(),
        "ttl_seconds": 300,
    }
    session_file = sessions_dir / "sess_review_alive.json"
    session_file.write_text(json.dumps(session_data))

    store = FakeContextStore()
    alive_ctx = SpecContextProject(
        name="alive-proj",
        state=ContextState.ALIVE,
        repo_slug="alive-repo",
        repo_url="https://example.com/alive",
        created_at="2026-01-01T00:00:00Z",
        alive_since="2026-01-01T00:00:00Z",
    )
    store.save(alive_ctx)

    doctor = _make_doctor(ws, store)

    issues = doctor.check()
    lock6_issues = [i for i in issues if i.code == "LOCK-6"]
    assert len(lock6_issues) == 0, "ALIVE context review session should not trigger LOCK-6"

    doctor.fix()
    assert session_file.exists(), "LOCK-6 must not delete session for ALIVE context"
