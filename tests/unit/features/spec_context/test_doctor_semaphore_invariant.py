"""Unit tests for T-SEMA-02: doctor SEM-1 semaphore invariant + --fix reclaim.

Done criterion:
1. `dadaia doctor` detects an orphaned semaphore (context not in alive spec_contexts.json)
   and emits [orphan-semaphore] <path>.
2. `dadaia doctor` detects a stale-by-liveness semaphore and emits [stale-semaphore] <path>.
3. `dadaia doctor --fix` deletes flagged semaphores and appends to semaphore-reclaims.jsonl.
4. Four unit tests pass:
   - test_clean_state_no_warning
   - test_orphan_semaphore_flagged
   - test_stale_semaphore_flagged
   - test_fix_reclaims_and_logs
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from dadaia_workspace.features.spec_context.doctor import DoctorService
from tests.fakes import FakeContextStore, FakeGitClient

if TYPE_CHECKING:
    from dadaia_workspace.core.models.spec_context import SpecContextProject

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SEMAPHORE_AUDIT_PATH_RELATIVE = Path(
    ".dadaia" / Path("states") / "audit" / "semaphore-reclaims.jsonl"
)


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws


def _make_alive_ctx(name: str, repo_slug: str = "") -> SpecContextProject:
    from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject

    return SpecContextProject(
        name=name,
        repo_slug=repo_slug or name,
        repo_url=f"https://github.com/org/{repo_slug or name}",
        state=ContextState.ALIVE,
        created_at="2026-01-01T00:00:00Z",
    )


def _make_dead_ctx(name: str, repo_slug: str = "") -> SpecContextProject:
    from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject

    return SpecContextProject(
        name=name,
        repo_slug=repo_slug or name,
        repo_url=f"https://github.com/org/{repo_slug or name}",
        state=ContextState.DEAD,
        created_at="2026-01-01T00:00:00Z",
    )


def _make_doctor(workspace: Path, store: FakeContextStore) -> DoctorService:
    return DoctorService(
        context_store=store,
        git_client=FakeGitClient(),
        workspace_root=workspace,
    )


def _write_semaphore(
    workspace: Path,
    context: str,
    data: dict,  # type: ignore[type-arg]
) -> Path:
    """Write semaphore data to the canonical path."""
    sem_path = workspace / ".dadaia" / "states" / "ctx_locks" / f"{context}.semaphore.json"
    sem_path.parent.mkdir(parents=True, exist_ok=True)
    sem_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return sem_path


def _write_session_file(workspace: Path, session_id: str) -> Path:
    sessions_dir = workspace / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_path = sessions_dir / f"{session_id}.json"
    session_path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "pid": os.getpid(),
                "mode": "BOUND_IMPLEMENTATION",
            }
        ),
        encoding="utf-8",
    )
    return session_path


def _live_semaphore_data(
    owner: str = "sess_live",
    *,
    pid: int | None = None,
    ttl: int = 300,
    heartbeat_offset_seconds: float = 0.0,
) -> dict:  # type: ignore[type-arg]
    """Build a fresh semaphore dict (non-stale by default)."""
    heartbeat_dt = datetime.now(tz=UTC) + timedelta(seconds=heartbeat_offset_seconds)
    data: dict = {  # type: ignore[type-arg]
        "owner": owner,
        "phase": "BOUND_IMPLEMENTATION",
        "release": "v0.1.5",
        "write_set": [],
        "acquired_at": heartbeat_dt.isoformat(),
        "ttl": ttl,
        "heartbeat": heartbeat_dt.isoformat(),
    }
    if pid is not None:
        data["pid"] = pid
    return data


def _dead_pid() -> int:
    """Return a PID that is guaranteed not to be alive on this OS."""
    candidate = 9_999_999
    try:
        os.kill(candidate, 0)
        return 9_999_998
    except ProcessLookupError:
        return candidate
    except (PermissionError, OSError):
        return 9_999_998


# ---------------------------------------------------------------------------
# Test: clean state → no SEM-1 warnings
# ---------------------------------------------------------------------------


class TestCleanStateNoWarning:
    """T-SEMA-02 AC-1 & 2 baseline: no semaphore files → no SEM-1 issues."""

    def test_clean_state_no_warning(self, tmp_path: Path) -> None:
        """An empty ctx_locks dir produces no SEM-1 issues."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        doctor = _make_doctor(ws, store)

        issues = doctor.check()
        sem_issues = [i for i in issues if i.code.startswith("SEM-")]
        assert sem_issues == [], f"Expected no SEM-* issues on clean state, got: {sem_issues}"

    def test_live_semaphore_for_alive_context_no_warning(self, tmp_path: Path) -> None:
        """A live, non-stale semaphore for an alive context does not trigger SEM-1."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        ctx = _make_alive_ctx("myctx", "my-repo")
        store.save(ctx)

        live_pid = os.getpid()
        session_id = "sess_healthy"
        data = _live_semaphore_data(owner=session_id, pid=live_pid)
        _write_semaphore(ws, "myctx", data)
        _write_session_file(ws, session_id)

        doctor = _make_doctor(ws, store)
        issues = doctor.check()
        sem_issues = [i for i in issues if i.code.startswith("SEM-")]
        assert sem_issues == [], (
            f"Live semaphore for alive context should not flag SEM-1, got: {sem_issues}"
        )


# ---------------------------------------------------------------------------
# Test: orphan semaphore (context not in alive spec_contexts.json)
# ---------------------------------------------------------------------------


class TestOrphanSemaphoreFlagged:
    """T-SEMA-02 AC-1: orphan semaphore (unknown context) is flagged as [orphan-semaphore]."""

    def test_orphan_semaphore_flagged(self, tmp_path: Path) -> None:
        """A semaphore for a context not listed in spec_contexts.json triggers SEM-1 ORPHAN."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        # No context "ghost-ctx" registered in the store

        live_pid = os.getpid()
        session_id = "sess_ghost"
        data = _live_semaphore_data(owner=session_id, pid=live_pid)
        _write_semaphore(ws, "ghost-ctx", data)
        _write_session_file(ws, session_id)

        doctor = _make_doctor(ws, store)
        issues = doctor.check()
        sem_issues = [i for i in issues if i.code == "SEM-1"]
        assert sem_issues, "Expected at least one SEM-1 issue for orphan semaphore"
        descriptions = [i.description for i in sem_issues]
        assert any("orphan" in d.lower() for d in descriptions), (
            f"Expected 'orphan' in SEM-1 description, got: {descriptions}"
        )
        # Must be fixable
        assert all(i.fixable for i in sem_issues)

    def test_orphan_semaphore_for_dead_context_flagged(self, tmp_path: Path) -> None:
        """A semaphore for a DEAD context is also orphan-flagged (not in alive set)."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        ctx = _make_dead_ctx("dead-ctx", "dead-repo")
        store.save(ctx)

        live_pid = os.getpid()
        session_id = "sess_dead_ctx"
        data = _live_semaphore_data(owner=session_id, pid=live_pid)
        _write_semaphore(ws, "dead-ctx", data)
        _write_session_file(ws, session_id)

        doctor = _make_doctor(ws, store)
        issues = doctor.check()
        sem_issues = [i for i in issues if i.code == "SEM-1"]
        assert sem_issues, "Expected SEM-1 issue for semaphore belonging to DEAD context"


# ---------------------------------------------------------------------------
# Test: stale semaphore (dead pid or TTL-expired)
# ---------------------------------------------------------------------------


class TestStaleSemaphoreFlagged:
    """T-SEMA-02 AC-2: stale-by-liveness semaphore is flagged as [stale-semaphore]."""

    def test_stale_semaphore_dead_pid_flagged(self, tmp_path: Path) -> None:
        """A semaphore with a dead owner PID triggers SEM-1 STALE."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        ctx = _make_alive_ctx("myctx", "my-repo")
        store.save(ctx)

        dead = _dead_pid()
        try:
            os.kill(dead, 0)
            pytest.skip(f"PID {dead} unexpectedly alive")
        except ProcessLookupError:
            pass

        session_id = "sess_dead_pid"
        data = _live_semaphore_data(owner=session_id, pid=dead)
        _write_semaphore(ws, "myctx", data)
        _write_session_file(ws, session_id)  # session file exists; only PID is dead

        doctor = _make_doctor(ws, store)
        issues = doctor.check()
        sem_issues = [i for i in issues if i.code == "SEM-1"]
        assert sem_issues, "Expected SEM-1 for dead-pid semaphore"
        descriptions = [i.description for i in sem_issues]
        assert any("stale" in d.lower() for d in descriptions), (
            f"Expected 'stale' in SEM-1 description, got: {descriptions}"
        )
        assert all(i.fixable for i in sem_issues)

    def test_stale_semaphore_missing_session_flagged(self, tmp_path: Path) -> None:
        """A semaphore whose owner session file is missing triggers SEM-1 STALE."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        ctx = _make_alive_ctx("myctx", "my-repo")
        store.save(ctx)

        live_pid = os.getpid()
        session_id = "sess_gone"
        data = _live_semaphore_data(owner=session_id, pid=live_pid)
        _write_semaphore(ws, "myctx", data)
        # No session file for sess_gone

        doctor = _make_doctor(ws, store)
        issues = doctor.check()
        sem_issues = [i for i in issues if i.code == "SEM-1"]
        assert sem_issues, "Expected SEM-1 for missing-session semaphore"
        descriptions = [i.description for i in sem_issues]
        assert any("stale" in d.lower() for d in descriptions), (
            f"Expected 'stale' in description, got: {descriptions}"
        )

    def test_stale_semaphore_ttl_expired_flagged(self, tmp_path: Path) -> None:
        """A TTL-expired semaphore triggers SEM-1 STALE."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        ctx = _make_alive_ctx("myctx", "my-repo")
        store.save(ctx)

        live_pid = os.getpid()
        session_id = "sess_expired"
        data = _live_semaphore_data(
            owner=session_id,
            pid=live_pid,
            ttl=300,
            heartbeat_offset_seconds=-400.0,
        )
        _write_semaphore(ws, "myctx", data)
        _write_session_file(ws, session_id)

        doctor = _make_doctor(ws, store)
        issues = doctor.check()
        sem_issues = [i for i in issues if i.code == "SEM-1"]
        assert sem_issues, "Expected SEM-1 for TTL-expired semaphore"
        descriptions = [i.description for i in sem_issues]
        assert any("stale" in d.lower() for d in descriptions), (
            f"Expected 'stale' in description, got: {descriptions}"
        )


# ---------------------------------------------------------------------------
# Test: --fix reclaims and logs
# ---------------------------------------------------------------------------


class TestFixReclaims:
    """T-SEMA-02 AC-3: doctor --fix deletes flagged semaphores and appends audit."""

    def test_fix_reclaims_and_logs(self, tmp_path: Path) -> None:
        """fix() deletes a stale semaphore and appends to semaphore-reclaims.jsonl."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        ctx = _make_alive_ctx("myctx", "my-repo")
        store.save(ctx)

        dead = _dead_pid()
        try:
            os.kill(dead, 0)
            pytest.skip(f"PID {dead} unexpectedly alive")
        except ProcessLookupError:
            pass

        session_id = "sess_reclaim"
        data = _live_semaphore_data(owner=session_id, pid=dead)
        sem_path = _write_semaphore(ws, "myctx", data)
        _write_session_file(ws, session_id)

        doctor = _make_doctor(ws, store)

        # Confirm issue detected before fix
        issues = doctor.check()
        sem_issues = [i for i in issues if i.code == "SEM-1"]
        assert sem_issues, "Pre-condition: SEM-1 should be detected before fix()"

        # Run fix
        actions = doctor.fix()
        sem_actions = [a for a in actions if "SEM-1" in a or "semaphore" in a.lower()]
        assert sem_actions, f"Expected semaphore fix action, got: {actions}"

        # Semaphore file must be deleted
        assert not sem_path.exists(), (
            f"fix() should delete the stale semaphore file, but it still exists: {sem_path}"
        )

        # Audit log must be written
        audit_path = ws / ".dadaia" / "states" / "audit" / "semaphore-reclaims.jsonl"
        assert audit_path.exists(), (
            f"fix() must write audit log at {audit_path}, but it does not exist"
        )
        lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
        assert lines, "Audit log must have at least one entry"
        record = json.loads(lines[-1])
        assert record.get("context") == "myctx", (
            f"Audit entry must record context='myctx', got: {record}"
        )
        assert record.get("session_id") == session_id, (
            f"Audit entry must record session_id='{session_id}', got: {record}"
        )

    def test_fix_reclaims_orphan_semaphore_and_logs(self, tmp_path: Path) -> None:
        """fix() deletes an orphan semaphore (unknown context) and logs it."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        # No context "ghost-ctx" registered

        live_pid = os.getpid()
        session_id = "sess_orphan"
        data = _live_semaphore_data(owner=session_id, pid=live_pid)
        sem_path = _write_semaphore(ws, "ghost-ctx", data)
        _write_session_file(ws, session_id)

        doctor = _make_doctor(ws, store)
        actions = doctor.fix()
        sem_actions = [a for a in actions if "SEM-1" in a or "semaphore" in a.lower()]
        assert sem_actions, f"Expected orphan semaphore reclaim action, got: {actions}"
        assert not sem_path.exists(), "fix() should delete the orphan semaphore file"

        audit_path = ws / ".dadaia" / "states" / "audit" / "semaphore-reclaims.jsonl"
        assert audit_path.exists(), "Audit log must exist after fix()"
        lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
        assert lines, "Audit log must have entries"

    def test_fix_does_not_touch_live_semaphore(self, tmp_path: Path) -> None:
        """fix() leaves a live, non-stale, alive-context semaphore untouched."""
        ws = _make_workspace(tmp_path)
        store = FakeContextStore()
        ctx = _make_alive_ctx("myctx", "my-repo")
        store.save(ctx)

        live_pid = os.getpid()
        session_id = "sess_live"
        data = _live_semaphore_data(owner=session_id, pid=live_pid)
        sem_path = _write_semaphore(ws, "myctx", data)
        _write_session_file(ws, session_id)

        doctor = _make_doctor(ws, store)
        actions = doctor.fix()
        sem_actions = [a for a in actions if "SEM-1" in a or "semaphore" in a.lower()]
        assert sem_actions == [], f"fix() should NOT touch a live semaphore, but got: {sem_actions}"
        assert sem_path.exists(), "fix() must not delete a live semaphore"
