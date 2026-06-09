"""Two-layer locking for Spec Context Projects (v0.1.6: Lock-3 removed).

Lock 1 — workspace-wide lock (.dadaia/states/.ws_lock)
    Wraps ALL load→mutate→dump operations on spec_contexts.json.
    Timeout: 5 seconds.  On timeout: WorkspaceLockTimeoutError.

Lock 2 — per-context lock (.dadaia/states/ctx_locks/<slug>.lock)
    Wraps git clone, shutil.rmtree, git push for a single context slug.
    Two different slugs lock independently (parallel OK).
    Same slug: exclusive (clone+rmtree cannot race).

Lock 3 (removed in v0.1.6) — replaced by single-record TTL-lease in lease.py.

Audit log — .dadaia/logs/lock-events.jsonl
    ONE JSON object per line, written with O_APPEND (atomic under PIPE_BUF).

Platform note (v0.1.8):
    The ``fcntl`` dependency has been moved to
    ``dadaia_workspace.infrastructure.file_lock_posix`` (LV-1 in SPEC §4.2).
    ``workspace_lock`` and ``context_lock`` delegate to the injected adapter
    via a lazy in-body default (ADR-1 transitional pattern).
    ``_acquire_flock`` is NOT re-exported from this module; tests that need it
    import it from ``dadaia_workspace.infrastructure.file_lock_posix`` directly.
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from dadaia_workspace.core.exceptions import (
    WorkspaceLockTimeoutError as WorkspaceLockTimeoutError,  # noqa: F401 — re-exported for callers
)

if TYPE_CHECKING:
    from dadaia_workspace.core.protocols.file_lock import ContextLock, WorkspaceLock

logger = __import__("logging").getLogger(__name__)

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
# Lazy adapter factory (ADR-1 transitional pattern)
# ---------------------------------------------------------------------------


def _default_workspace_lock() -> WorkspaceLock:
    """Return the platform-appropriate WorkspaceLock adapter.

    Uses an in-body sys.platform check (module-level read is forbidden per SPEC §4.1).

    TODO: Replace with PLATFORM.has_fcntl once PLATFORM is stable in T-018-05 callers.
    """
    import sys  # noqa: PLC0415 — intentional lazy import per ADR-1

    if sys.platform == "win32":  # TODO: replace with PLATFORM.has_fcntl once stable
        from dadaia_workspace.infrastructure.file_lock_windows import WindowsWorkspaceLock

        return WindowsWorkspaceLock()
    from dadaia_workspace.infrastructure.file_lock_posix import PosixWorkspaceLock

    return PosixWorkspaceLock()


def _default_context_lock() -> ContextLock:
    """Return the platform-appropriate ContextLock adapter.

    Uses an in-body sys.platform check (module-level read is forbidden per SPEC §4.1).

    TODO: Replace with PLATFORM.has_fcntl once PLATFORM is stable in T-018-05 callers.
    """
    import sys  # noqa: PLC0415 — intentional lazy import per ADR-1

    if sys.platform == "win32":  # TODO: replace with PLATFORM.has_fcntl once stable
        from dadaia_workspace.infrastructure.file_lock_windows import WindowsContextLock

        return WindowsContextLock()
    from dadaia_workspace.infrastructure.file_lock_posix import PosixContextLock

    return PosixContextLock()


# ---------------------------------------------------------------------------
# Lock 1 — workspace-wide lock (delegates to adapter)
# ---------------------------------------------------------------------------


@contextmanager
def workspace_lock(
    workspace_root: Path,
    *,
    _lock: WorkspaceLock | None = None,
) -> Generator[None, None, None]:
    """Context manager: acquires the workspace-wide exclusive lock.

    File: .dadaia/states/.ws_lock
    Holds for the duration of the ``with`` block; releases on exit.

    Args:
        workspace_root: Root directory of the initialized dadaia workspace.
        _lock: Optional injected lock adapter (for testing).  When ``None``
               the platform-appropriate adapter is selected automatically.

    Raises:
        WorkspaceLockTimeoutError: Lock not acquired within 5 seconds.
    """
    adapter = _lock if _lock is not None else _default_workspace_lock()
    with adapter.acquire(workspace_root):
        yield


# ---------------------------------------------------------------------------
# Lock 2 — per-context lock (delegates to adapter)
# ---------------------------------------------------------------------------


@contextmanager
def context_lock(
    workspace_root: Path,
    repo_slug: str,
    *,
    _lock: ContextLock | None = None,
) -> Generator[None, None, None]:
    """Context manager: acquires the per-context exclusive lock.

    File: .dadaia/states/ctx_locks/<repo_slug>.lock
    Two different slugs lock independently; same slug is exclusive.

    Args:
        workspace_root: Root directory of the initialized dadaia workspace.
        repo_slug:      Context identifier (repo slug).
        _lock: Optional injected lock adapter (for testing).  When ``None``
               the platform-appropriate adapter is selected automatically.

    Raises:
        WorkspaceLockTimeoutError: Lock not acquired within 5 seconds.
    """
    adapter = _lock if _lock is not None else _default_context_lock()
    with adapter.acquire(workspace_root, repo_slug):
        yield


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
