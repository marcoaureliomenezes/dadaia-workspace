"""Unit tests for T-R1-06: Doctor LOCK-7 orphan lock invariant.

LOCK-7 (orphan lock) definition:
    A HELD implementation lock whose owning session has no session file on disk
    (.dadaia/sessions/<session_id>.json is absent). This is distinct from:

    - LOCK-2: impl lock for a DEAD context (context state issue)
    - LOCK-3: HELD lock with expired TTL or dead pid (heartbeat/liveness issue)

    The key new scenario: the session file was deleted (e.g. manual cleanup, bug)
    while the lock file persists. The pid may appear alive (e.g. reused by OS) but
    the session is gone — making the lock unrecoverable without manual intervention.

    LOCK-7 fires only when:
      - The lock is NOT already LOCK-2 (context is ALIVE, not DEAD)
      - The lock state may be HELD or STALE
      - The session file is ABSENT

    When the pid is dead AND the heartbeat is stale → LOCK-3 fires (existing).
    When the pid is dead but heartbeat is fresh → LOCK-3 fires (pid check in check_lock_state).
    When the session file is missing → LOCK-7 fires (new orphan check).

    The fix() for LOCK-7 removes the orphan lock file and appends an audit event.

Tests:
  - clean state: no LOCK-7 issues when lock has session file
  - orphan: LOCK-7 detected when session file is absent (live pid)
  - orphan: LOCK-7 detected when session file is absent (dead pid still gets LOCK-3 too)
  - fix() removes orphan lock and appends audit trail
  - LOCK-7 does NOT fire when session file is present (even if pid is dead → LOCK-3)
  - LOCK-7 does NOT fire for DEAD-context locks (LOCK-2 handles those)
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService
from tests.fakes import FakeContextStore, FakeGitClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(
    name: str,
    state: ContextState = ContextState.ALIVE,
    repo_slug: str | None = None,
) -> SpecContextProject:
    slug = repo_slug or name
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=slug,
        repo_url=f"https://github.com/org/{slug}",
        created_at="2026-01-01T00:00:00",
        alive_since="2026-06-01T00:00:00Z" if state == ContextState.ALIVE else None,
        dead_since=None,
        current_branch="main" if state == ContextState.ALIVE else None,
    )


def _make_doctor(
    workspace_root: Path,
    contexts: list[SpecContextProject] | None = None,
) -> tuple[DoctorService, FakeContextStore]:
    ctx_store = FakeContextStore()
    for c in contexts or []:
        ctx_store.save(c)
    git_client = FakeGitClient()
    svc = DoctorService(ctx_store, git_client, workspace_root)
    return svc, ctx_store


def _fresh_ts() -> str:
    return datetime.now(tz=UTC).isoformat()


def _stale_ts(seconds_ago: int = 400) -> str:
    return (datetime.now(tz=UTC) - timedelta(seconds=seconds_ago)).isoformat()


def _make_lock_file(
    workspace: Path,
    context: str,
    release: str,
    session_id: str,
    pid: int,
    last_seen_at: str | None = None,
    ttl_seconds: int = 300,
) -> Path:
    """Create an implementation lock file."""
    locks_dir = workspace / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_file = locks_dir / f"{context}__{release}.json"
    lock_file.write_text(
        json.dumps(
            {
                "lock_type": "implementation",
                "session_id": session_id,
                "context": context,
                "release": release,
                "pid": pid,
                "last_seen_at": last_seen_at or _fresh_ts(),
                "ttl_seconds": ttl_seconds,
                "runtime": "test",
            },
            indent=2,
        )
    )
    return lock_file


def _make_session_file(
    workspace: Path,
    session_id: str,
    context: str,
    release: str,
    mode: str = "BOUND_IMPLEMENTATION",
    pid: int | None = None,
    last_seen_at: str | None = None,
) -> Path:
    """Create a session file."""
    sessions_dir = workspace / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / f"{session_id}.json"
    session_file.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "context": context,
                "mode": mode,
                "release": release,
                "runtime": "test",
                "pid": pid or os.getpid(),
                "bound_at": _fresh_ts(),
                "last_seen_at": last_seen_at or _fresh_ts(),
                "ttl_seconds": 300,
                "is_stale": False,
            },
            indent=2,
        )
    )
    return session_file


def _audit_log_path(workspace: Path) -> Path:
    return workspace / ".dadaia" / "logs" / "lock-events.jsonl"


# ---------------------------------------------------------------------------
# Clean state — no LOCK-7 issues when everything is healthy
# ---------------------------------------------------------------------------


def test_lock7_clean_state_no_issue(tmp_path: Path) -> None:
    """No LOCK-7 when lock has a live pid and a matching session file."""
    ctx = _ctx("proj", state=ContextState.ALIVE)
    (tmp_path / "repos" / "proj").mkdir(parents=True)

    # Lock with current (live) pid
    _make_lock_file(tmp_path, "proj", "v1", "sess_good01", pid=os.getpid())
    # Matching session file
    _make_session_file(tmp_path, "sess_good01", "proj", "v1", pid=os.getpid())

    svc, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    lock7_issues = [i for i in issues if i.code == "LOCK-7"]
    assert lock7_issues == [], f"Expected no LOCK-7, got: {lock7_issues}"


# ---------------------------------------------------------------------------
# LOCK-7: missing session file (live pid — genuinely new orphan case)
# ---------------------------------------------------------------------------


def test_lock7_missing_session_file_live_pid_detected(tmp_path: Path) -> None:
    """LOCK-7 when lock has a live pid but no session file on disk."""
    ctx = _ctx("proj", state=ContextState.ALIVE)
    (tmp_path / "repos" / "proj").mkdir(parents=True)

    # Lock with current (live) pid but NO matching session file
    _make_lock_file(tmp_path, "proj", "v1", "sess_nosess01", pid=os.getpid())
    # Intentionally NO session file created

    svc, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    codes = {i.code for i in issues}
    assert "LOCK-7" in codes, f"Expected LOCK-7 for missing session file (live pid), got: {codes}"

    lock7 = next(i for i in issues if i.code == "LOCK-7")
    assert lock7.fixable is True
    assert "proj" in lock7.description or "sess_nosess01" in lock7.description


# ---------------------------------------------------------------------------
# LOCK-7: missing session file (dead pid — orphan AND stale)
# ---------------------------------------------------------------------------


def test_lock7_missing_session_file_dead_pid_detected(tmp_path: Path) -> None:
    """LOCK-7 also fires when lock has dead pid and no session file (orphan).

    Note: LOCK-3 may also fire since dead pid → STALE state.
    LOCK-7 is the specific orphan code (session absent) regardless of pid state.
    """
    ctx = _ctx("proj", state=ContextState.ALIVE)
    (tmp_path / "repos" / "proj").mkdir(parents=True)

    dead_pid = 9_999_999
    _make_lock_file(tmp_path, "proj", "v1", "sess_dead01", pid=dead_pid)
    # No session file — orphan

    svc, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    codes = {i.code for i in issues}
    assert "LOCK-7" in codes, f"Expected LOCK-7 for missing session file, got: {codes}"

    lock7 = next(i for i in issues if i.code == "LOCK-7")
    assert lock7.fixable is True


# ---------------------------------------------------------------------------
# LOCK-7 does NOT fire when session file is present (even if pid dead → LOCK-3)
# ---------------------------------------------------------------------------


def test_lock7_not_fired_when_session_file_present_pid_dead(tmp_path: Path) -> None:
    """No LOCK-7 when session file exists; dead pid → LOCK-3 only."""
    ctx = _ctx("proj", state=ContextState.ALIVE)
    (tmp_path / "repos" / "proj").mkdir(parents=True)

    dead_pid = 9_999_999
    _make_lock_file(tmp_path, "proj", "v1", "sess_dead02", pid=dead_pid)
    # Session file IS present (different from orphan)
    _make_session_file(tmp_path, "sess_dead02", "proj", "v1", pid=dead_pid)

    svc, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    codes = {i.code for i in issues}

    # LOCK-3 fires for dead pid (check_lock_state returns STALE)
    assert "LOCK-3" in codes, f"Expected LOCK-3 for dead pid, got: {codes}"
    # LOCK-7 should NOT fire — session file is present
    assert "LOCK-7" not in codes, f"LOCK-7 must not fire when session file is present: {codes}"


# ---------------------------------------------------------------------------
# LOCK-7 fix reclaims orphan lock and writes audit trail
# ---------------------------------------------------------------------------


def test_lock7_fix_reclaims_orphan_live_pid(tmp_path: Path) -> None:
    """fix() removes orphan lock (live pid, no session file) and appends audit."""
    ctx = _ctx("proj", state=ContextState.ALIVE)
    (tmp_path / "repos" / "proj").mkdir(parents=True)

    lock_file = _make_lock_file(tmp_path, "proj", "v1", "sess_nosess02", pid=os.getpid())
    # No session file

    svc, _ = _make_doctor(tmp_path, [ctx])

    # Verify check sees LOCK-7
    issues = svc.check()
    assert any(i.code == "LOCK-7" for i in issues)

    # Fix
    actions = svc.fix()

    # Lock file must be removed
    assert not lock_file.exists(), "Orphan lock file should be removed by fix()"
    assert any("LOCK-7" in a or "orphan" in a.lower() for a in actions)


def test_lock7_fix_appends_audit_trail(tmp_path: Path) -> None:
    """fix() appends an audit log entry for orphan lock reclaim."""
    ctx = _ctx("proj", state=ContextState.ALIVE)
    (tmp_path / "repos" / "proj").mkdir(parents=True)

    _make_lock_file(tmp_path, "proj", "v1", "sess_audit01", pid=os.getpid())
    # No session file

    svc, _ = _make_doctor(tmp_path, [ctx])
    svc.fix()

    audit_path = _audit_log_path(tmp_path)
    assert audit_path.exists(), "Audit log should exist after fix()"
    lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 1
    events = [json.loads(ln) for ln in lines]
    orphan_events = [
        e for e in events if "ORPHAN" in e.get("event", "") or "orphan" in str(e).lower()
    ]
    assert orphan_events, f"Expected at least one orphan audit event, got: {events}"


# ---------------------------------------------------------------------------
# LOCK-7 does NOT fire for DEAD-context locks (LOCK-2 handles those)
# ---------------------------------------------------------------------------


def test_lock7_dead_context_is_lock2_not_lock7(tmp_path: Path) -> None:
    """A lock for a DEAD context gets LOCK-2; LOCK-7 is not raised separately."""
    ctx = _ctx("proj", state=ContextState.DEAD)  # DEAD context

    _make_lock_file(tmp_path, "proj", "v1", "sess_dead03", pid=os.getpid())
    # No session file — would normally trigger LOCK-7 for ALIVE context

    svc, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    codes = {i.code for i in issues}

    # LOCK-2 fires for DEAD context + impl lock
    assert "LOCK-2" in codes, f"Expected LOCK-2 for dead context, got: {codes}"
    # LOCK-7 should NOT fire separately (LOCK-2 already covers this lock)
    assert "LOCK-7" not in codes, f"LOCK-7 should not fire for DEAD-context case: {codes}"
