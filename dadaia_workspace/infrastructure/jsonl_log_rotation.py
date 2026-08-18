"""Shared JSONL log-rotation helper (FR27, T-043-42).

Every ``.dadaia/logs/*.jsonl`` writer (``hooks/pre_gate.py``'s ``hook-latency.jsonl``,
``hooks/sdd_post_gate.py``'s ``reconciler-events.jsonl``,
``features/chokepoints/service.py``'s ``push-verdict-gc-ledger.jsonl`` — the SAME
directory family per that module's own FR24 comment, so this release covers it too with
no separate carve-out) funnels its append through :func:`append_rotating_jsonl` so the
~1 MB cap + current+1 retention rule (A27.1) exists exactly once, never copy-pasted per
writer.

Rotation happens AT WRITE TIME, by the writer itself — never an external cron or
reconciler sweep, matching FR27's letter.

Fail-open (A27.2): every failure mode here — an unwritable parent dir, the target path
already a directory, a lock-acquisition timeout, any other ``OSError`` — is swallowed
and the function returns ``False`` without raising. A rotation failure (or the rotation
mechanism itself) must NEVER change the verdict of the hook/gate/tool the caller serves;
worst case, one telemetry/ledger line is silently dropped.

Concurrency (A27.3): only a caller that observes the file AT OR OVER the cap takes a
lock — the overwhelming majority of calls (comfortably under the cap) stay completely
lock-free, a single ``stat`` + append, identical cost to what every writer already did
before FR27. The lock is a directory-mkdir mutex (``<path>.rotlock/``): ``os.mkdir`` is
atomic on POSIX and Windows alike, so no ``fcntl``/platform split is needed for
something this small (unlike ``infrastructure/telemetry_lock_posix.py``'s
``fcntl.flock``, which needs one because it protects a much longer-held critical
section). Inside the lock, the size is RE-CHECKED before rotating (double-checked
locking) — this is what prevents two near-simultaneous crossers from both calling
``os.replace`` and destroying each other's rotated generation; a writer that observed
"under cap" never rotates at all, so it can never cause that race regardless of when its
append physically lands (``O_APPEND`` guarantees its bytes land intact in whichever
generation its file descriptor targets — see the two long-form notes below for why this
holds under every interleaving, not just the common one).

Two subtleties worth writing down because they are easy to get backwards:

1. **Why unlocked appends near the boundary are still safe.** Every append is a single
   buffered ``write()`` that resolves to ONE OS ``write(2)`` syscall on ``close()``
   (JSONL lines are far smaller than the default buffer). ``O_APPEND`` makes each such
   syscall atomic and always targets the current end-of-file — this is the textbook safe
   pattern for multiple processes appending to one shared log file without any lock.
   Nothing here can interleave/corrupt bytes WITHIN or ACROSS lines; the lock exists
   solely to serialize the (much rarer) directory-entry rename, not the appends.
2. **Why a lock-free writer's line is never truly lost, only possibly relocated.** If an
   unlocked writer's file descriptor was opened before a concurrent rotation's
   ``os.replace`` runs, its bytes land in the file NOW REACHABLE via the ``.1`` path
   (the rename does not affect an already-open descriptor's target inode) instead of
   ``current`` — present, not corrupted, just in the other surviving generation.

A stale lock directory (a crashed holder that never released it — vanishingly rare given
how short the critical section is) self-heals: any acquirer that finds the lock dir
older than :data:`_STALE_LOCK_SECONDS` reclaims it instead of waiting forever, so a dead
process can never permanently stall rotation for everyone else.
"""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path

from dadaia_workspace.core.kernel_tunables import LOG_ROTATION_MAX_BYTES

__all__ = ["LOG_ROTATION_MAX_BYTES", "append_rotating_jsonl"]

#: Bound on lock-acquisition attempts before giving up — fail-open: the append is
#: dropped, never blocks the caller indefinitely (A27.2). Worst-case wait is
#: ``_LOCK_MAX_ATTEMPTS * _LOCK_RETRY_SECONDS`` (~100 ms at the defaults below).
_LOCK_MAX_ATTEMPTS: int = 50
_LOCK_RETRY_SECONDS: float = 0.002

#: A lock dir older than this is presumed abandoned by a crashed holder — reclaimed
#: instead of waited on. Generous relative to the critical section's real duration
#: (a handful of syscalls, sub-millisecond) so a live holder is never preempted.
_STALE_LOCK_SECONDS: float = 5.0


def _lock_dir_for(path: Path) -> Path:
    return path.with_name(path.name + ".rotlock")


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _acquire(lock_dir: Path) -> bool:
    for _ in range(_LOCK_MAX_ATTEMPTS):
        try:
            lock_dir.mkdir()
            return True
        except FileExistsError:
            try:
                age = time.time() - lock_dir.stat().st_mtime
            except OSError:
                age = 0.0
            if age > _STALE_LOCK_SECONDS:
                with contextlib.suppress(OSError):
                    lock_dir.rmdir()
                continue
            time.sleep(_LOCK_RETRY_SECONDS)
        except OSError:
            return False
    return False


def _release(lock_dir: Path) -> None:
    with contextlib.suppress(OSError):
        lock_dir.rmdir()


def _write_line(path: Path, line: str) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _rotate_if_still_over_cap(path: Path, max_bytes: int) -> None:
    """Re-checked (double-checked locking) under the caller's held lock."""
    if _safe_size(path) < max_bytes:
        return
    rotated = path.with_name(path.name + ".1")
    # another holder already rotated it between our two stat calls, if raised.
    with contextlib.suppress(FileNotFoundError):
        os.replace(path, rotated)


def _rotate_and_append(path: Path, line: str, max_bytes: int) -> bool:
    lock_dir = _lock_dir_for(path)
    if not _acquire(lock_dir):
        # Contention timeout (A27.2 fail-open): append without the safety re-check
        # rather than drop the line outright. This branch never calls os.replace, so
        # it can never cause the double-rotation race the lock exists to prevent.
        try:
            _write_line(path, line)
            return True
        except OSError:
            return False
    try:
        _rotate_if_still_over_cap(path, max_bytes)
        _write_line(path, line)
        return True
    except OSError:
        return False
    finally:
        _release(lock_dir)


def append_rotating_jsonl(path: Path, line: str, *, max_bytes: int | None = None) -> bool:
    """Append *line* (no trailing newline) to *path*, rotating first if needed.

    A27.1: once *path*'s current size is ``>= max_bytes``, the current file is renamed
    to ``<name>.1`` (an existing ``.1`` is atomically discarded/replaced — current+1
    retention, never more) before *line* lands in a fresh *path*.

    *max_bytes* defaults to :data:`LOG_ROTATION_MAX_BYTES` **read at call time** (never
    baked into a bound default) so a caller — or a test — that reassigns the module
    attribute observes the new cap on the very next call.

    A27.2/fail-open: every failure path returns ``False`` without raising — never crash
    the hook/gate/tool this appender serves.

    A27.3: see the module docstring for the full concurrency argument.
    """
    effective_cap = LOG_ROTATION_MAX_BYTES if max_bytes is None else max_bytes
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    if _safe_size(path) < effective_cap:
        try:
            _write_line(path, line)
            return True
        except OSError:
            return False
    return _rotate_and_append(path, line, effective_cap)
