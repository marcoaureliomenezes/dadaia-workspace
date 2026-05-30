"""Three-layer locking for Spec Context Projects (ADR D-4).

Lock 1 — workspace-wide fcntl lock (.dadaia/states/.ws_lock)
    Wraps ALL load→mutate→dump operations on spec_contexts.json.
    Timeout: 5 seconds.  On timeout: WorkspaceLockTimeoutError.

Lock 2 — per-context fcntl lock (.dadaia/states/ctx_locks/<slug>.lock)
    Wraps git clone, shutil.rmtree, git push for a single context slug.
    Two different slugs lock independently (parallel OK).
    Same slug: exclusive (clone+rmtree cannot race).

Lock 3 — per-release implementation lock (JSON state machine)
    File: .dadaia/locks/implementation/<context>__<release>.json
    States: FREE → HELD → STALE → RECLAIMED
    Heartbeat and full TTL renewal are T-12; we implement detection here.

Audit log — .dadaia/logs/lock-events.jsonl
    ONE JSON object per line, written with O_APPEND (atomic under PIPE_BUF).
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.exceptions import (
    ImplementationBlockedByReviewError,
    LockActiveError,
    LockHeldError,
    ReviewBlockedByImplementationError,
    WorkspaceLockTimeoutError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOCK_TIMEOUT_SECONDS = 5.0
_LOCK_POLL_INTERVAL = 0.05  # 50 ms between retries
_LOCK_TTL_DEFAULT = 300  # seconds (Lock 3 default TTL)

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _ws_lock_path(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "states" / ".ws_lock"


def _ctx_lock_path(workspace_root: Path, repo_slug: str) -> Path:
    return workspace_root / ".dadaia" / "states" / "ctx_locks" / f"{repo_slug}.lock"


def _impl_lock_path(workspace_root: Path, context: str, release: str) -> Path:
    return workspace_root / ".dadaia" / "locks" / "implementation" / f"{context}__{release}.json"


def _audit_log_path(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "logs" / "lock-events.jsonl"


# ---------------------------------------------------------------------------
# Lock 1 — workspace-wide fcntl
# ---------------------------------------------------------------------------


def _acquire_flock(fd: int, path: str, timeout: float = _LOCK_TIMEOUT_SECONDS) -> None:
    """Attempt to acquire LOCK_EX|LOCK_NB in a retry loop with *timeout* seconds.

    We poll every _LOCK_POLL_INTERVAL seconds rather than calling time.sleep for
    long intervals so the total wait stays bounded and the code stays testable.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            pass
        if time.monotonic() >= deadline:
            # Try to read the PID from the lock file content (best-effort)
            holder_pid: int | None = None
            with contextlib.suppress(Exception), open(path) as fh:
                holder_pid = int(fh.read().strip())
            raise WorkspaceLockTimeoutError(
                f"Could not acquire workspace lock '{path}' within {timeout}s. "
                + (f"Holder PID: {holder_pid}." if holder_pid else "Holder PID unknown.")
            )
        time.sleep(_LOCK_POLL_INTERVAL)


@contextmanager
def workspace_lock(workspace_root: Path) -> Generator[None, None, None]:
    """Context manager: acquires the workspace-wide fcntl exclusive lock.

    File: .dadaia/states/.ws_lock
    Holds for the duration of the ``with`` block; releases on exit.

    Raises:
        WorkspaceLockTimeoutError: Lock not acquired within 5 seconds.
    """
    lock_path = _ws_lock_path(workspace_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        # Write current PID so other waiters can report holder PID in errors.
        os.write(fd, str(os.getpid()).encode())
        _acquire_flock(fd, str(lock_path))
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


# ---------------------------------------------------------------------------
# Lock 2 — per-context fcntl
# ---------------------------------------------------------------------------


@contextmanager
def context_lock(workspace_root: Path, repo_slug: str) -> Generator[None, None, None]:
    """Context manager: acquires the per-context fcntl exclusive lock.

    File: .dadaia/states/ctx_locks/<repo_slug>.lock
    Two different slugs lock independently; same slug is exclusive.

    Raises:
        WorkspaceLockTimeoutError: Lock not acquired within 5 seconds.
    """
    lock_path = _ctx_lock_path(workspace_root, repo_slug)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        os.write(fd, str(os.getpid()).encode())
        _acquire_flock(fd, str(lock_path))
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


# ---------------------------------------------------------------------------
# Lock 3 — per-release implementation lock (JSON state machine)
# ---------------------------------------------------------------------------


class LockState:
    FREE = "FREE"
    HELD = "HELD"
    STALE = "STALE"
    RECLAIMED = "RECLAIMED"


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _is_pid_alive(pid: int) -> bool:
    """Return True if *pid* is alive (conservative: PermissionError → alive)."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # alive but unprobable (e.g. root-owned)
    except OSError:
        return True  # conservative


def check_lock_state(workspace_root: Path, context: str, release: str) -> str:
    """Return the current Lock 3 state for *context*/*release*.

    FREE    — no lock file.
    HELD    — file exists, last_seen_at within ttl, AND pid alive.
    STALE   — file exists but ttl exceeded OR pid dead.
    """
    lock_path = _impl_lock_path(workspace_root, context, release)
    if not lock_path.exists():
        return LockState.FREE

    try:
        data = json.loads(lock_path.read_text())
    except (json.JSONDecodeError, OSError):
        return LockState.STALE  # unreadable file = treat as stale

    ttl = int(data.get("ttl_seconds", _LOCK_TTL_DEFAULT))
    last_seen_raw = data.get("last_seen_at", "")
    pid = data.get("pid")

    # PID liveness fast-path
    if pid is not None and not _is_pid_alive(int(pid)):
        return LockState.STALE

    # TTL check
    if last_seen_raw:
        try:
            last_seen = datetime.fromisoformat(last_seen_raw.replace("Z", "+00:00"))
            elapsed = (datetime.now(tz=UTC) - last_seen).total_seconds()
            if elapsed > ttl:
                return LockState.STALE
        except ValueError:
            return LockState.STALE

    return LockState.HELD


def create_impl_lock(
    workspace_root: Path,
    context: str,
    release: str,
    session_id: str,
    runtime: str,
    pid: int,
    task_path: str = "",
    owner_note: str = "",
) -> dict:  # type: ignore[type-arg]
    """Create a Lock 3 implementation lock file atomically.

    Checks current state; raises LockHeldError if already HELD.

    Returns the lock data dict on success.
    """
    state = check_lock_state(workspace_root, context, release)
    if state == LockState.HELD:
        lock_path = _impl_lock_path(workspace_root, context, release)
        try:
            existing = json.loads(lock_path.read_text())
            owner_id = existing.get("session_id", "unknown")
            owner_last_seen = existing.get("last_seen_at", "unknown")
        except Exception:
            owner_id = "unknown"
            owner_last_seen = "unknown"
        raise LockHeldError(
            f"Implementation lock for '{context}/{release}' is already HELD by "
            f"session '{owner_id}' (last_seen_at: {owner_last_seen}). "
            "Run 'dadaia context release' in the owning session or wait for it to expire."
        )

    now = _now_iso()
    lock_data: dict = {  # type: ignore[type-arg]
        "lock_type": "implementation",
        "context": context,
        "release": release,
        "session_id": session_id,
        "runtime": runtime,
        "pid": pid,
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": now,
        "last_seen_at": now,
        "ttl_seconds": _LOCK_TTL_DEFAULT,
        "task_path": task_path,
        "owner_note": owner_note,
    }

    lock_path = _impl_lock_path(workspace_root, context, release)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write via tmp → os.replace
    tmp = lock_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(lock_data, indent=2))
    os.replace(tmp, lock_path)

    return lock_data


def release_impl_lock(
    workspace_root: Path,
    context: str,
    release: str,
    session_id: str,
) -> bool:
    """Delete the Lock 3 file if this *session_id* owns it.

    Returns True if deleted, False if not owned or not found.
    """
    lock_path = _impl_lock_path(workspace_root, context, release)
    if not lock_path.exists():
        return False
    try:
        data = json.loads(lock_path.read_text())
        if data.get("session_id") != session_id:
            return False
        lock_path.unlink(missing_ok=True)
        return True
    except (json.JSONDecodeError, OSError):
        lock_path.unlink(missing_ok=True)
        return True


def reclaim_impl_lock(
    workspace_root: Path,
    context: str,
    release: str,
    new_session_id: str,
    runtime: str,
    pid: int,
    reason: str,
    task_path: str = "",
    owner_note: str = "",
) -> dict:  # type: ignore[type-arg]
    """Force-reclaim a STALE Lock 3 file.

    Raises LockActiveError if the lock is HELD (not stale).
    Writes STALE_DETECTED + RECLAIMED audit events.
    """
    state = check_lock_state(workspace_root, context, release)
    if state == LockState.HELD:
        raise LockActiveError(
            f"Cannot reclaim: lock for '{context}/{release}' is still HELD (not stale). "
            "Use 'dadaia context release' or wait for the TTL to expire."
        )

    lock_path = _impl_lock_path(workspace_root, context, release)
    old_session_id = "unknown"
    if lock_path.exists():
        with contextlib.suppress(Exception):
            old_data = json.loads(lock_path.read_text())
            old_session_id = old_data.get("session_id", "unknown")
        # Emit STALE_DETECTED before overwriting
        _append_audit_event(
            workspace_root,
            event="STALE_DETECTED",
            context=context,
            release=release,
            session_id=old_session_id,
            runtime=runtime,
            pid=pid,
            reason=reason,
            reclaim_by=new_session_id,
        )

    now = _now_iso()
    new_lock_data: dict = {  # type: ignore[type-arg]
        "lock_type": "implementation",
        "context": context,
        "release": release,
        "session_id": new_session_id,
        "runtime": runtime,
        "pid": pid,
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": now,
        "last_seen_at": now,
        "ttl_seconds": _LOCK_TTL_DEFAULT,
        "task_path": task_path,
        "owner_note": owner_note,
    }

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = lock_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(new_lock_data, indent=2))
    os.replace(tmp, lock_path)

    _append_audit_event(
        workspace_root,
        event="RECLAIMED",
        context=context,
        release=release,
        session_id=new_session_id,
        runtime=runtime,
        pid=pid,
        reason=reason,
        reclaim_by=new_session_id,
    )

    return new_lock_data


def has_implementation_lock(workspace_root: Path, context_name: str) -> bool:
    """Return True if any HELD implementation lock exists for *context_name*.

    T-11: checks lock state (HELD = file + fresh + pid alive).
    Previously (T-10d): file existence was sufficient.
    """
    locks_dir = workspace_root / ".dadaia" / "locks" / "implementation"
    if not locks_dir.exists():
        return False
    prefix = f"{context_name}__"
    for f in locks_dir.iterdir():
        if f.is_file() and f.name.startswith(prefix):
            # Extract release from filename: <context>__<release>.json
            stem = f.stem  # e.g. "proj__v1"
            release = stem[len(prefix):]
            state = check_lock_state(workspace_root, context_name, release)
            if state == LockState.HELD:
                return True
    return False


def find_review_sessions(
    workspace_root: Path, context_name: str, release: str
) -> list[str]:
    """Return session IDs of non-stale BOUND_REVIEW sessions for context/release."""
    sessions_dir = workspace_root / ".dadaia" / "sessions"
    if not sessions_dir.exists():
        return []
    review_session_ids: list[str] = []
    for f in sessions_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if (
            data.get("mode") == "BOUND_REVIEW"
            and data.get("context") == context_name
            and data.get("release") == release
            and not _session_is_stale(data)
        ):
            review_session_ids.append(data["session_id"])
    return review_session_ids


def _session_is_stale(session_data: dict) -> bool:  # type: ignore[type-arg]
    """Return True if the session's last_seen_at is beyond its TTL."""
    try:
        last_seen = session_data.get("last_seen_at", "")
        ttl = int(session_data.get("ttl_seconds", 300))
        if not last_seen:
            return False
        last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        elapsed = (datetime.now(tz=UTC) - last_seen_dt).total_seconds()
        return elapsed > ttl
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Impl-XOR-Review guard helpers
# ---------------------------------------------------------------------------


def check_impl_xor_review(
    workspace_root: Path,
    context: str,
    release: str,
    mode: str,
    session_id: str,
) -> None:
    """Enforce Impl-XOR-Review mutual exclusion for IMPLEMENTATION and REVIEW modes.

    Args:
        workspace_root: workspace root path.
        context: context name.
        release: release ID.
        mode: "IMPLEMENTATION" or "REVIEW" (uppercase).
        session_id: the new session being created (for error messages).

    Raises:
        ReviewBlockedByImplementationError: review bind while impl lock is HELD.
        ImplementationBlockedByReviewError: impl bind while non-stale BOUND_REVIEW exists.
    """
    if mode == "REVIEW":
        state = check_lock_state(workspace_root, context, release)
        if state == LockState.HELD:
            lock_path = _impl_lock_path(workspace_root, context, release)
            owner_id = "unknown"
            with contextlib.suppress(Exception):
                data = json.loads(lock_path.read_text())
                owner_id = data.get("session_id", "unknown")
            raise ReviewBlockedByImplementationError(
                f"Context '{context}' release '{release}' has an active implementation lock "
                f"held by session '{owner_id}'. "
                "Review cannot proceed while implementation is in progress."
            )

    elif mode == "IMPLEMENTATION":
        blocking_reviews = find_review_sessions(workspace_root, context, release)
        if blocking_reviews:
            raise ImplementationBlockedByReviewError(
                f"Context '{context}' release '{release}' is blocked by active BOUND_REVIEW "
                f"session(s): {', '.join(blocking_reviews)}. "
                "Wait for the review to complete before starting implementation."
            )


# ---------------------------------------------------------------------------
# Audit log (Lock 3 / AC-AUDIT-1)
# ---------------------------------------------------------------------------


def _append_audit_event(
    workspace_root: Path,
    *,
    event: str,
    context: str,
    release: str,
    session_id: str,
    runtime: str,
    pid: int,
    reason: str = "",
    reclaim_by: str = "",
    fpath: str = "",
) -> None:
    """Append one audit event to .dadaia/logs/lock-events.jsonl using O_APPEND.

    Records are <1 KB (well under PIPE_BUF on Linux = 4096 bytes), so each
    os.write() call is atomic with O_APPEND.
    """
    audit_path = _audit_log_path(workspace_root)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    record: dict = {  # type: ignore[type-arg]
        "ts": _now_iso(),
        "event": event,
        "context": context,
        "release": release,
        "session_id": session_id,
        "runtime": runtime,
        "pid": pid,
        "reason": reason,
        "reclaim_by": reclaim_by,
        "fpath": fpath,
    }
    line = json.dumps(record) + "\n"
    encoded = line.encode("utf-8")

    fd = os.open(str(audit_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, encoded)
    finally:
        os.close(fd)


def audit_acquired(
    workspace_root: Path,
    *,
    context: str,
    release: str,
    session_id: str,
    runtime: str,
    pid: int,
) -> None:
    _append_audit_event(
        workspace_root,
        event="ACQUIRED",
        context=context,
        release=release,
        session_id=session_id,
        runtime=runtime,
        pid=pid,
    )


def audit_released(
    workspace_root: Path,
    *,
    context: str,
    release: str,
    session_id: str,
    runtime: str,
    pid: int,
) -> None:
    _append_audit_event(
        workspace_root,
        event="RELEASED",
        context=context,
        release=release,
        session_id=session_id,
        runtime=runtime,
        pid=pid,
    )


def audit_blocked(
    workspace_root: Path,
    *,
    context: str,
    release: str,
    session_id: str,
    runtime: str,
    pid: int,
    reason: str,
) -> None:
    _append_audit_event(
        workspace_root,
        event="BLOCKED_ATTEMPT",
        context=context,
        release=release,
        session_id=session_id,
        runtime=runtime,
        pid=pid,
        reason=reason,
    )
