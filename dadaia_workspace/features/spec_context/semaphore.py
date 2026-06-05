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
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

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


def _is_stale(data: dict) -> bool:  # type: ignore[type-arg]
    """Return True if the semaphore's heartbeat has exceeded its TTL."""
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
    return not _is_stale(data)


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
    if existing is not None and not _is_stale(existing):
        holder = existing.get("owner", "unknown")
        if holder != session_id:
            raise SemaphoreAlreadyHeldError(
                f"Context '{context}' semaphore is already held by session '{holder}' "
                f"(phase={existing.get('phase', 'unknown')}, "
                f"release={existing.get('release', 'unknown')}, "
                f"acquired_at={existing.get('acquired_at', 'unknown')}). "
                "Wait for the holder to release or its TTL to expire, then retry."
            )
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
