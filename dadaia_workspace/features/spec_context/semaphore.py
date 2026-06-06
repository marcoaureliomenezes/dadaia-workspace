"""Per-context semaphore for SDD implementation+review gate (T-R1-02).

Implements a JSON-based semaphore at:
    .dadaia/states/ctx_locks/<context>.semaphore.json

Fields:
    owner       - session_id of the holder
    phase       - mode: BOUND_IMPLEMENTATION or BOUND_REVIEW
    release     - release id being worked on
    write_set   - list of glob patterns the holder may write
    acquired_at - ISO 8601 timestamp when acquired
    ttl         - TTL in seconds (default 300)
    heartbeat   - ISO 8601 timestamp of last renewal

Semantics:
    - At most one BOUND_IMPLEMENTATION or BOUND_REVIEW holder per context.
    - READ and SPEC phases are never blocked (bypass the semaphore).
    - A stale semaphore (heartbeat > TTL) can be reclaimed.
    - Atomic writes via tmp → os.replace.

This semaphore is complementary to the fcntl context_lock (locking.py Lock 2)
and the per-release implementation lock (locking.py Lock 3). It provides a
higher-level "is any writing session active on this context?" guard.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "ContextSemaphoreError",
    "SemaphoreAlreadyHeldError",
    "acquire_context_semaphore",
    "renew_context_semaphore",
    "release_context_semaphore",
    "is_semaphore_held",
    "read_semaphore",
]

# Phases that bypass the semaphore entirely (never blocked).
_BYPASS_PHASES: frozenset[str] = frozenset({"READ", "SPEC"})

# Phases that require the semaphore (mutual exclusion).
_EXCLUSIVE_PHASES: frozenset[str] = frozenset({"BOUND_IMPLEMENTATION", "BOUND_REVIEW"})

_DEFAULT_TTL = 300  # seconds


class ContextSemaphoreError(Exception):
    """Base for all context semaphore errors."""


class SemaphoreAlreadyHeldError(ContextSemaphoreError):
    """Raised when a second exclusive session tries to acquire a held semaphore."""


def _semaphore_path(workspace_root: Path, context: str) -> Path:
    return workspace_root / ".dadaia" / "states" / "ctx_locks" / f"{context}.semaphore.json"


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
        return True  # alive but un-ownable (e.g. root-owned)
    except OSError:
        return True  # conservative


def _sessions_dir(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "sessions"


def _safe_session_filename(owner: str) -> str:
    """Sanitize an owner/session id before path construction (CWE-22).

    ``owner`` is read from the semaphore JSON on disk; strip anything outside the
    session-id charset so a crafted ``owner`` (e.g. ``../../etc``) cannot escape
    the sessions directory when its session file is existence-checked.
    """
    return "".join(c for c in owner if c.isalnum() or c in "_-")


def _is_stale(
    data: dict,  # type: ignore[type-arg]
    workspace_root: Path | None = None,
) -> bool:
    """Return True if the semaphore is stale.

    A semaphore is stale when ANY of the following hold:
    1. The owner's PID is not alive (``data["pid"]`` checked via ``os.kill(pid, 0)``).
    2. The owner's session file (``.dadaia/sessions/<owner>.json``) does not exist.
    3. The heartbeat timestamp has exceeded the TTL (existing TTL-only behavior).

    Checks are applied in order; the first True short-circuits.

    Args:
        data: Semaphore data dict (deserialized JSON).
        workspace_root: Optional workspace root used to locate session files.
            When ``None``, PID and session-file liveness checks are skipped and
            only the TTL check applies (preserving backward-compat for callers
            that do not pass the workspace root).
    """
    # ------------------------------------------------------------------
    # Liveness checks (T-SEMA-01) — require workspace_root to locate files.
    # ------------------------------------------------------------------
    if workspace_root is not None:
        pid_raw = data.get("pid")
        if pid_raw is not None:
            try:
                pid = int(pid_raw)
                # Check 1: dead PID → stale immediately.
                if not _is_pid_alive(pid):
                    return True

                # Check 2: PID is alive but session file is absent → stale.
                # Session files are written by the bind command; an alive process
                # that has no session file is an orphan holder.  We only apply this
                # check when a pid is present so that lightweight callers (e.g.
                # unit tests that call acquire_context_semaphore directly without
                # going through the full bind flow) are not mis-classified as stale.
                owner = _safe_session_filename(str(data.get("owner", "")))
                if owner:
                    session_file = _sessions_dir(workspace_root) / f"{owner}.json"
                    if not session_file.exists():
                        return True
            except (TypeError, ValueError):
                pass

    # ------------------------------------------------------------------
    # TTL check (original behavior — always applies).
    # ------------------------------------------------------------------
    try:
        heartbeat_raw = data.get("heartbeat", "")
        ttl = int(data.get("ttl", _DEFAULT_TTL))
        if not heartbeat_raw:
            return False
        heartbeat_dt = datetime.fromisoformat(heartbeat_raw.replace("Z", "+00:00"))
        elapsed = (datetime.now(tz=UTC) - heartbeat_dt).total_seconds()
        return elapsed > ttl
    except Exception:
        return False


def read_semaphore(workspace_root: Path, context: str) -> dict | None:  # type: ignore[type-arg]
    """Read the semaphore data. Returns None if absent or unreadable."""
    path = _semaphore_path(workspace_root, context)
    if not path.exists():
        return None
    try:
        result: dict = json.loads(path.read_text(encoding="utf-8"))  # type: ignore[type-arg]
        return result
    except (json.JSONDecodeError, OSError):
        return None


def is_semaphore_held(workspace_root: Path, context: str) -> bool:
    """Return True if the semaphore is currently HELD (present and non-stale)."""
    data = read_semaphore(workspace_root, context)
    if data is None:
        return False
    return not _is_stale(data, workspace_root=workspace_root)


def acquire_context_semaphore(
    workspace_root: Path,
    context: str,
    session_id: str,
    phase: str = "BOUND_IMPLEMENTATION",
    release: str = "",
    write_set: list[str] | None = None,
    ttl: int = _DEFAULT_TTL,
) -> dict:  # type: ignore[type-arg]
    """Acquire the per-context semaphore.

    READ and SPEC phases are never blocked — this function is a no-op for them
    (returns an empty dict since no semaphore is written).

    For BOUND_IMPLEMENTATION and BOUND_REVIEW:
    - If no semaphore exists or it is stale: write the semaphore and return data.
    - If a non-stale semaphore exists and is owned by a different session:
      raise SemaphoreAlreadyHeldError naming the holder.
    - If owned by the same session (idempotent re-acquire): update heartbeat.

    Args:
        workspace_root: workspace root path
        context: context name
        session_id: the acquiring session's ID
        phase: session mode (READ/SPEC bypass; BOUND_IMPLEMENTATION/BOUND_REVIEW exclusive)
        release: active release ID (informational)
        write_set: list of glob patterns this session may write (informational)
        ttl: TTL in seconds for heartbeat staleness check

    Returns:
        Semaphore data dict (empty dict for bypass phases).

    Raises:
        SemaphoreAlreadyHeldError: if a non-stale semaphore is held by another session.
    """
    # Bypass for read/spec phases
    if phase in _BYPASS_PHASES:
        return {}

    sem_path = _semaphore_path(workspace_root, context)
    sem_path.parent.mkdir(parents=True, exist_ok=True)

    # Check existing semaphore
    existing = read_semaphore(workspace_root, context)
    if existing is not None:
        stale = _is_stale(existing, workspace_root=workspace_root)
        if stale:
            # Stale by TTL, dead PID, or missing session — reclaim with audit log.
            holder = existing.get("owner", "unknown")
            reason_parts: list[str] = []
            pid_raw = existing.get("pid")
            if pid_raw is not None:
                try:
                    if not _is_pid_alive(int(pid_raw)):
                        reason_parts.append(f"dead-pid={pid_raw}")
                except (TypeError, ValueError):
                    pass
            if not reason_parts:
                owner_str = _safe_session_filename(str(holder))
                session_file = _sessions_dir(workspace_root) / f"{owner_str}.json"
                if not session_file.exists():
                    reason_parts.append("missing-session-file")
            if not reason_parts:
                reason_parts.append("ttl-expired")
            reason = ",".join(reason_parts)
            logger.info(
                "Reclaiming stale semaphore for context '%s' (holder=%s, reason=%s)",
                context,
                holder,
                reason,
            )
        elif existing.get("owner") != session_id:
            holder = existing.get("owner", "unknown")
            raise SemaphoreAlreadyHeldError(
                f"Context '{context}' semaphore is already held by session '{holder}' "
                f"(phase={existing.get('phase', 'unknown')}, "
                f"release={existing.get('release', 'unknown')}, "
                f"acquired_at={existing.get('acquired_at', 'unknown')}). "
                "Wait for the holder to release or its TTL to expire, then retry."
            )
        else:
            # Idempotent re-acquire: just renew
            existing["heartbeat"] = _now_iso()
            existing["phase"] = phase
            _atomic_write(sem_path, existing)
            return existing

    # Write new semaphore (also overwrites stale)
    now = _now_iso()
    data: dict = {  # type: ignore[type-arg]
        "owner": session_id,
        "phase": phase,
        "release": release,
        "write_set": write_set or [],
        "acquired_at": now,
        "ttl": ttl,
        "heartbeat": now,
    }
    _atomic_write(sem_path, data)
    return data


def renew_context_semaphore(
    workspace_root: Path,
    context: str,
    session_id: str,
) -> bool:
    """Renew the heartbeat timestamp of the semaphore owned by session_id.

    Returns True if renewed, False if the semaphore was not found or not owned
    by session_id.
    """
    sem_path = _semaphore_path(workspace_root, context)
    if not sem_path.exists():
        return False

    try:
        data = json.loads(sem_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    if data.get("owner") != session_id:
        return False

    data["heartbeat"] = _now_iso()
    _atomic_write(sem_path, data)
    return True


def release_context_semaphore(
    workspace_root: Path,
    context: str,
    session_id: str,
) -> bool:
    """Release the semaphore if owned by session_id.

    Returns True if released, False if not found or not owned by session_id.
    """
    sem_path = _semaphore_path(workspace_root, context)
    if not sem_path.exists():
        return False

    try:
        data = json.loads(sem_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Unreadable file: remove it (best-effort cleanup)
        sem_path.unlink(missing_ok=True)
        return True

    if data.get("owner") != session_id:
        return False

    sem_path.unlink(missing_ok=True)
    return True


def _atomic_write(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    """Write data to path atomically via a unique tmp file and os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.{uuid.uuid4().hex}.tmp"
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
