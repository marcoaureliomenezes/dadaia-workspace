"""Two-layer locking for Spec Context Projects (v0.1.6: Lock-3 removed).

Lock 1 — workspace-wide fcntl lock (.dadaia/states/.ws_lock)
    Wraps ALL load→mutate→dump operations on spec_contexts.json.
    Timeout: 5 seconds.  On timeout: WorkspaceLockTimeoutError.

Lock 2 — per-context fcntl lock (.dadaia/states/ctx_locks/<slug>.lock)
    Wraps git clone, shutil.rmtree, git push for a single context slug.
    Two different slugs lock independently (parallel OK).
    Same slug: exclusive (clone+rmtree cannot race).

Lock 3 (removed in v0.1.6) — replaced by single-record TTL-lease in lease.py.

Audit log — .dadaia/logs/lock-events.jsonl
    ONE JSON object per line, written with O_APPEND (atomic under PIPE_BUF).
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.exceptions import (
    WorkspaceLockTimeoutError,
)

logger = __import__("logging").getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOCK_TIMEOUT_SECONDS = 5.0
_LOCK_POLL_INTERVAL = 0.05  # 50 ms between retries

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _ws_lock_path(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "states" / ".ws_lock"


def _ctx_lock_path(workspace_root: Path, repo_slug: str) -> Path:
    return workspace_root / ".dadaia" / "states" / "ctx_locks" / f"{repo_slug}.lock"


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
# Audit log helpers (shared with lease.py)
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


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

    record: dict[str, object] = {
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
