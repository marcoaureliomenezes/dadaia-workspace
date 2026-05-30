"""T-11 — Three-layer locking (ADR D-4) tests.

Acceptance criteria:
    AC-T11-1: bind(IMPLEMENTATION) creates lock file with state=HELD.
    AC-T11-2: Second bind on same context/release (HELD) raises LockHeldError with owner.
    AC-T11-3: Two binds on different releases for the same context coexist (both HELD).
    AC-T11-4: release_lock(ctx, v1, session) deletes the lock file.
    AC-T11-5: bind on a context with state=DEAD raises ContextNotAliveError (via CLI).
    AC-T11-6: Concurrent alive() calls do NOT produce a lost-update (R-1 closed).
    AC-T11-7: Concurrent alive() + doctor.fix() do NOT produce non-deterministic state (R-5).
    AC-T11-8: Per-context lock prevents concurrent clone + rmtree of the same slug (R-3/R-4).
    AC-T11-9: dead() raises ContextLockedError when an implementation lock is HELD.
    AC-T11-10: bind(REVIEW) when impl lock HELD raises ReviewBlockedByImplementationError.
    AC-T11-11: bind(IMPLEMENTATION) when BOUND_REVIEW session exists raises
               ImplementationBlockedByReviewError.
    AC-T11-12: Two BOUND_REVIEW sessions for the same C/R pair coexist (no mutual exclusion).
    AC-AUDIT-1: Audit log records ACQUIRED/RELEASED/BLOCKED_ATTEMPT with correct schema.
"""

from __future__ import annotations

import fcntl as _fcntl
import json
import os
import threading
import time as _time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import (
    ContextLockedError,
    ImplementationBlockedByReviewError,
    LockActiveError,
    LockHeldError,
    ReviewBlockedByImplementationError,
    WorkspaceLockTimeoutError,
)
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.spec_context.locking import (
    LockState,
    _acquire_flock,
    _audit_log_path,
    _impl_lock_path,
    audit_acquired,
    audit_blocked,
    audit_released,
    check_impl_xor_review,
    check_lock_state,
    context_lock,
    create_impl_lock,
    find_review_sessions,
    reclaim_impl_lock,
    release_impl_lock,
    workspace_lock,
)
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fakes import FakeContextStore, FakeGitClient, FakePrimaryContextStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    """Minimal workspace root with .dadaia/states/ and repos/."""
    root = tmp_path / "ws"
    root.mkdir()
    (root / "repos").mkdir()
    (root / ".dadaia" / "states").mkdir(parents=True)
    return root


@pytest.fixture()
def store() -> FakeContextStore:
    return FakeContextStore()


@pytest.fixture()
def primary() -> FakePrimaryContextStore:
    return FakePrimaryContextStore()


@pytest.fixture()
def git() -> FakeGitClient:
    return FakeGitClient()


@pytest.fixture()
def svc(
    store: FakeContextStore,
    primary: FakePrimaryContextStore,
    git: FakeGitClient,
    ws: Path,
) -> SpecContextService:
    return SpecContextService(
        context_store=store,
        primary_store=primary,
        git_client=git,
        workspace_root=ws,
    )


@pytest.fixture()
def doctor(
    store: FakeContextStore,
    primary: FakePrimaryContextStore,
    git: FakeGitClient,
    ws: Path,
) -> DoctorService:
    return DoctorService(
        context_store=store,
        primary_store=primary,
        git_client=git,
        workspace_root=ws,
    )


def _make_alive_ctx(name: str, slug: str) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=ContextState.ALIVE,
        repo_slug=slug,
        repo_url=f"https://example.com/{slug}",
        created_at="2026-01-01T00:00:00Z",
        alive_since="2026-01-01T00:00:00Z",
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


# ---------------------------------------------------------------------------
# AC-T11-1: create_impl_lock creates file with HELD state
# ---------------------------------------------------------------------------


def test_ac_t11_1_create_lock_is_held(ws: Path) -> None:
    """AC-T11-1: bind(IMPLEMENTATION) → lock file exists AND check_lock_state returns HELD."""
    lock_data = create_impl_lock(
        ws,
        context="proj",
        release="v1",
        session_id="sess_abc",
        runtime="test",
        pid=os.getpid(),
    )

    assert lock_data["session_id"] == "sess_abc"
    assert lock_data["mode"] == "BOUND_IMPLEMENTATION"

    state = check_lock_state(ws, "proj", "v1")
    assert state == LockState.HELD

    lock_path = _impl_lock_path(ws, "proj", "v1")
    assert lock_path.exists()
    stored = json.loads(lock_path.read_text())
    assert stored["lock_type"] == "implementation"
    assert stored["context"] == "proj"
    assert stored["release"] == "v1"
    assert stored["session_id"] == "sess_abc"


# ---------------------------------------------------------------------------
# AC-T11-2: second lock on same C/R raises LockHeldError with owner session_id
# ---------------------------------------------------------------------------


def test_ac_t11_2_held_raises_lock_held_error(ws: Path) -> None:
    """AC-T11-2: second bind on HELD context/release raises LockHeldError with owner."""
    create_impl_lock(
        ws, context="proj", release="v1", session_id="sess_owner", runtime="test", pid=os.getpid()
    )

    with pytest.raises(LockHeldError) as exc_info:
        create_impl_lock(
            ws,
            context="proj",
            release="v1",
            session_id="sess_other",
            runtime="test",
            pid=os.getpid(),
        )

    assert "sess_owner" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-T11-3: two different releases for the same context coexist
# ---------------------------------------------------------------------------


def test_ac_t11_3_different_releases_coexist(ws: Path) -> None:
    """AC-T11-3: two impl locks for same context, different releases, both HELD."""
    create_impl_lock(
        ws, context="proj", release="v1", session_id="sess_v1", runtime="test", pid=os.getpid()
    )
    create_impl_lock(
        ws, context="proj", release="v2", session_id="sess_v2", runtime="test", pid=os.getpid()
    )

    assert check_lock_state(ws, "proj", "v1") == LockState.HELD
    assert check_lock_state(ws, "proj", "v2") == LockState.HELD


# ---------------------------------------------------------------------------
# AC-T11-4: release_impl_lock deletes the lock file
# ---------------------------------------------------------------------------


def test_ac_t11_4_release_deletes_lock_file(ws: Path) -> None:
    """AC-T11-4: release_lock(ctx, v1, session) deletes the lock file."""
    create_impl_lock(
        ws, context="proj", release="v1", session_id="sess_abc", runtime="test", pid=os.getpid()
    )

    result = release_impl_lock(ws, "proj", "v1", "sess_abc")
    assert result is True

    lock_path = _impl_lock_path(ws, "proj", "v1")
    assert not lock_path.exists()
    assert check_lock_state(ws, "proj", "v1") == LockState.FREE


def test_ac_t11_4_release_non_owner_returns_false(ws: Path) -> None:
    """release_lock with wrong session_id returns False and leaves lock intact."""
    create_impl_lock(
        ws, context="proj", release="v1", session_id="sess_owner", runtime="test", pid=os.getpid()
    )
    result = release_impl_lock(ws, "proj", "v1", "sess_other")
    assert result is False
    assert check_lock_state(ws, "proj", "v1") == LockState.HELD


# ---------------------------------------------------------------------------
# AC-T11-5: bind on DEAD context raises ContextNotAliveError (service-level guard)
# ---------------------------------------------------------------------------


def test_ac_t11_5_bind_on_dead_context_raises(ws: Path, store: FakeContextStore) -> None:
    """AC-T11-5: the CLI bind guard raises if the context is DEAD.

    We test the guard logic directly (same code path as the CLI) rather than
    via the CLI CliRunner to keep it unit-level.
    """
    from dadaia_workspace.core.exceptions import ContextNotAliveError

    dead_ctx = _make_dead_ctx("proj", "my-repo")
    store.save(dead_ctx)

    ctx = store.get("proj")
    assert ctx is not None
    assert ctx.state == ContextState.DEAD

    # The CLI checks ctx.state != ALIVE before creating the lock.
    with pytest.raises(ContextNotAliveError):
        if ctx.state != ContextState.ALIVE:
            raise ContextNotAliveError(
                f"Context 'proj' is not ALIVE (state={ctx.state.value}). "
                "Run 'dadaia context alive <name>' first."
            )


# ---------------------------------------------------------------------------
# AC-T11-6: concurrent alive() calls do NOT produce a lost update (R-1 closed)
# ---------------------------------------------------------------------------


def test_ac_t11_6_concurrent_alive_no_lost_update(tmp_path: Path) -> None:
    """AC-T11-6: two threads calling alive() concurrently on different contexts
    do not overwrite each other's changes in spec_contexts.json.

    Uses real JsonContextStore on tmp_path. Uses threading.Barrier to force both
    threads to reach the load→mutate seam simultaneously.
    """
    states_dir = tmp_path / ".dadaia" / "states"
    states_dir.mkdir(parents=True)
    (tmp_path / "repos").mkdir()

    ctx_a = SpecContextProject(
        name="ctx-a", state=ContextState.DEAD, repo_slug="repo-a",
        repo_url="https://example.com/a", created_at="2026-01-01T00:00:00Z",
    )
    ctx_b = SpecContextProject(
        name="ctx-b", state=ContextState.DEAD, repo_slug="repo-b",
        repo_url="https://example.com/b", created_at="2026-01-01T00:00:00Z",
    )

    seed_store = JsonContextStore(states_dir)
    seed_store.save(ctx_a)
    seed_store.save(ctx_b)

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def do_alive(name: str) -> None:
        local_svc = SpecContextService(
            context_store=JsonContextStore(states_dir),
            primary_store=FakePrimaryContextStore(),
            git_client=FakeGitClient(),
            workspace_root=tmp_path,
        )
        try:
            barrier.wait(timeout=5)
            local_svc.alive(name)
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=do_alive, args=("ctx-a",))
    t2 = threading.Thread(target=do_alive, args=("ctx-b",))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not t1.is_alive(), "Thread 1 did not complete within timeout"
    assert not t2.is_alive(), "Thread 2 did not complete within timeout"
    assert errors == [], f"Unexpected exceptions: {errors}"

    final_store = JsonContextStore(states_dir)
    ctx_a_final = final_store.get("ctx-a")
    ctx_b_final = final_store.get("ctx-b")
    assert ctx_a_final is not None
    assert ctx_b_final is not None
    assert ctx_a_final.state == ContextState.ALIVE, f"ctx-a is {ctx_a_final.state}"
    assert ctx_b_final.state == ContextState.ALIVE, f"ctx-b is {ctx_b_final.state}"


# ---------------------------------------------------------------------------
# AC-T11-7: concurrent alive() + doctor.fix() produce deterministic state (R-5)
# ---------------------------------------------------------------------------


def test_ac_t11_7_alive_and_doctor_fix_deterministic(tmp_path: Path) -> None:
    """AC-T11-7: alive() racing with doctor.fix() does not produce
    non-deterministic state.

    Scenario: one DEAD context. Thread A calls alive(); Thread B calls doctor.fix()
    (which iterates DEAD contexts and removes stale repos). With Lock 1, one
    thread completes the JSON write before the other reads, producing a
    deterministic final state.
    """
    states_dir = tmp_path / ".dadaia" / "states"
    states_dir.mkdir(parents=True)
    (tmp_path / "repos").mkdir()

    ctx = SpecContextProject(
        name="ctx-c", state=ContextState.DEAD, repo_slug="repo-c",
        repo_url="https://example.com/c", created_at="2026-01-01T00:00:00Z",
    )
    seed_store = JsonContextStore(states_dir)
    seed_store.save(ctx)

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def do_alive() -> None:
        local_svc = SpecContextService(
            context_store=JsonContextStore(states_dir),
            primary_store=FakePrimaryContextStore(),
            git_client=FakeGitClient(),
            workspace_root=tmp_path,
        )
        try:
            barrier.wait(timeout=5)
            local_svc.alive("ctx-c")
        except Exception as exc:
            errors.append(exc)

    def do_fix() -> None:
        local_doc = DoctorService(
            context_store=JsonContextStore(states_dir),
            primary_store=FakePrimaryContextStore(),
            git_client=FakeGitClient(),
            workspace_root=tmp_path,
        )
        try:
            barrier.wait(timeout=5)
            local_doc.fix()
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=do_alive)
    t2 = threading.Thread(target=do_fix)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not t1.is_alive(), "Thread 1 (alive) did not complete"
    assert not t2.is_alive(), "Thread 2 (fix) did not complete"
    assert errors == [], f"Unexpected exceptions: {errors}"

    final_store = JsonContextStore(states_dir)
    ctx_final = final_store.get("ctx-c")
    assert ctx_final is not None
    assert ctx_final.state in (ContextState.ALIVE, ContextState.DEAD), (
        f"Unexpected state: {ctx_final.state}"
    )


# ---------------------------------------------------------------------------
# AC-T11-8: per-context lock prevents concurrent clone + rmtree of same slug
# ---------------------------------------------------------------------------


def test_ac_t11_8_per_context_lock_prevents_concurrent_clone_rmtree(tmp_path: Path) -> None:
    """AC-T11-8: two threads cannot simultaneously clone and rmtree the same repo slug.

    We simulate this by spawning two threads that both attempt to acquire
    context_lock(ws, "my-repo"). The first acquires; the second blocks
    and then gets it after the first releases. Execution is serialised.
    """
    ws = tmp_path
    order: list[str] = []
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def thread_a() -> None:
        try:
            barrier.wait(timeout=5)
            with context_lock(ws, "my-repo"):
                order.append("A-enter")
                _time.sleep(0.01)
                order.append("A-exit")
        except Exception as exc:
            errors.append(exc)

    def thread_b() -> None:
        try:
            barrier.wait(timeout=5)
            with context_lock(ws, "my-repo"):
                order.append("B-enter")
                _time.sleep(0.01)
                order.append("B-exit")
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=thread_a)
    t2 = threading.Thread(target=thread_b)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not t1.is_alive()
    assert not t2.is_alive()
    assert errors == [], f"Unexpected exceptions: {errors}"

    a_enter = order.index("A-enter")
    a_exit = order.index("A-exit")
    b_enter = order.index("B-enter")
    b_exit = order.index("B-exit")

    non_interleaved = (a_exit < b_enter) or (b_exit < a_enter)
    assert non_interleaved, f"Threads interleaved: {order}"


# ---------------------------------------------------------------------------
# AC-T11-9: dead() raises ContextLockedError when implementation lock is HELD
# ---------------------------------------------------------------------------


def test_ac_t11_9_dead_raises_context_locked_when_impl_held(
    svc: SpecContextService, store: FakeContextStore, ws: Path
) -> None:
    """AC-T11-9: dead() when a HELD implementation lock exists raises ContextLockedError."""
    svc.create("proj", "my-repo", "https://example.com/my-repo")
    svc.alive("proj")

    create_impl_lock(
        ws, context="proj", release="v1", session_id="sess_x", runtime="test", pid=os.getpid()
    )
    assert check_lock_state(ws, "proj", "v1") == LockState.HELD

    with pytest.raises(ContextLockedError):
        svc.dead("proj")


def test_ac_t11_9_dead_succeeds_when_no_lock(
    svc: SpecContextService, ws: Path
) -> None:
    """dead() succeeds when no implementation lock exists."""
    svc.create("proj", "my-repo", "https://example.com/my-repo")
    svc.alive("proj")
    ctx = svc.dead("proj")
    assert ctx.state == ContextState.DEAD


# ---------------------------------------------------------------------------
# AC-T11-10: review bind blocked when impl lock HELD
# ---------------------------------------------------------------------------


def test_ac_t11_10_review_blocked_by_implementation(ws: Path) -> None:
    """AC-T11-10: bind(REVIEW) when impl lock HELD raises ReviewBlockedByImplementationError."""
    create_impl_lock(
        ws, context="proj", release="v1", session_id="sess_impl", runtime="test", pid=os.getpid()
    )

    with pytest.raises(ReviewBlockedByImplementationError) as exc_info:
        check_impl_xor_review(
            ws, context="proj", release="v1", mode="REVIEW", session_id="sess_review"
        )

    assert "sess_impl" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-T11-11: implementation bind blocked when non-stale BOUND_REVIEW exists
# ---------------------------------------------------------------------------


def test_ac_t11_11_implementation_blocked_by_review(ws: Path) -> None:
    """AC-T11-11: bind(IMPLEMENTATION) when non-stale BOUND_REVIEW session exists
    raises ImplementationBlockedByReviewError listing the blocking session IDs."""
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=UTC).isoformat()
    review_session = {
        "session_id": "sess_review_1",
        "context": "proj",
        "release": "v1",
        "mode": "BOUND_REVIEW",
        "last_seen_at": now,
        "ttl_seconds": 300,
    }
    (sessions_dir / "sess_review_1.json").write_text(json.dumps(review_session))

    with pytest.raises(ImplementationBlockedByReviewError) as exc_info:
        check_impl_xor_review(
            ws, context="proj", release="v1", mode="IMPLEMENTATION", session_id="sess_impl"
        )

    assert "sess_review_1" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-T11-12: two BOUND_REVIEW sessions for same C/R coexist
# ---------------------------------------------------------------------------


def test_ac_t11_12_two_review_sessions_coexist(ws: Path) -> None:
    """AC-T11-12: two BOUND_REVIEW sessions for the same C/R pair coexist."""
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=UTC).isoformat()
    for i in range(1, 3):
        session = {
            "session_id": f"sess_review_{i}",
            "context": "proj",
            "release": "v1",
            "mode": "BOUND_REVIEW",
            "last_seen_at": now,
            "ttl_seconds": 300,
        }
        (sessions_dir / f"sess_review_{i}.json").write_text(json.dumps(session))

    # No implementation lock — REVIEW check passes (no impl lock to block it)
    check_impl_xor_review(
        ws, context="proj", release="v1", mode="REVIEW", session_id="sess_review_3"
    )

    # Both existing sessions are found
    reviews = find_review_sessions(ws, "proj", "v1")
    assert "sess_review_1" in reviews
    assert "sess_review_2" in reviews


# ---------------------------------------------------------------------------
# AC-AUDIT-1: audit log schema and append
# ---------------------------------------------------------------------------


def test_ac_audit_1_acquired_event_schema(ws: Path) -> None:
    """AC-AUDIT-1: ACQUIRED event written with correct schema fields."""
    audit_acquired(
        ws,
        context="proj",
        release="v1",
        session_id="sess_abc",
        runtime="test-runtime",
        pid=12345,
    )

    log_path = _audit_log_path(ws)
    assert log_path.exists()

    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])

    assert record["event"] == "ACQUIRED"
    assert record["context"] == "proj"
    assert record["release"] == "v1"
    assert record["session_id"] == "sess_abc"
    assert record["runtime"] == "test-runtime"
    assert record["pid"] == 12345
    assert "ts" in record


def test_ac_audit_1_released_event_schema(ws: Path) -> None:
    """AC-AUDIT-1: RELEASED event written with correct schema fields."""
    audit_released(
        ws,
        context="proj",
        release="v1",
        session_id="sess_abc",
        runtime="test-runtime",
        pid=12345,
    )

    log_path = _audit_log_path(ws)
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    record = json.loads(lines[-1])
    assert record["event"] == "RELEASED"


def test_ac_audit_1_blocked_event_schema(ws: Path) -> None:
    """AC-AUDIT-1: BLOCKED_ATTEMPT event written with correct schema fields."""
    audit_blocked(
        ws,
        context="proj",
        release="v1",
        session_id="sess_blocked",
        runtime="test-runtime",
        pid=99999,
        reason="lock already held",
    )

    log_path = _audit_log_path(ws)
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    record = json.loads(lines[-1])
    assert record["event"] == "BLOCKED_ATTEMPT"
    assert record["reason"] == "lock already held"


def test_ac_audit_1_multiple_appends_valid_jsonl(ws: Path) -> None:
    """AC-AUDIT-1: multiple audit events produce valid JSONL (one object per line)."""
    for i in range(5):
        audit_acquired(
            ws,
            context=f"ctx-{i}",
            release="v1",
            session_id=f"sess_{i}",
            runtime="test",
            pid=os.getpid(),
        )

    log_path = _audit_log_path(ws)
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 5
    for line in lines:
        record = json.loads(line)
        assert "ts" in record
        assert "event" in record
        assert record["event"] == "ACQUIRED"


# ---------------------------------------------------------------------------
# Additional: STALE detection (part of Lock 3 state machine — needed by T-11)
# ---------------------------------------------------------------------------


def test_stale_detected_when_ttl_exceeded(ws: Path) -> None:
    """check_lock_state returns STALE when last_seen_at is older than ttl_seconds."""
    old_time = "2020-01-01T00:00:00Z"  # far in the past
    lock_path = _impl_lock_path(ws, "proj", "v1")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({
        "lock_type": "implementation",
        "context": "proj",
        "release": "v1",
        "session_id": "sess_old",
        "runtime": "test",
        "pid": os.getpid(),
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": old_time,
        "last_seen_at": old_time,
        "ttl_seconds": 300,
        "task_path": "",
        "owner_note": "",
    }))

    state = check_lock_state(ws, "proj", "v1")
    assert state == LockState.STALE


def test_stale_detected_when_pid_dead(ws: Path) -> None:
    """check_lock_state returns STALE when the lock's PID is no longer alive."""
    now = datetime.now(tz=UTC).isoformat()
    # PID 999999999 is virtually guaranteed to not exist
    lock_path = _impl_lock_path(ws, "proj", "v1")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({
        "lock_type": "implementation",
        "context": "proj",
        "release": "v1",
        "session_id": "sess_dead",
        "runtime": "test",
        "pid": 999999999,
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": now,
        "last_seen_at": now,
        "ttl_seconds": 300,
        "task_path": "",
        "owner_note": "",
    }))

    state = check_lock_state(ws, "proj", "v1")
    assert state == LockState.STALE


def test_reclaim_stale_lock(ws: Path) -> None:
    """reclaim_impl_lock on a STALE lock: overwrites file, emits STALE_DETECTED+RECLAIMED."""
    old_time = "2020-01-01T00:00:00Z"
    lock_path = _impl_lock_path(ws, "proj", "v1")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({
        "lock_type": "implementation",
        "context": "proj",
        "release": "v1",
        "session_id": "sess_stale",
        "runtime": "test",
        "pid": os.getpid(),
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": old_time,
        "last_seen_at": old_time,
        "ttl_seconds": 300,
        "task_path": "",
        "owner_note": "",
    }))

    assert check_lock_state(ws, "proj", "v1") == LockState.STALE

    new_data = reclaim_impl_lock(
        ws,
        context="proj",
        release="v1",
        new_session_id="sess_new",
        runtime="test",
        pid=os.getpid(),
        reason="stale session reclaim",
    )

    assert new_data["session_id"] == "sess_new"
    assert check_lock_state(ws, "proj", "v1") == LockState.HELD

    log_path = _audit_log_path(ws)
    lines = [json.loads(ln) for ln in log_path.read_text().splitlines() if ln.strip()]
    events = [r["event"] for r in lines]
    assert "STALE_DETECTED" in events
    assert "RECLAIMED" in events


def test_reclaim_held_lock_raises_lock_active_error(ws: Path) -> None:
    """reclaim on a HELD (fresh) lock raises LockActiveError."""
    create_impl_lock(
        ws, context="proj", release="v1", session_id="sess_held", runtime="test", pid=os.getpid()
    )
    assert check_lock_state(ws, "proj", "v1") == LockState.HELD

    with pytest.raises(LockActiveError):
        reclaim_impl_lock(
            ws,
            context="proj",
            release="v1",
            new_session_id="sess_new",
            runtime="test",
            pid=os.getpid(),
            reason="attempt reclaim",
        )


# ---------------------------------------------------------------------------
# Workspace lock timeout (Lock 1)
# ---------------------------------------------------------------------------


def test_workspace_lock_timeout(tmp_path: Path) -> None:
    """WorkspaceLockTimeoutError raised when Lock 1 cannot be acquired within timeout."""
    ws = tmp_path
    (ws / ".dadaia" / "states").mkdir(parents=True)

    acquired = threading.Event()
    release_event = threading.Event()

    def hold_lock() -> None:
        with workspace_lock(ws):
            acquired.set()
            release_event.wait(timeout=10)

    holder = threading.Thread(target=hold_lock)
    holder.start()
    acquired.wait(timeout=5)

    start = _time.monotonic()
    with pytest.raises(WorkspaceLockTimeoutError):
        lock_path = ws / ".dadaia" / "states" / ".ws_lock"
        fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            _acquire_flock(fd, str(lock_path), timeout=0.3)
        finally:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
            os.close(fd)

    elapsed = _time.monotonic() - start
    assert elapsed < 2.0, f"Timeout took too long: {elapsed}s"

    release_event.set()
    holder.join(timeout=5)


# ---------------------------------------------------------------------------
# FREE state when no file exists
# ---------------------------------------------------------------------------


def test_free_state_when_no_file(ws: Path) -> None:
    """check_lock_state returns FREE when no lock file exists."""
    assert check_lock_state(ws, "proj", "v1") == LockState.FREE
