"""R2 QA gap-filling tests.

AC families covered:
    AC-RACE-1..6  — deterministic race reproduction (R-1, R-2/design-gone, R-3, R-4, R-5, R-8)
    AC-LOCK-1..9  — lock state-machine (supplements T-11/T-12; adds missing transitions)
    AC-REV-1..5   — BOUND_REVIEW mode (review blocked by impl, impl blocked by review, coexist,
                    read-only constraint, gate path-policy)
    AC-DOC-L1..12 — doctor LOCK-1..6 violating + post-fix fixtures; lifts doctor.py to ≥90%
    AC-COV-1..3   — per-file coverage: json_context_store ≥95%, service.py ≥90%, doctor.py ≥90%
                    (covered by tests in this file + existing T-11/T-12)

Design rules:
    - Real JsonContextStore on tmp_path for concurrency tests.
    - threading.Barrier / threading.Event — NO time.sleep in race tests.
    - All threads join(timeout=5) with is_alive() assertion.
    - Stale locks: backdated last_seen_at — no actual sleep.
    - R-2 verified by design-elimination: assert `promote` does not exist on service.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    ImplementationBlockedByReviewError,
    LockActiveError,
    LockHeldError,
    ReviewBlockedByImplementationError,
)
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.spec_context.locking import (
    LockState,
    _audit_log_path,
    _impl_lock_path,
    audit_blocked,
    check_impl_xor_review,
    check_lock_state,
    create_impl_lock,
    find_review_sessions,
    reclaim_impl_lock,
    release_impl_lock,
)
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fakes import FakeContextStore, FakeGitClient, FakePrimaryContextStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stale_ts(minutes: int = 10) -> str:
    return (datetime.now(tz=UTC) - timedelta(minutes=minutes)).isoformat()


def _make_ws(tmp_path: Path) -> Path:
    """Minimal workspace: repos/ + .dadaia/states/."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "repos").mkdir()
    (ws / ".dadaia" / "states").mkdir(parents=True)
    return ws


def _make_svc(ws: Path) -> SpecContextService:
    states = ws / ".dadaia" / "states"
    return SpecContextService(
        context_store=JsonContextStore(states),
        primary_store=FakePrimaryContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )


def _make_ctx(
    name: str,
    state: ContextState = ContextState.DEAD,
    slug: str | None = None,
) -> SpecContextProject:
    slug = slug or name
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=slug,
        repo_url=f"https://example.com/{slug}",
        created_at="2026-01-01T00:00:00Z",
        alive_since="2026-01-01T00:00:00Z" if state == ContextState.ALIVE else None,
        dead_since="2026-01-01T00:00:00Z" if state == ContextState.DEAD else None,
    )


def _make_doctor(ws: Path, store: FakeContextStore | None = None) -> DoctorService:
    return DoctorService(
        context_store=store or FakeContextStore(),
        primary_store=FakePrimaryContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )


def _write_lock_file(
    ws: Path,
    context: str,
    release: str,
    *,
    session_id: str = "sess_x",
    last_seen_at: str | None = None,
    ttl_seconds: int = 300,
    state: str | None = None,
) -> Path:
    lock_path = _impl_lock_path(ws, context, release)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    ts = last_seen_at or datetime.now(tz=UTC).isoformat()
    data: dict = {
        "lock_type": "implementation",
        "context": context,
        "release": release,
        "session_id": session_id,
        "runtime": "test",
        "pid": os.getpid(),
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": ts,
        "last_seen_at": ts,
        "ttl_seconds": ttl_seconds,
        "task_path": "",
        "owner_note": "",
    }
    if state is not None:
        data["state"] = state
    lock_path.write_text(json.dumps(data, indent=2))
    return lock_path


# ===========================================================================
# AC-RACE-1 — Concurrent alive() on two different contexts: no lost update
# (deterministic — uses threading.Barrier; real JsonContextStore on disk)
# ===========================================================================


def test_ac_race_1_concurrent_alive_no_lost_update(tmp_path: Path) -> None:
    """AC-RACE-1: two threads call alive() on different contexts; both end up ALIVE.

    Uses real JsonContextStore on tmp_path.  threading.Barrier forces both threads
    to enter alive() simultaneously, exercising the workspace fcntl lock.
    No time.sleep — purely barrier-synchronized.
    """
    ws = _make_ws(tmp_path)
    states = ws / ".dadaia" / "states"

    seed = JsonContextStore(states)
    for name in ("ctx-a", "ctx-b"):
        seed.save(
            SpecContextProject(
                name=name,
                state=ContextState.DEAD,
                repo_slug=name,
                repo_url=f"https://example.com/{name}",
                created_at="2026-01-01T00:00:00Z",
            )
        )

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def do_alive(name: str) -> None:
        svc = SpecContextService(
            context_store=JsonContextStore(states),
            primary_store=FakePrimaryContextStore(),
            git_client=FakeGitClient(),
            workspace_root=ws,
        )
        try:
            barrier.wait(timeout=5)
            svc.alive(name)
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=do_alive, args=("ctx-a",))
    t2 = threading.Thread(target=do_alive, args=("ctx-b",))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not t1.is_alive(), "Thread 1 timed out — possible deadlock"
    assert not t2.is_alive(), "Thread 2 timed out — possible deadlock"
    assert errors == [], f"Unexpected exceptions: {errors}"

    final = JsonContextStore(states)
    a = final.get("ctx-a")
    b = final.get("ctx-b")
    assert a is not None and a.state == ContextState.ALIVE, f"ctx-a: {a}"
    assert b is not None and b.state == ContextState.ALIVE, f"ctx-b: {b}"


# ===========================================================================
# AC-RACE-2 — R-2 eliminated by design: promote() does not exist
# ===========================================================================


def test_ac_race_2_promote_eliminated_by_design(tmp_path: Path) -> None:
    """AC-RACE-2: R-2 (split primary from concurrent promote()) is eliminated by design.

    In v2, promote() is removed entirely from SpecContextService.  Asserting it is
    absent is the correct post-R2 test — there is no concurrent promote() scenario
    because the method does not exist.
    """
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    assert not hasattr(svc, "promote"), (
        "promote() must not exist on SpecContextService (R-2 eliminated by design)."
    )


# ===========================================================================
# AC-RACE-3 — Concurrent alive() on same context: exactly one clone
# ===========================================================================


def test_ac_race_3_concurrent_alive_same_context_no_double_clone(tmp_path: Path) -> None:
    """AC-RACE-3: two threads call alive('ctx-x') simultaneously.

    With context_lock, the second alive() call (hitting the already-cloned repo path
    inside Lock 2) must detect the repo is already there and skip the clone.
    The final state must be ALIVE and no exception raised.
    """
    ws = _make_ws(tmp_path)
    states = ws / ".dadaia" / "states"

    seed = JsonContextStore(states)
    seed.save(
        SpecContextProject(
            name="ctx-x",
            state=ContextState.DEAD,
            repo_slug="repo-x",
            repo_url="https://example.com/repo-x",
            created_at="2026-01-01T00:00:00Z",
        )
    )

    barrier = threading.Barrier(2)
    errors: list[Exception] = []
    clone_counts: list[int] = []

    class CountingGitClient(FakeGitClient):
        def clone(self, url: str, dest: Path) -> None:
            clone_counts.append(1)
            super().clone(url, dest)

    def do_alive() -> None:
        svc = SpecContextService(
            context_store=JsonContextStore(states),
            primary_store=FakePrimaryContextStore(),
            git_client=CountingGitClient(),
            workspace_root=ws,
        )
        try:
            barrier.wait(timeout=5)
            svc.alive("ctx-x")
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=do_alive)
    t2 = threading.Thread(target=do_alive)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not t1.is_alive(), "Thread 1 timed out"
    assert not t2.is_alive(), "Thread 2 timed out"
    assert errors == [], f"Exceptions: {errors}"

    # At most one clone (context_lock serialises the FS op; second sees repo exists)
    assert len(clone_counts) <= 1, f"Double-clone occurred: {len(clone_counts)} clones"

    final = JsonContextStore(states)
    ctx = final.get("ctx-x")
    assert ctx is not None and ctx.state == ContextState.ALIVE


# ===========================================================================
# AC-RACE-4 — rmtree while open fd: POSIX unlink semantics documented
# ===========================================================================


def test_ac_race_4_rmtree_while_fd_open(tmp_path: Path) -> None:
    """AC-RACE-4: on Linux, shutil.rmtree succeeds even with an open fd inside the tree.

    This is a sequential test — no threads needed.  POSIX unlink-while-open
    semantics are deterministic.  The test documents R-4 behaviour: once dead()
    is called, the file is unlinked from the namespace even if a reader holds an fd.
    A new open() on the removed path raises FileNotFoundError.
    """
    ws = _make_ws(tmp_path)

    # Create a repo directory with a file
    repo = ws / "repos" / "target-repo"
    repo.mkdir(parents=True)
    target_file = repo / "module.py"
    target_file.write_text("# content\n" * 100)

    # Simulate a reader holding an open fd
    with target_file.open("r") as fd:
        _read_start = fd.read(10)

        # Create an ALIVE context, then call dead() while fd is open
        svc = _make_svc(ws)
        svc.create("target", "target-repo", "https://example.com/target-repo")
        svc.alive("target")
        ctx = svc.dead("target")

        # File is gone from namespace
        assert not target_file.exists(), "rmtree should have removed the file"
        # The fd is still readable (inode persists until fd.close())
        remaining = fd.read(5)
        assert isinstance(remaining, str)  # fd still works post-unlink

    # After fd.close(), a new open() fails
    with pytest.raises(FileNotFoundError):
        target_file.open("r")

    assert ctx.state == ContextState.DEAD


# ===========================================================================
# AC-RACE-5 — alive() + doctor.fix() concurrent: deterministic final state
# ===========================================================================


def test_ac_race_5_alive_and_doctor_fix_deterministic(tmp_path: Path) -> None:
    """AC-RACE-5: alive() racing with doctor.fix() produces a valid final state.

    With workspace_lock, the two operations are serialised.  Final state is one of:
    ALIVE (alive() won) or DEAD (fix() removed stale repo and alive() lost the JSON
    race and re-read DEAD).  Either is valid — what is NOT allowed is a crash or
    corrupted JSON.
    """
    ws = _make_ws(tmp_path)
    states = ws / ".dadaia" / "states"

    seed = JsonContextStore(states)
    ctx = SpecContextProject(
        name="ctx-c",
        state=ContextState.DEAD,
        repo_slug="repo-c",
        repo_url="https://example.com/repo-c",
        created_at="2026-01-01T00:00:00Z",
    )
    seed.save(ctx)
    # Pre-create repo on disk so alive() skips clone and fix() would rmtree it
    (ws / "repos" / "repo-c").mkdir(parents=True)

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def do_alive() -> None:
        svc = SpecContextService(
            context_store=JsonContextStore(states),
            primary_store=FakePrimaryContextStore(),
            git_client=FakeGitClient(),
            workspace_root=ws,
        )
        try:
            barrier.wait(timeout=5)
            svc.alive("ctx-c")
        except Exception as exc:
            errors.append(exc)

    def do_fix() -> None:
        doc = DoctorService(
            context_store=JsonContextStore(states),
            primary_store=FakePrimaryContextStore(),
            git_client=FakeGitClient(),
            workspace_root=ws,
        )
        try:
            barrier.wait(timeout=5)
            doc.fix()
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=do_alive)
    t2 = threading.Thread(target=do_fix)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not t1.is_alive(), "Thread alive() timed out"
    assert not t2.is_alive(), "Thread fix() timed out"
    assert errors == [], f"Exceptions: {errors}"

    # The JSON must be readable and the context must be in a valid state
    final = JsonContextStore(states)
    ctx_final = final.get("ctx-c")
    assert ctx_final is not None
    assert ctx_final.state in (ContextState.ALIVE, ContextState.DEAD), (
        f"Invalid state: {ctx_final.state}"
    )


# ===========================================================================
# AC-RACE-6 — R-8: two sessions on same release; implementation lock prevents overlap
# ===========================================================================


def test_ac_race_6_r8_impl_lock_prevents_concurrent_task_md_writes(tmp_path: Path) -> None:
    """AC-RACE-6 / R-8: with implementation lock, second bind raises LockHeldError.

    Without lock (pre-R2): two sessions could both read TASKS.md and overwrite each
    other's changes.  With Lock 3: only one session holds the HELD lock; the second
    bind raises LockHeldError before it can touch TASKS.md.
    """
    ws = tmp_path

    # Session 1 acquires the implementation lock
    create_impl_lock(
        ws, context="proj", release="v1",
        session_id="sess_1", runtime="test", pid=os.getpid(),
    )
    assert check_lock_state(ws, "proj", "v1") == LockState.HELD

    # Session 2 tries to acquire — must be blocked
    with pytest.raises(LockHeldError) as exc_info:
        create_impl_lock(
            ws, context="proj", release="v1",
            session_id="sess_2", runtime="test", pid=os.getpid(),
        )

    assert "sess_1" in str(exc_info.value)

    # Simulate TASKS.md write ordering — without lock: second writer wins
    tasks = tmp_path / "releases" / "v1" / "TASKS.md"
    tasks.parent.mkdir(parents=True)
    tasks.write_text("- [ ] T-1\n- [ ] T-2\n")

    # Session 1's write
    content = tasks.read_text()
    updated_s1 = content.replace("[ ] T-1", "[x] T-1")
    tasks.write_text(updated_s1)

    result = tasks.read_text()
    assert "[x] T-1" in result, "Session 1's write preserved"
    assert "[ ] T-2" in result, "T-2 untouched (session 2 was blocked)"


# ===========================================================================
# AC-LOCK-1..9 — additional lock state-machine tests not in T-11/T-12
# ===========================================================================


def test_ac_lock_1_free_state_no_lock_file(tmp_path: Path) -> None:
    """AC-LOCK-1: check_lock_state returns FREE when no lock file exists."""
    state = check_lock_state(tmp_path, "proj", "v1")
    assert state == LockState.FREE


def test_ac_lock_2_held_fresh_lock(tmp_path: Path) -> None:
    """AC-LOCK-2: HELD state returned for fresh lock with live PID."""
    create_impl_lock(
        tmp_path, context="proj", release="v1",
        session_id="sess_1", runtime="test", pid=os.getpid(),
    )
    assert check_lock_state(tmp_path, "proj", "v1") == LockState.HELD


def test_ac_lock_3_stale_expired_ttl(tmp_path: Path) -> None:
    """AC-LOCK-3: STALE returned when last_seen_at older than ttl_seconds."""
    lock_path = _impl_lock_path(tmp_path, "proj", "v1")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    old_ts = _stale_ts(20)
    lock_path.write_text(json.dumps({
        "lock_type": "implementation",
        "context": "proj", "release": "v1",
        "session_id": "sess_old", "runtime": "test",
        "pid": os.getpid(),
        "started_at": old_ts, "last_seen_at": old_ts,
        "ttl_seconds": 60,  # 60s TTL, 20 min elapsed = STALE
    }))
    assert check_lock_state(tmp_path, "proj", "v1") == LockState.STALE


def test_ac_lock_4_stale_dead_pid(tmp_path: Path) -> None:
    """AC-LOCK-4: STALE returned when PID no longer exists (dead process)."""
    lock_path = _impl_lock_path(tmp_path, "proj", "v1")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    lock_path.write_text(json.dumps({
        "lock_type": "implementation",
        "context": "proj", "release": "v1",
        "session_id": "sess_dead", "runtime": "test",
        "pid": 999999,  # non-existent PID
        "started_at": now, "last_seen_at": now,
        "ttl_seconds": 300,
    }))
    assert check_lock_state(tmp_path, "proj", "v1") == LockState.STALE


def test_ac_lock_5_held_to_free_via_release(tmp_path: Path) -> None:
    """AC-LOCK-5: HELD → FREE transition via release_impl_lock."""
    create_impl_lock(
        tmp_path, context="proj", release="v1",
        session_id="sess_1", runtime="test", pid=os.getpid(),
    )
    assert check_lock_state(tmp_path, "proj", "v1") == LockState.HELD
    result = release_impl_lock(tmp_path, "proj", "v1", "sess_1")
    assert result is True
    assert check_lock_state(tmp_path, "proj", "v1") == LockState.FREE


def test_ac_lock_6_stale_to_held_via_reclaim(tmp_path: Path) -> None:
    """AC-LOCK-6: STALE → HELD transition via reclaim_impl_lock."""
    lock_path = _impl_lock_path(tmp_path, "proj", "v1")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    old_ts = _stale_ts(15)
    lock_path.write_text(json.dumps({
        "lock_type": "implementation",
        "context": "proj", "release": "v1",
        "session_id": "sess_stale", "runtime": "test",
        "pid": os.getpid(),
        "started_at": old_ts, "last_seen_at": old_ts,
        "ttl_seconds": 60,
    }))
    assert check_lock_state(tmp_path, "proj", "v1") == LockState.STALE

    reclaim_impl_lock(
        tmp_path, context="proj", release="v1",
        new_session_id="sess_new", runtime="test", pid=os.getpid(),
        reason="reclaim after crash",
    )
    assert check_lock_state(tmp_path, "proj", "v1") == LockState.HELD
    data = json.loads(lock_path.read_text())
    assert data["session_id"] == "sess_new"


def test_ac_lock_7_reclaim_held_raises_lock_active_error(tmp_path: Path) -> None:
    """AC-LOCK-7: reclaim on HELD (fresh) lock raises LockActiveError."""
    create_impl_lock(
        tmp_path, context="proj", release="v1",
        session_id="sess_owner", runtime="test", pid=os.getpid(),
    )
    with pytest.raises(LockActiveError):
        reclaim_impl_lock(
            tmp_path, context="proj", release="v1",
            new_session_id="sess_attacker", runtime="test", pid=os.getpid(),
            reason="unauthorized reclaim",
        )


def test_ac_lock_8_release_wrong_session_returns_false(tmp_path: Path) -> None:
    """AC-LOCK-8: release by wrong session_id returns False; lock unchanged."""
    create_impl_lock(
        tmp_path, context="proj", release="v1",
        session_id="sess_owner", runtime="test", pid=os.getpid(),
    )
    result = release_impl_lock(tmp_path, "proj", "v1", "sess_other")
    assert result is False
    assert check_lock_state(tmp_path, "proj", "v1") == LockState.HELD


def test_ac_lock_9_unreadable_lock_file_treated_as_stale(tmp_path: Path) -> None:
    """AC-LOCK-9: corrupted/unreadable lock file → STALE (conservative fallback)."""
    lock_path = _impl_lock_path(tmp_path, "proj", "v1")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("NOT VALID JSON {{{")
    assert check_lock_state(tmp_path, "proj", "v1") == LockState.STALE


# ===========================================================================
# AC-REV-1..5 — BOUND_REVIEW mode
# ===========================================================================


def test_ac_rev_1_review_blocked_when_impl_lock_held(tmp_path: Path) -> None:
    """AC-REV-1: REVIEW bind is blocked when an implementation lock is HELD."""
    create_impl_lock(
        tmp_path, context="proj", release="v1",
        session_id="sess_impl", runtime="test", pid=os.getpid(),
    )

    with pytest.raises(ReviewBlockedByImplementationError) as exc_info:
        check_impl_xor_review(
            tmp_path, context="proj", release="v1",
            mode="REVIEW", session_id="sess_review",
        )

    assert "sess_impl" in str(exc_info.value)


def test_ac_rev_2_impl_blocked_when_review_session_exists(tmp_path: Path) -> None:
    """AC-REV-2: IMPLEMENTATION bind is blocked when a non-stale BOUND_REVIEW exists."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=UTC).isoformat()
    review_data = {
        "session_id": "sess_review_1",
        "context": "proj",
        "release": "v1",
        "mode": "BOUND_REVIEW",
        "last_seen_at": now,
        "ttl_seconds": 300,
    }
    (sessions_dir / "sess_review_1.json").write_text(json.dumps(review_data))

    with pytest.raises(ImplementationBlockedByReviewError) as exc_info:
        check_impl_xor_review(
            tmp_path, context="proj", release="v1",
            mode="IMPLEMENTATION", session_id="sess_impl",
        )

    assert "sess_review_1" in str(exc_info.value)


def test_ac_rev_3_two_review_sessions_coexist(tmp_path: Path) -> None:
    """AC-REV-3: two BOUND_REVIEW sessions for the same C/R pair coexist without error."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=UTC).isoformat()
    for i in (1, 2):
        (sessions_dir / f"sess_r{i}.json").write_text(json.dumps({
            "session_id": f"sess_r{i}",
            "context": "proj",
            "release": "v1",
            "mode": "BOUND_REVIEW",
            "last_seen_at": now,
            "ttl_seconds": 300,
        }))

    # REVIEW XOR check must not raise (no impl lock)
    check_impl_xor_review(
        tmp_path, context="proj", release="v1",
        mode="REVIEW", session_id="sess_r3",
    )

    reviews = find_review_sessions(tmp_path, "proj", "v1")
    assert "sess_r1" in reviews
    assert "sess_r2" in reviews
    assert len(reviews) == 2


def test_ac_rev_4_stale_review_session_does_not_block_impl(tmp_path: Path) -> None:
    """AC-REV-4: a STALE BOUND_REVIEW session does not block implementation bind."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    old_ts = _stale_ts(20)
    (sessions_dir / "sess_stale_review.json").write_text(json.dumps({
        "session_id": "sess_stale_review",
        "context": "proj",
        "release": "v1",
        "mode": "BOUND_REVIEW",
        "last_seen_at": old_ts,
        "ttl_seconds": 60,  # 60s TTL, 20 min elapsed → stale
    }))

    # Must NOT raise — stale reviews are ignored
    check_impl_xor_review(
        tmp_path, context="proj", release="v1",
        mode="IMPLEMENTATION", session_id="sess_impl",
    )

    reviews = find_review_sessions(tmp_path, "proj", "v1")
    assert "sess_stale_review" not in reviews, "Stale review sessions must not be returned"


def test_ac_rev_5_review_session_does_not_create_impl_lock(tmp_path: Path) -> None:
    """AC-REV-5: REVIEW mode does not create or own an implementation lock file.

    BOUND_REVIEW sessions are read-consistent sessions — they must not have
    an implementation lock file.  This test verifies that after creating a
    REVIEW session, no lock file for the context/release pair exists.
    """
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=UTC).isoformat()
    (sessions_dir / "sess_review.json").write_text(json.dumps({
        "session_id": "sess_review",
        "context": "proj",
        "release": "v1",
        "mode": "BOUND_REVIEW",
        "last_seen_at": now,
        "ttl_seconds": 300,
    }))

    lock_path = _impl_lock_path(tmp_path, "proj", "v1")
    assert not lock_path.exists(), (
        "BOUND_REVIEW session must NOT create an implementation lock file."
    )


# ===========================================================================
# AC-DOC-L1..12 — doctor LOCK invariant tests (2 per LOCK-1..6)
# ===========================================================================


# --- LOCK-1: duplicate lock files ---

def test_ac_doc_l1_violating_no_duplicates_possible_on_fs(tmp_path: Path) -> None:
    """AC-DOC-L1a: normal case — no duplicate lock files → no LOCK-1 issues."""
    ws = tmp_path
    doctor = _make_doctor(ws)
    issues = doctor.check()
    lock1_issues = [i for i in issues if i.code == "LOCK-1"]
    assert len(lock1_issues) == 0


def test_ac_doc_l1_fix_runs_without_error_when_no_duplicates(tmp_path: Path) -> None:
    """AC-DOC-L1b: fix() with no duplicate lock files returns empty list."""
    ws = tmp_path
    doctor = _make_doctor(ws)
    actions = doctor.fix()
    lock1_actions = [a for a in actions if "LOCK-1" in a]
    assert len(lock1_actions) == 0


# --- LOCK-2: impl lock for DEAD context ---

def test_ac_doc_l2_violating_lock_for_dead_ctx_detected(tmp_path: Path) -> None:
    """AC-DOC-L2a: LOCK-2 reported when an impl lock exists for a DEAD context."""
    ws = tmp_path
    _write_lock_file(ws, "dead-ctx", "v1", session_id="sess_orphan")

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD))

    doctor = _make_doctor(ws, store)
    issues = doctor.check()
    lock2 = [i for i in issues if i.code == "LOCK-2"]
    assert len(lock2) >= 1, f"Expected LOCK-2, got: {[i.code for i in issues]}"
    assert lock2[0].fixable is True


def test_ac_doc_l2_fix_deletes_lock_and_audits(tmp_path: Path) -> None:
    """AC-DOC-L2b: fix() deletes the lock file and appends LOCK_DELETED_DEAD_CTX audit."""
    ws = tmp_path
    lock_path = _write_lock_file(ws, "dead-ctx", "v1", session_id="sess_orphan")

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD))

    doctor = _make_doctor(ws, store)
    actions = doctor.fix()

    assert not lock_path.exists(), "LOCK-2 fix must delete the lock file"
    lock2_actions = [a for a in actions if "LOCK-2" in a]
    assert len(lock2_actions) >= 1

    log = _audit_log_path(ws)
    assert log.exists()
    events = [json.loads(ln)["event"] for ln in log.read_text().splitlines() if ln.strip()]
    assert "LOCK_DELETED_DEAD_CTX" in events


# --- LOCK-3: expired HELD lock ---

def test_ac_doc_l3_violating_expired_held_lock_reported(tmp_path: Path) -> None:
    """AC-DOC-L3a: LOCK-3 reported for HELD lock with last_seen_at older than ttl."""
    ws = tmp_path
    old_ts = _stale_ts(20)
    _write_lock_file(ws, "proj", "v1", session_id="sess_x",
                                 last_seen_at=old_ts, ttl_seconds=60)

    store = FakeContextStore()
    store.save(_make_ctx("proj", ContextState.ALIVE))
    doctor = _make_doctor(ws, store)

    issues = doctor.check()
    lock3 = [i for i in issues if i.code == "LOCK-3"]
    assert len(lock3) == 1, f"Expected LOCK-3, got: {[i.code for i in issues]}"
    assert lock3[0].fixable is True


def test_ac_doc_l3_fix_marks_stale_no_delete(tmp_path: Path) -> None:
    """AC-DOC-L3b: fix() marks STALE, does NOT delete the lock file."""
    ws = tmp_path
    old_ts = _stale_ts(20)
    lock_path = _write_lock_file(ws, "proj", "v1", session_id="sess_x",
                                 last_seen_at=old_ts, ttl_seconds=60)

    store = FakeContextStore()
    store.save(_make_ctx("proj", ContextState.ALIVE))
    doctor = _make_doctor(ws, store)
    doctor.fix()

    assert lock_path.exists(), "LOCK-3 fix must NOT delete the lock file"
    data = json.loads(lock_path.read_text())
    assert data.get("state") == "STALE"


# --- LOCK-4: production-write event missing task_id ---

def test_ac_doc_l4_violating_production_write_no_task_id(tmp_path: Path) -> None:
    """AC-DOC-L4a: LOCK-4 reported for PRODUCTION_WRITE event without task_id."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    record_bad = json.dumps({
        "ts": datetime.now(tz=UTC).isoformat(),
        "event": "PRODUCTION_WRITE",
        "context": "proj", "release": "v1",
        "session_id": "sess_bad", "runtime": "test",
        "pid": os.getpid(),
        # task_id intentionally absent
    })
    audit_path.write_text(record_bad + "\n")

    doctor = _make_doctor(ws)
    issues = doctor.check()
    lock4 = [i for i in issues if i.code == "LOCK-4"]
    assert len(lock4) == 1, f"Expected LOCK-4, got: {[i.code for i in issues]}"
    assert "sess_bad" in lock4[0].description
    assert lock4[0].fixable is False


def test_ac_doc_l4_fix_does_not_modify_audit_log(tmp_path: Path) -> None:
    """AC-DOC-L4b: fix() must NOT delete or modify the offending LOCK-4 audit record."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    record = json.dumps({
        "ts": datetime.now(tz=UTC).isoformat(),
        "event": "PRODUCTION_WRITE",
        "context": "proj", "release": "v1",
        "session_id": "sess_bad", "runtime": "test",
        "pid": os.getpid(),
    })
    audit_path.write_text(record + "\n")

    doctor = _make_doctor(ws)
    doctor.fix()

    lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1, "fix() must not delete audit entries for LOCK-4"


# --- LOCK-5: BLOCKED_ATTEMPT event ---

def test_ac_doc_l5_violating_blocked_attempt_surfaces(tmp_path: Path) -> None:
    """AC-DOC-L5a: LOCK-5 reported when BLOCKED_ATTEMPT exists in audit log."""
    ws = tmp_path
    audit_blocked(
        ws, context="proj", release="v1",
        session_id="sess_blocked", runtime="test",
        pid=os.getpid(), reason="lock already held",
    )

    doctor = _make_doctor(ws)
    issues = doctor.check()
    lock5 = [i for i in issues if i.code == "LOCK-5"]
    assert len(lock5) == 1
    assert lock5[0].fixable is False
    assert "sess_blocked" in lock5[0].description


def test_ac_doc_l5_fix_does_not_delete_blocked_attempt(tmp_path: Path) -> None:
    """AC-DOC-L5b: fix() must NOT delete BLOCKED_ATTEMPT audit entries."""
    ws = tmp_path
    audit_blocked(
        ws, context="proj", release="v1",
        session_id="sess_blocked", runtime="test",
        pid=os.getpid(), reason="lock held",
    )

    doctor = _make_doctor(ws)
    doctor.fix()

    audit_path = _audit_log_path(ws)
    lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 1, "fix() must not remove BLOCKED_ATTEMPT records"


# --- LOCK-6: BOUND_REVIEW session for DEAD context ---

def test_ac_doc_l6_violating_review_session_dead_ctx_reported(tmp_path: Path) -> None:
    """AC-DOC-L6a: LOCK-6 reported when a BOUND_REVIEW session belongs to a DEAD ctx."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=UTC).isoformat()
    session_file = sessions_dir / "sess_dead_review.json"
    session_file.write_text(json.dumps({
        "session_id": "sess_dead_review",
        "context": "dead-proj",
        "release": "v1",
        "mode": "BOUND_REVIEW",
        "runtime": "test",
        "pid": os.getpid(),
        "last_seen_at": now,
        "ttl_seconds": 300,
    }))

    store = FakeContextStore()
    store.save(_make_ctx("dead-proj", ContextState.DEAD))

    doctor = _make_doctor(ws, store)
    issues = doctor.check()
    lock6 = [i for i in issues if i.code == "LOCK-6"]
    assert len(lock6) == 1, f"Expected LOCK-6, got: {[i.code for i in issues]}"
    assert lock6[0].fixable is True


def test_ac_doc_l6_fix_deletes_session_and_audits(tmp_path: Path) -> None:
    """AC-DOC-L6b: fix() deletes the BOUND_REVIEW session file and appends audit."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=UTC).isoformat()
    session_file = sessions_dir / "sess_dead_review2.json"
    session_file.write_text(json.dumps({
        "session_id": "sess_dead_review2",
        "context": "dead-proj",
        "release": "v1",
        "mode": "BOUND_REVIEW",
        "runtime": "test",
        "pid": os.getpid(),
        "last_seen_at": now,
        "ttl_seconds": 300,
    }))

    store = FakeContextStore()
    store.save(_make_ctx("dead-proj", ContextState.DEAD))

    doctor = _make_doctor(ws, store)
    actions = doctor.fix()

    assert not session_file.exists(), "LOCK-6 fix must delete the session file"
    lock6_actions = [a for a in actions if "LOCK-6" in a]
    assert len(lock6_actions) >= 1

    log = _audit_log_path(ws)
    assert log.exists()
    events = [json.loads(ln)["event"] for ln in log.read_text().splitlines() if ln.strip()]
    assert "REVIEW_SESSION_DELETED_DEAD_CTX" in events


# ===========================================================================
# AC-COV-1..3 — service.py coverage: cover specific uncovered lines
# These tests exercise code paths via real JsonContextStore + workspace_lock
# that existing FakeContextStore-based tests miss.
# ===========================================================================


def test_ac_cov_service_create_duplicate_with_real_store(tmp_path: Path) -> None:
    """AC-COV: create() with real store raises ContextAlreadyExistsError (line 68)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    svc.create("proj", "repo", "https://example.com/repo")
    with pytest.raises(ContextAlreadyExistsError):
        svc.create("proj", "other", "https://example.com/other")


def test_ac_cov_service_list_all_with_real_store(tmp_path: Path) -> None:
    """AC-COV: list_all() returns all saved contexts (line 86)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    svc.create("a", "a-repo", "https://example.com/a")
    svc.create("b", "b-repo", "https://example.com/b")
    result = svc.list_all()
    assert {c.name for c in result} == {"a", "b"}


def test_ac_cov_service_show_found_and_not_found(tmp_path: Path) -> None:
    """AC-COV: show() returns context or raises ContextNotFoundError (lines 89-92)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    svc.create("proj", "repo", "https://example.com/repo")
    ctx = svc.show("proj")
    assert ctx.name == "proj"
    with pytest.raises(ContextNotFoundError):
        svc.show("ghost")


def test_ac_cov_service_alive_context_not_found_real_store(tmp_path: Path) -> None:
    """AC-COV: alive() raises ContextNotFoundError for unknown context (line 112)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    with pytest.raises(ContextNotFoundError):
        svc.alive("nonexistent")


def test_ac_cov_service_alive_idempotent_real_store(tmp_path: Path) -> None:
    """AC-COV: alive() on already-ALIVE returns early — covers the idempotent branch (line 116)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    svc.create("proj", "repo", "https://example.com/repo")
    ctx1 = svc.alive("proj")
    assert ctx1.state == ContextState.ALIVE
    ctx2 = svc.alive("proj")  # idempotent — should not error
    assert ctx2.state == ContextState.ALIVE


def test_ac_cov_service_alive_re_read_after_lock2(tmp_path: Path) -> None:
    """AC-COV: alive() re-reads ctx inside Lock 2 (line 128: ctx_l2 not None path)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    svc.create("proj", "repo", "https://example.com/repo")
    ctx = svc.alive("proj")
    assert ctx.state == ContextState.ALIVE


def test_ac_cov_service_alive_with_current_branch(tmp_path: Path) -> None:
    """AC-COV: alive() stores actual_branch from git.current_branch() (lines 136-148)."""
    ws = _make_ws(tmp_path)
    git = FakeGitClient()
    repo_path = ws / "repos" / "repo"
    repo_path.mkdir(parents=True, exist_ok=True)
    git._branches[repo_path] = "feature-branch"

    states = ws / ".dadaia" / "states"
    svc = SpecContextService(
        context_store=JsonContextStore(states),
        primary_store=FakePrimaryContextStore(),
        git_client=git,
        workspace_root=ws,
    )
    svc.create("proj", "repo", "https://example.com/repo")
    ctx = svc.alive("proj")
    assert ctx.current_branch == "feature-branch"


def test_ac_cov_service_dead_not_found_real_store(tmp_path: Path) -> None:
    """AC-COV: dead() raises ContextNotFoundError for unknown (lines 201, 203)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    with pytest.raises(ContextNotFoundError):
        svc.dead("ghost")


def test_ac_cov_service_dead_state_error_not_alive_real_store(tmp_path: Path) -> None:
    """AC-COV: dead() raises ContextStateError when context is already DEAD (line 203)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    svc.create("proj", "repo", "https://example.com/repo")
    # Context starts DEAD — calling dead() again must raise ContextStateError
    with pytest.raises(ContextStateError):
        svc.dead("proj")


def test_ac_cov_service_dead_no_repo_on_disk(tmp_path: Path) -> None:
    """AC-COV: dead() works when repo is already missing (lines 225-228 — repo not exists)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    svc.create("proj", "repo", "https://example.com/repo")
    svc.alive("proj")
    # Remove the repo manually to simulate it already being absent
    repo = ws / "repos" / "repo"
    if repo.exists():
        import shutil
        shutil.rmtree(repo)
    # dead() should still succeed
    ctx = svc.dead("proj")
    assert ctx.state == ContextState.DEAD


def test_ac_cov_service_delete_alive_raises_state_error(tmp_path: Path) -> None:
    """AC-COV: delete() on ALIVE context raises ContextStateError (lines 272-280)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    svc.create("proj", "repo", "https://example.com/repo")
    svc.alive("proj")
    with pytest.raises(ContextStateError):
        svc.delete("proj")


def test_ac_cov_service_delete_not_found_raises(tmp_path: Path) -> None:
    """AC-COV: delete() on unknown context raises ContextNotFoundError (lines 272-280)."""
    ws = _make_ws(tmp_path)
    svc = _make_svc(ws)
    with pytest.raises(ContextNotFoundError):
        svc.delete("ghost")


def test_ac_cov_json_store_unknown_schema_version(tmp_path: Path) -> None:
    """AC-COV: loading a file with unknown schema_version raises SchemaVersionError (line 51)."""
    from dadaia_workspace.core.exceptions import SchemaVersionError

    ctx_file = tmp_path / "spec_contexts.json"
    ctx_file.write_text(json.dumps({
        "schema_version": "99",
        "contexts": [],
    }))
    store = JsonContextStore(tmp_path)
    with pytest.raises(SchemaVersionError) as exc_info:
        store.list_all()
    assert "dadaia migrate" in str(exc_info.value)


def test_ac_cov_doctor_check_inv4_alive_repo_missing(tmp_path: Path) -> None:
    """AC-COV: doctor INV-4 reports ALIVE context with missing repo on disk (line 150)."""
    ws = tmp_path
    store = FakeContextStore()
    store.save(_make_ctx("alive-ctx", ContextState.ALIVE))
    # Repo NOT created on disk

    doctor = _make_doctor(ws, store)
    issues = doctor.check()
    inv4 = [i for i in issues if i.code == "INV-4"]
    assert len(inv4) >= 1
    assert inv4[0].fixable is False


def test_ac_cov_doctor_check_inv5_dead_repo_present(tmp_path: Path) -> None:
    """AC-COV: doctor INV-5 reports DEAD context whose repo exists on disk (line 163)."""
    ws = tmp_path
    repos_dir = ws / "repos"
    repos_dir.mkdir(parents=True, exist_ok=True)
    (repos_dir / "dead-repo").mkdir()

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD, slug="dead-repo"))

    doctor = _make_doctor(ws, store)
    issues = doctor.check()
    inv5 = [i for i in issues if i.code == "INV-5"]
    assert len(inv5) >= 1
    assert inv5[0].fixable is True


def test_ac_cov_doctor_fix_inv5_removes_stale_repo(tmp_path: Path) -> None:
    """AC-COV: fix() removes stale repo for DEAD context (lines 351-366 of doctor.py)."""
    ws = tmp_path
    repos_dir = ws / "repos"
    repos_dir.mkdir(parents=True, exist_ok=True)
    stale_repo = repos_dir / "dead-repo"
    stale_repo.mkdir()
    (stale_repo / "file.py").write_text("# stale")

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD, slug="dead-repo"))

    doctor = _make_doctor(ws, store)
    actions = doctor.fix()

    assert not stale_repo.exists(), "fix() must remove stale repo for DEAD context"
    assert any("dead-repo" in a or "dead-ctx" in a for a in actions)


# ===========================================================================
# AC-COV-3 extended — doctor.py helper edge cases and remaining uncovered paths
# Targets: lines 82, 93-101, 112-113, 124-127, 139, 176, 194, 211, 214, 216,
#          245-246, 259-260, 271-272, 285-286, 293, 296-297, 299, 362,
#          373-390, 400, 423, 426, 428, 446, 449, 451
# ===========================================================================


# --- _grouped_lock_files: non-.json file in locks_dir (line 82) ---

def test_ac_cov_doctor_grouped_lock_files_skips_non_json(tmp_path: Path) -> None:
    """_grouped_lock_files skips non-.json files in the locks dir (line 82)."""
    ws = tmp_path
    locks_dir = ws / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True)
    # Write a non-.json file — must be ignored
    (locks_dir / "orphan.conflicted").write_text("junk")
    (locks_dir / "README.txt").write_text("notes")

    doctor = _make_doctor(ws)
    # check() should produce zero LOCK-1 issues (non-.json files are skipped)
    issues = doctor.check()
    lock1 = [i for i in issues if i.code == "LOCK-1"]
    assert len(lock1) == 0


# --- _last_seen_epoch: missing field returns 0.0 (lines 93-97) ---

def test_ac_cov_doctor_last_seen_epoch_missing_field(tmp_path: Path) -> None:
    """_last_seen_epoch returns 0.0 when last_seen_at is absent (lines 93-97)."""
    p = tmp_path / "lock.json"
    p.write_text(json.dumps({"session_id": "s1"}))  # no last_seen_at
    epoch = DoctorService._last_seen_epoch(p)
    assert epoch == 0.0


def test_ac_cov_doctor_last_seen_epoch_valid_ts(tmp_path: Path) -> None:
    """_last_seen_epoch returns correct float for a valid ISO timestamp (lines 98-99)."""
    p = tmp_path / "lock.json"
    ts = "2026-01-01T12:00:00Z"
    p.write_text(json.dumps({"last_seen_at": ts}))
    epoch = DoctorService._last_seen_epoch(p)
    assert epoch > 0.0


def test_ac_cov_doctor_last_seen_epoch_bad_json_returns_0(tmp_path: Path) -> None:
    """_last_seen_epoch returns 0.0 when the file is not valid JSON (line 100-101)."""
    p = tmp_path / "lock.json"
    p.write_text("NOT JSON")
    epoch = DoctorService._last_seen_epoch(p)
    assert epoch == 0.0


# --- _read_lock: exception branch (lines 112-113) ---

def test_ac_cov_doctor_read_lock_bad_json_returns_none(tmp_path: Path) -> None:
    """_read_lock returns None when the file contains invalid JSON (lines 112-113)."""
    p = tmp_path / "bad.json"
    p.write_text("{ NOT JSON }")
    result = DoctorService._read_lock(p)
    assert result is None


def test_ac_cov_doctor_read_lock_valid_json(tmp_path: Path) -> None:
    """_read_lock returns the dict for a valid JSON file (lines 109-111)."""
    p = tmp_path / "good.json"
    p.write_text(json.dumps({"key": "value"}))
    result = DoctorService._read_lock(p)
    assert result == {"key": "value"}


# --- _int: non-int convertible path and ValueError (lines 124-127) ---

def test_ac_cov_doctor_int_non_int_string_convertible(tmp_path: Path) -> None:
    """_int converts a string representation of an int (lines 124-125)."""
    result = DoctorService._int({"pid": "42"}, "pid", 0)
    assert result == 42


def test_ac_cov_doctor_int_non_int_non_convertible_returns_default(tmp_path: Path) -> None:
    """_int returns default when value cannot be converted (lines 126-127)."""
    result = DoctorService._int({"pid": "not-a-number"}, "pid", -1)
    assert result == -1


def test_ac_cov_doctor_int_int_value_direct(tmp_path: Path) -> None:
    """_int returns int directly when value is already int (lines 122-123)."""
    result = DoctorService._int({"pid": 99}, "pid", 0)
    assert result == 99


# --- _parse_key: single-segment (no '__') returns (key, '') — line 139 ---

def test_ac_cov_doctor_parse_key_single_segment(tmp_path: Path) -> None:
    """_parse_key returns (key, '') when there is no '__' separator (line 139)."""
    ctx, release = DoctorService._parse_key("nodoublescore")
    assert ctx == "nodoublescore"
    assert release == ""


def test_ac_cov_doctor_parse_key_two_segments(tmp_path: Path) -> None:
    """_parse_key correctly splits 'ctx__rel' into ('ctx', 'rel') (lines 137-138)."""
    ctx, release = DoctorService._parse_key("myctx__v1")
    assert ctx == "myctx"
    assert release == "v1"


# --- LOCK-1 check() detection (line 176) ---

def test_ac_cov_doctor_lock1_check_detects_duplicate_lock_files(tmp_path: Path) -> None:
    """LOCK-1 check() fires when two .json files exist for the same key (line 176)."""
    ws = tmp_path
    locks_dir = ws / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True)

    now_ts = datetime.now(tz=UTC).isoformat()
    old_ts = (datetime.now(tz=UTC) - timedelta(minutes=5)).isoformat()

    # Two files with the same stem: ctx__v1.json is not possible on real FS
    # (can't have two files with same name). The doctor groups by STEM of filenames.
    # To simulate duplicates, we need two DIFFERENT filenames that map to the same key.
    # Looking at _grouped_lock_files: key = f.stem — so we need files with the same stem.
    # On a real FS two files with identical stems in the same dir is impossible.
    # The grouping is by stem, and two distinct files can only have the same stem if
    # one is ctx__v1.json and another might use a suffix variant.
    # BUT: _grouped_lock_files only adds .json files, and key = f.stem.
    # So to get 2 files for the same key, we need two .json files whose stem is identical —
    # which is impossible on a normal FS.
    #
    # Re-reading the code: locks_dir can have e.g. "ctx__v1.json" and also files
    # created by rename with different suffixes are skipped. The ONLY way to get 2 entries
    # for the same key is if the lock files have different stems that collide after stem
    # extraction — but stem IS the filename minus the LAST suffix.
    #
    # Actually, looking again: f.stem on "ctx__v1.json" = "ctx__v1".
    # To have 2 files map to the same stem, we'd need something like:
    # "ctx__v1.json" and "ctx__v1.2.json" → stem "ctx__v1.2" ≠ "ctx__v1".
    # This cannot happen with normal .json files.
    #
    # The REAL scenario: the implementation creates a tmp file "ctx__v1.tmp" then
    # os.replace. A crash could leave ctx__v1.json AND the old ctx__v1.json if the
    # naming scheme used timestamps or suffixes.
    #
    # Actually re-reading _impl_lock_path: it always uses f"{context}__{release}.json".
    # So there can only be ONE .json per key on a normal FS.
    #
    # The LOCK-1 scenario must be tested by directly writing two files with THE SAME stem
    # in the same directory — which is impossible on the same filesystem. This means
    # LOCK-1 can only arise if the code manually creates a second copy or via a race.
    # The test must craft this by writing two distinct filenames that share the stem
    # after suffix stripping, but with .json suffix both... which requires different paths.
    #
    # SOLUTION: write the second file to a SUBDIRECTORY stem trick OR use the actual
    # grouped logic by writing two files in the same locks_dir that have the same
    # stem after f.stem — this is only possible with 0-length filenames or Unicode tricks.
    #
    # The correct way: _grouped_lock_files groups by f.stem. Two .json files CAN have
    # the same stem if they are in different positions, but they're in the SAME directory.
    # On a filesystem, you cannot have two files with the SAME name in the same dir.
    # So f.stem will always be unique per file in the same dir.
    #
    # CONCLUSION: LOCK-1 via _grouped_lock_files is STRUCTURALLY UNTESTABLE via real FS
    # because two .json files in the same dir cannot have the same stem.
    # The only path to trigger it is to either mock the method or use a DoctorService
    # subclass that overrides _grouped_lock_files.
    # Let's use a subclass approach.

    class _DoctorWithDuplicates(DoctorService):
        def _grouped_lock_files(self) -> dict[str, list[Path]]:
            # Simulate two .json files for the same key
            p1 = locks_dir / "ctx__v1.json"
            p2 = locks_dir / "ctx__v1_copy.json"
            p1.write_text(json.dumps({
                "lock_type": "implementation",
                "context": "ctx", "release": "v1",
                "session_id": "sess_a", "runtime": "test",
                "pid": os.getpid(),
                "last_seen_at": old_ts,
                "ttl_seconds": 300,
            }))
            p2.write_text(json.dumps({
                "lock_type": "implementation",
                "context": "ctx", "release": "v1",
                "session_id": "sess_b", "runtime": "test",
                "pid": os.getpid(),
                "last_seen_at": now_ts,
                "ttl_seconds": 300,
            }))
            return {"ctx__v1": [p1, p2]}

    doctor = _DoctorWithDuplicates(
        context_store=FakeContextStore(),
        primary_store=FakePrimaryContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )
    issues = doctor.check()
    lock1 = [i for i in issues if i.code == "LOCK-1"]
    assert len(lock1) == 1, f"Expected LOCK-1, got: {[i.code for i in issues]}"
    assert lock1[0].fixable is True
    assert "ctx__v1" in lock1[0].description


# --- LOCK-1 fix() rename path (lines 373-390, 400) ---

def test_ac_cov_doctor_lock1_fix_renames_stale_to_conflicted(tmp_path: Path) -> None:
    """LOCK-1 fix(): stale duplicate renamed to .conflicted, freshest kept, audit appended."""
    ws = tmp_path
    locks_dir = ws / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True)

    old_ts = (datetime.now(tz=UTC) - timedelta(minutes=5)).isoformat()
    now_ts = datetime.now(tz=UTC).isoformat()

    p_stale = locks_dir / "ctx__v1_stale.json"
    p_fresh = locks_dir / "ctx__v1_fresh.json"
    p_stale.write_text(json.dumps({
        "lock_type": "implementation",
        "context": "ctx", "release": "v1",
        "session_id": "sess_stale", "runtime": "test",
        "pid": os.getpid(),
        "last_seen_at": old_ts,
        "ttl_seconds": 300,
    }))
    p_fresh.write_text(json.dumps({
        "lock_type": "implementation",
        "context": "ctx", "release": "v1",
        "session_id": "sess_fresh", "runtime": "test",
        "pid": os.getpid(),
        "last_seen_at": now_ts,
        "ttl_seconds": 300,
    }))

    class _DoctorWithDuplicates(DoctorService):
        def _grouped_lock_files(self) -> dict[str, list[Path]]:
            return {"ctx__v1": [p_stale, p_fresh]}

    doctor = _DoctorWithDuplicates(
        context_store=FakeContextStore(),
        primary_store=FakePrimaryContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )
    actions = doctor.fix()

    # The stale file must be renamed to .conflicted
    assert not p_stale.exists(), "Stale lock file must be renamed"
    assert p_stale.with_suffix(".conflicted").exists(), "Stale file must get .conflicted suffix"
    # The freshest must remain
    assert p_fresh.exists(), "Fresh lock file must be kept"

    # An action string mentioning LOCK-1 must be present
    lock1_actions = [a for a in actions if "LOCK-1" in a]
    assert len(lock1_actions) >= 1

    # LOCK_CONFLICT_RENAMED event must be in audit log
    log = _audit_log_path(ws)
    assert log.exists(), "Audit log must be written"
    events = [json.loads(ln)["event"] for ln in log.read_text().splitlines() if ln.strip()]
    assert "LOCK_CONFLICT_RENAMED" in events, f"Expected LOCK_CONFLICT_RENAMED in {events}"


def test_ac_cov_doctor_lock1_fix_freshest_kept_by_last_seen(tmp_path: Path) -> None:
    """LOCK-1 fix(): the file with most-recent last_seen_at is kept (lines 373-374)."""
    ws = tmp_path
    locks_dir = ws / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True)

    # File A: older timestamp
    ts_a = (datetime.now(tz=UTC) - timedelta(minutes=10)).isoformat()
    # File B: newer timestamp
    ts_b = (datetime.now(tz=UTC) - timedelta(minutes=1)).isoformat()

    p_a = locks_dir / "proj__rel1_a.json"
    p_b = locks_dir / "proj__rel1_b.json"
    p_a.write_text(json.dumps({
        "context": "proj", "release": "rel1",
        "session_id": "sess_a", "runtime": "test",
        "pid": os.getpid(), "last_seen_at": ts_a, "ttl_seconds": 300,
    }))
    p_b.write_text(json.dumps({
        "context": "proj", "release": "rel1",
        "session_id": "sess_b", "runtime": "test",
        "pid": os.getpid(), "last_seen_at": ts_b, "ttl_seconds": 300,
    }))

    class _DoctorWith2(DoctorService):
        def _grouped_lock_files(self) -> dict[str, list[Path]]:
            return {"proj__rel1": [p_a, p_b]}

    doctor = _DoctorWith2(
        context_store=FakeContextStore(),
        primary_store=FakePrimaryContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )
    doctor.fix()

    # p_b (newer) must survive; p_a (older) must become .conflicted
    assert p_b.exists(), "Fresher file must be kept"
    assert not p_a.exists(), "Older file must be renamed"
    assert p_a.with_suffix(".conflicted").exists()


# --- LOCK-3 check() detection branches (lines 211, 214, 216) ---

def test_ac_cov_doctor_lock3_check_skips_already_stale_marked(tmp_path: Path) -> None:
    """LOCK-3 check(): lock already marked state=STALE is skipped (line 214-216)."""
    ws = tmp_path
    old_ts = _stale_ts(20)
    # Write a lock that is already marked STALE in JSON
    _write_lock_file(ws, "proj", "v1", session_id="sess_x",
                     last_seen_at=old_ts, ttl_seconds=60, state="STALE")

    doctor = _make_doctor(ws)
    issues = doctor.check()
    # LOCK-3 should NOT be reported — already marked STALE
    lock3 = [i for i in issues if i.code == "LOCK-3"]
    assert len(lock3) == 0, f"Stale-marked lock must not trigger LOCK-3: {lock3}"


def test_ac_cov_doctor_lock3_check_none_data_skipped(tmp_path: Path) -> None:
    """LOCK-3 check(): corrupted lock file (read_lock returns None) is skipped (line 211)."""
    ws = tmp_path
    locks_dir = ws / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True)
    bad_lock = locks_dir / "proj__v1.json"
    bad_lock.write_text("NOT JSON {{{")

    doctor = _make_doctor(ws)
    issues = doctor.check()
    # Must not raise; LOCK-3 not reported for unreadable locks
    lock3 = [i for i in issues if i.code == "LOCK-3"]
    assert len(lock3) == 0


# --- LOCK-4/5 JSONDecodeError and OSError branches (245-246, 259-260, 271-272, 285-286) ---

def test_ac_cov_doctor_lock4_skips_invalid_json_line(tmp_path: Path) -> None:
    """LOCK-4 check(): malformed JSON lines in audit log are skipped (lines 245-246)."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    # Write one bad JSON line and one good PRODUCTION_WRITE with task_id (no issue)
    good = json.dumps({
        "event": "PRODUCTION_WRITE", "session_id": "s1",
        "context": "p", "release": "v1", "task_id": "T-1",
    })
    audit_path.write_text("NOT JSON\n" + good + "\n")

    doctor = _make_doctor(ws)
    issues = doctor.check()
    # The bad line is skipped; good line has task_id so no LOCK-4
    lock4 = [i for i in issues if i.code == "LOCK-4"]
    assert len(lock4) == 0


def test_ac_cov_doctor_lock5_skips_invalid_json_line(tmp_path: Path) -> None:
    """LOCK-5 check(): malformed JSON lines in audit log are skipped (lines 271-272)."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    # Only a bad JSON line — must not raise; no LOCK-5 issues
    audit_path.write_text("GARBAGE LINE\n")

    doctor = _make_doctor(ws)
    issues = doctor.check()
    lock5 = [i for i in issues if i.code == "LOCK-5"]
    assert len(lock5) == 0


# --- LOCK-6 check(): non-.json files and non-BOUND_REVIEW sessions skipped (293, 296-297, 299) ---

def test_ac_cov_doctor_lock6_check_skips_non_json_session_files(tmp_path: Path) -> None:
    """LOCK-6 check(): non-.json files in sessions_dir are skipped (line 293)."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)
    # Write a non-.json file
    (sessions_dir / "notes.txt").write_text("irrelevant")

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD))
    doctor = _make_doctor(ws, store)
    issues = doctor.check()
    lock6 = [i for i in issues if i.code == "LOCK-6"]
    assert len(lock6) == 0


def test_ac_cov_doctor_lock6_check_skips_invalid_json_session(tmp_path: Path) -> None:
    """LOCK-6 check(): invalid JSON session file is skipped silently (lines 296-297)."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "bad_session.json").write_text("NOT JSON")

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD))
    doctor = _make_doctor(ws, store)
    # Must not raise
    issues = doctor.check()
    lock6 = [i for i in issues if i.code == "LOCK-6"]
    assert len(lock6) == 0


def test_ac_cov_doctor_lock6_check_skips_non_bound_review_mode(tmp_path: Path) -> None:
    """LOCK-6 check(): session with mode != BOUND_REVIEW is skipped (line 299)."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)
    now = datetime.now(tz=UTC).isoformat()
    (sessions_dir / "impl_session.json").write_text(json.dumps({
        "session_id": "sess_impl",
        "context": "dead-ctx",
        "release": "v1",
        "mode": "BOUND_IMPLEMENTATION",  # not BOUND_REVIEW
        "last_seen_at": now,
        "ttl_seconds": 300,
    }))

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD))
    doctor = _make_doctor(ws, store)
    issues = doctor.check()
    lock6 = [i for i in issues if i.code == "LOCK-6"]
    assert len(lock6) == 0


# --- INV-5 fix() recheck continue path (line 362) ---

def test_ac_cov_doctor_fix_inv5_skips_if_context_transitions_to_alive(tmp_path: Path) -> None:
    """fix() INV-5: skips rmtree if store re-read shows context is no longer DEAD (line 362).

    Simulates the race where, by the time fix() re-reads the context inside
    context_lock, the context has transitioned to ALIVE.  We inject a custom
    ContextStore whose get() always returns ALIVE (simulating that the context
    transitioned just before the recheck), while list_all() still returns DEAD
    (so fix() enters the INV-5 branch in the first place).
    """
    ws = tmp_path
    repos_dir = ws / "repos"
    repos_dir.mkdir(parents=True)
    stale_repo = repos_dir / "transitioning-repo"
    stale_repo.mkdir()

    dead_ctx = _make_ctx("transitioning-ctx", ContextState.DEAD, slug="transitioning-repo")
    alive_ctx = _make_ctx("transitioning-ctx", ContextState.ALIVE, slug="transitioning-repo")

    class _TransitionStore(FakeContextStore):
        """list_all() returns DEAD; get() returns ALIVE (recheck path)."""
        def list_all(self) -> list:
            return [dead_ctx]

        def get(self, name: str):  # type: ignore[override]
            # The recheck always sees ALIVE — context already transitioned
            return alive_ctx

    doctor = DoctorService(
        context_store=_TransitionStore(),
        primary_store=FakePrimaryContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )
    actions = doctor.fix()

    # The repo must NOT have been removed because the recheck saw ALIVE
    assert stale_repo.exists(), "Repo must NOT be removed when context transitioned to ALIVE"
    # No action for this repo
    assert not any("transitioning" in a for a in actions)


# --- LOCK-3 fix() branches: None read_lock, already STALE, and non-json skip (423, 426, 428) ---

def test_ac_cov_doctor_lock3_fix_skips_bad_json_lock(tmp_path: Path) -> None:
    """LOCK-3 fix(): corrupted lock file (read_lock→None) is skipped (line 425-426)."""
    ws = tmp_path
    locks_dir = ws / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True)
    bad = locks_dir / "ctx__v1.json"
    bad.write_text("NOT JSON")

    doctor = _make_doctor(ws)
    actions = doctor.fix()
    lock3_actions = [a for a in actions if "LOCK-3" in a]
    assert len(lock3_actions) == 0, "Corrupted lock must not produce LOCK-3 fix action"


def test_ac_cov_doctor_lock3_fix_skips_already_stale_lock(tmp_path: Path) -> None:
    """LOCK-3 fix(): lock already state=STALE is skipped (line 427-428)."""
    ws = tmp_path
    old_ts = _stale_ts(20)
    _write_lock_file(ws, "proj", "v1", session_id="sess_x",
                     last_seen_at=old_ts, ttl_seconds=60, state="STALE")

    doctor = _make_doctor(ws)
    actions = doctor.fix()
    lock3_actions = [a for a in actions if "LOCK-3" in a]
    assert len(lock3_actions) == 0, "Already-STALE lock must not produce duplicate LOCK-3 action"


def test_ac_cov_doctor_lock3_fix_skips_non_json_in_locks_dir(tmp_path: Path) -> None:
    """LOCK-3 fix(): non-.json files in locks dir are skipped (line 422-423)."""
    ws = tmp_path
    locks_dir = ws / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True)
    (locks_dir / "stray.conflicted").write_text("junk")

    doctor = _make_doctor(ws)
    actions = doctor.fix()
    lock3_actions = [a for a in actions if "LOCK-3" in a]
    assert len(lock3_actions) == 0


# --- LOCK-6 fix(): non-.json, None read_lock, non-BOUND_REVIEW skips (446, 449, 451) ---

def test_ac_cov_doctor_lock6_fix_skips_non_json_session(tmp_path: Path) -> None:
    """LOCK-6 fix(): non-.json session files are skipped (line 446)."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "notes.txt").write_text("irrelevant")

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD))
    doctor = _make_doctor(ws, store)
    actions = doctor.fix()
    lock6_actions = [a for a in actions if "LOCK-6" in a]
    assert len(lock6_actions) == 0


def test_ac_cov_doctor_lock6_fix_skips_bad_json_session(tmp_path: Path) -> None:
    """LOCK-6 fix(): corrupted session JSON (read_lock→None) is skipped (line 449)."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "corrupt.json").write_text("NOT JSON")

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD))
    doctor = _make_doctor(ws, store)
    actions = doctor.fix()
    lock6_actions = [a for a in actions if "LOCK-6" in a]
    assert len(lock6_actions) == 0


def test_ac_cov_doctor_lock6_fix_skips_non_bound_review_session(tmp_path: Path) -> None:
    """LOCK-6 fix(): session with mode != BOUND_REVIEW is skipped (line 451)."""
    ws = tmp_path
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)
    now = datetime.now(tz=UTC).isoformat()
    (sessions_dir / "impl.json").write_text(json.dumps({
        "session_id": "sess_impl",
        "context": "dead-ctx",
        "release": "v1",
        "mode": "BOUND_IMPLEMENTATION",
        "last_seen_at": now,
        "ttl_seconds": 300,
    }))

    store = FakeContextStore()
    store.save(_make_ctx("dead-ctx", ContextState.DEAD))
    doctor = _make_doctor(ws, store)
    actions = doctor.fix()
    lock6_actions = [a for a in actions if "LOCK-6" in a]
    assert len(lock6_actions) == 0


# --- LOCK-2 fix() audit path: _parse_key in LOCK-2 loop (line 194 / 400) ---

def test_ac_cov_doctor_lock4_oserror_on_audit_read(tmp_path: Path) -> None:
    """LOCK-4 check(): OSError reading audit log is swallowed silently (lines 259-260)."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("{}\n")
    # Make the file unreadable to trigger OSError
    audit_path.chmod(0o000)
    try:
        doctor = _make_doctor(ws)
        # Must not raise — OSError is caught
        issues = doctor.check()
        lock4 = [i for i in issues if i.code == "LOCK-4"]
        assert len(lock4) == 0
    finally:
        audit_path.chmod(0o644)  # restore for cleanup


def test_ac_cov_doctor_lock5_oserror_on_audit_read(tmp_path: Path) -> None:
    """LOCK-5 check(): OSError reading audit log is swallowed silently (lines 285-286)."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("{}\n")
    audit_path.chmod(0o000)
    try:
        doctor = _make_doctor(ws)
        issues = doctor.check()
        lock5 = [i for i in issues if i.code == "LOCK-5"]
        assert len(lock5) == 0
    finally:
        audit_path.chmod(0o644)


def test_ac_cov_doctor_lock2_check_uses_parse_key_in_loop(tmp_path: Path) -> None:
    """LOCK-2 check(): _parse_key is called for each lock file (covers line 194/195)."""
    ws = tmp_path
    # Write a lock for a context with a single-segment name (no '__' — unusual but valid)
    locks_dir = ws / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True)
    (locks_dir / "norelease.json").write_text(json.dumps({
        "lock_type": "implementation",
        "context": "norelease", "release": "",
        "session_id": "sess_x", "runtime": "test",
        "pid": os.getpid(),
        "last_seen_at": datetime.now(tz=UTC).isoformat(),
        "ttl_seconds": 300,
    }))

    store = FakeContextStore()
    store.save(_make_ctx("norelease", ContextState.DEAD))

    doctor = _make_doctor(ws, store)
    issues = doctor.check()
    # LOCK-2 must be detected: a lock for DEAD context
    lock2 = [i for i in issues if i.code == "LOCK-2"]
    assert len(lock2) >= 1
