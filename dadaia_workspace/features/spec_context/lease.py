"""Single-record cross-platform TTL-lease (v0.1.6).

One liveness record per context governs release-mutation serialization::

    .dadaia/states/ctx_locks/<ctx>.lock.json

This module replaces the four desynchronized stores (workspace fcntl, per-context
fcntl, per-release implementation lock, per-context semaphore) that soft-deadlocked
the workspace and grew a 188-file session graveyard. fcntl Lock-1/Lock-2 in
``locking.py`` are retained — they serialize short same-process git ops.

Acquisition is an **O_EXCL compare-and-swap** via a sentinel file (``open(path, "x")``):
this closes the read→stale-check→write TOCTOU gap that caused the double-acquire
race. No read-then-write acquire path exists anywhere — this is a security red line.

Liveness is TTL-only (``core.lock_liveness.is_stale``): no PID, no ``os.kill``, no
``/proc`` — Windows-safe (OQ-1). A dead holder expires after TTL; an idle-but-alive
holder renews its heartbeat on every PreToolUse.

Cross-harness honesty: this record + ``doctor`` GC are the real enforcement on
opencode (which cannot block via JSON PreToolUse); Claude Code / Codex also get a
real PreToolUse block.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.exceptions import LockHeldError
from dadaia_workspace.core.lock_liveness import is_stale

__all__ = [
    "DEFAULT_TTL",
    "acquire",
    "is_held",
    "read_record",
    "release",
    "renew_heartbeat",
    "steal",
]

#: Heartbeat TTL in seconds (30 min) — OQ-1 binding decision. Renew-on-tool-use.
DEFAULT_TTL = 1800

_MAX_RETRIES = 3
_INITIAL_BACKOFF = 0.1
#: A sentinel older than this is an orphan (process SIGKILLed between CAS and unlink).
_SENTINEL_ORPHAN_AGE = 30.0
_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")

#: Test-only TOCTOU seam. ``acquire`` calls it after the sentinel CAS wins and
#: before the record is written, letting a test interleave a concurrent acquirer.
#: MUST be ``None`` in production; tests set it via ``monkeypatch`` (guaranteed
#: teardown even on failure).
_before_write: Callable[[], None] | None = None

# Import-time guard: in production _before_write is None. Tests under
# DADAIA_TESTING=1 may install it after import.
assert _before_write is None or os.environ.get("DADAIA_TESTING") == "1", (
    "lease._before_write must be None in production "
    "(set only by tests via monkeypatch under DADAIA_TESTING=1)"
)


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _validate(name: str, *, field: str) -> str:
    """Reject names outside the ``[A-Za-z0-9_-]`` allowlist (CWE-22/CWE-59)."""
    if not _NAME_RE.fullmatch(name):
        raise ValueError(f"invalid {field} {name!r}: must match [A-Za-z0-9_-]+ (CWE-22/CWE-59)")
    return name


def _lock_dir(workspace: Path) -> Path:
    d = workspace / ".dadaia" / "states" / "ctx_locks"
    d.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        d.chmod(0o700)
    return d


def _record_path(workspace: Path, ctx: str) -> Path:
    _validate(ctx, field="context")
    return _lock_dir(workspace) / f"{ctx}.lock.json"


def _sentinel_path(workspace: Path, ctx: str) -> Path:
    _validate(ctx, field="context")
    return _lock_dir(workspace) / f"{ctx}.lock.sentinel"


def read_record(workspace: Path, ctx: str) -> dict[str, object] | None:
    """Read the lease record. Returns ``None`` if absent or unparseable (pure read)."""
    path = _record_path(workspace, ctx)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _write_record(path: Path, data: dict[str, object]) -> None:
    """Atomic write via unique tmp + ``os.replace`` (inside the sentinel CAS)."""
    tmp = path.parent / f"{path.name}.{uuid.uuid4().hex}.tmp"
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _audit(
    workspace: Path,
    event: str,
    ctx: str,
    session_id: str,
    *,
    clock: Callable[[], datetime],
) -> None:
    """Append one JSON line to ``.dadaia/logs/lock-events.jsonl`` (POSIX O_APPEND)."""
    log_dir = workspace / ".dadaia" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "event": event,
        "context": ctx,
        "session_id": session_id,
        "at": clock().isoformat(),
        "runtime": os.environ.get("DADAIA_RUNTIME", "unknown"),
    }
    with open(log_dir / "lock-events.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _new_record(
    ctx: str,
    release: str,
    session_id: str,
    mode: str,
    *,
    clock: Callable[[], datetime],
    ttl: int,
) -> dict[str, object]:
    now = clock().isoformat()
    return {
        "context": ctx,
        "release": release,
        "session_id": session_id,
        "mode": mode,
        "acquired_at": now,
        "heartbeat": now,
        "ttl": ttl,
    }


def _gc_orphan_sentinel(sentinel: Path) -> None:
    """Unlink an orphan sentinel (mtime > 30 s) — prevents permanent deadlock after SIGKILL."""
    try:
        age = time.time() - sentinel.stat().st_mtime
    except OSError:
        return
    if age > _SENTINEL_ORPHAN_AGE:
        sentinel.unlink(missing_ok=True)


def _held_message(ctx: str, rec: dict[str, object]) -> str:
    """Exact unblock message (FR-P1-06) — always contains ``dadaia lock steal``."""
    return (
        f"[SDD LOCK] Release-mutation on '{ctx}' is held by session {rec.get('session_id', '?')}\n"
        f"           acquired_at={rec.get('acquired_at', '?')}, "
        f"last_heartbeat={rec.get('heartbeat', '?')}.\n"
        f"           One serialized release session at a time.\n"
        f"           To reclaim: dadaia lock steal {ctx}\n"
        f"           Backlog / audit / research writes are never blocked."
    )


def acquire(
    workspace: Path,
    ctx: str,
    session_id: str,
    release: str,
    mode: str,
    *,
    clock: Callable[[], datetime] = _utcnow,
    ttl: int = DEFAULT_TTL,
) -> tuple[str, dict[str, object]]:
    """Acquire (or renew) the lease via O_EXCL CAS.

    Returns ``("ACQUIRED", record)`` when the record was absent/stale and freshly
    written, or ``("RENEWED", record)`` when the caller already held it. Raises
    :class:`LockHeldError` on a live conflict (the *only* block) — its message
    carries the ``dadaia lock steal`` unblock path.
    """
    _validate(ctx, field="context")
    _validate(session_id, field="session_id")
    record_path = _record_path(workspace, ctx)
    sentinel = _sentinel_path(workspace, ctx)

    backoff = _INITIAL_BACKOFF
    for attempt in range(_MAX_RETRIES + 1):
        _gc_orphan_sentinel(sentinel)
        try:
            with open(sentinel, "x", encoding="utf-8"):  # O_CREAT|O_EXCL CAS
                pass
        except FileExistsError:
            if attempt >= _MAX_RETRIES:
                rec = read_record(workspace, ctx)
                holder = (rec or {}).get("session_id", "<acquiring>")
                raise LockHeldError(
                    f"context {ctx!r} lease is being acquired concurrently "
                    f"(holder={holder}); retry the operation."
                ) from None
            time.sleep(backoff)
            backoff *= 2
            continue
        try:
            if _before_write is not None:
                _before_write()
            rec = read_record(workspace, ctx)
            if rec is None or is_stale(rec, clock=clock):
                new = _new_record(ctx, release, session_id, mode, clock=clock, ttl=ttl)
                _write_record(record_path, new)
                _audit(workspace, "acquire", ctx, session_id, clock=clock)
                return "ACQUIRED", new
            if rec.get("session_id") == session_id:
                rec["heartbeat"] = clock().isoformat()
                _write_record(record_path, rec)
                return "RENEWED", rec
            raise LockHeldError(_held_message(ctx, rec))
        finally:
            sentinel.unlink(missing_ok=True)

    # Unreachable: the loop either returns, raises, or exhausts retries above.
    raise LockHeldError(f"context {ctx!r}: could not acquire lease sentinel")


def renew_heartbeat(
    workspace: Path,
    ctx: str,
    session_id: str,
    *,
    clock: Callable[[], datetime] = _utcnow,
) -> bool:
    """Renew heartbeat iff held by ``session_id`` and not stale. No-op otherwise."""
    rec = read_record(workspace, ctx)
    if rec is None or rec.get("session_id") != session_id:
        return False
    if is_stale(rec, clock=clock):
        return False
    rec["heartbeat"] = clock().isoformat()
    _write_record(_record_path(workspace, ctx), rec)
    return True


def release(workspace: Path, ctx: str, session_id: str) -> bool:
    """Delete the record iff held by ``session_id``. No-op otherwise."""
    rec = read_record(workspace, ctx)
    if rec is None or rec.get("session_id") != session_id:
        return False
    _record_path(workspace, ctx).unlink(missing_ok=True)
    _audit(workspace, "release", ctx, session_id, clock=_utcnow)
    return True


def is_held(workspace: Path, ctx: str, *, clock: Callable[[], datetime] = _utcnow) -> bool:
    """True if a live (non-stale) record exists. Pure read."""
    rec = read_record(workspace, ctx)
    return rec is not None and not is_stale(rec, clock=clock)


def steal(
    workspace: Path,
    ctx: str,
    session_id: str,
    *,
    clock: Callable[[], datetime] = _utcnow,
    ttl: int = DEFAULT_TTL,
) -> tuple[bool, dict[str, object] | None]:
    """Reclaim a *stale* lease for ``session_id`` via the same O_EXCL CAS as acquire.

    Refuses (returns ``(False, record)``) if the lease is live. Returns
    ``(True, new_record)`` on success. The CAS prevents a double-steal race.
    """
    _validate(ctx, field="context")
    _validate(session_id, field="session_id")
    rec = read_record(workspace, ctx)
    if rec is not None and not is_stale(rec, clock=clock):
        return False, rec

    sentinel = _sentinel_path(workspace, ctx)
    record_path = _record_path(workspace, ctx)
    backoff = _INITIAL_BACKOFF
    for attempt in range(_MAX_RETRIES + 1):
        _gc_orphan_sentinel(sentinel)
        try:
            with open(sentinel, "x", encoding="utf-8"):
                pass
        except FileExistsError:
            if attempt >= _MAX_RETRIES:
                return False, read_record(workspace, ctx)
            time.sleep(backoff)
            backoff *= 2
            continue
        try:
            rec2 = read_record(workspace, ctx)
            if rec2 is not None and not is_stale(rec2, clock=clock):
                return False, rec2  # became live during the race
            release_id = str(rec2.get("release", "")) if rec2 else ""
            mode = str(rec2.get("mode", "")) if rec2 else ""
            new = _new_record(ctx, release_id, session_id, mode, clock=clock, ttl=ttl)
            _write_record(record_path, new)
            _audit(workspace, "steal", ctx, session_id, clock=clock)
            return True, new
        finally:
            sentinel.unlink(missing_ok=True)
    return False, read_record(workspace, ctx)


def _main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: the SDD gate's SINGLE acquisition point.

    Usage::

        python -m dadaia_workspace.features.spec_context.lease acquire <ctx> <sid> <release> <mode>

    Prints ``ACQUIRED`` / ``RENEWED`` and exits 0 on success; prints the unblock
    message and exits 1 on a live conflict. Any unexpected failure exits 0
    (fail-open) so the gate never deadlocks on a lease-subsystem bug.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: lease <acquire|steal|release|status> <ctx> ...", file=sys.stderr)
        return 2

    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    # The gate passes WORKSPACE_ROOT so the lease acts on the same workspace it
    # classified (hermetic); fall back to CWD resolution for direct CLI use.
    ws_env = os.environ.get("WORKSPACE_ROOT")
    try:
        workspace = Path(ws_env) if ws_env else resolve_workspace_root()
    except Exception as exc:  # noqa: BLE001 — fail-open: gate must never deadlock
        print(f"WORKSPACE_UNRESOLVED: {exc}", file=sys.stderr)
        return 0

    cmd = args[0]
    try:
        if cmd == "acquire":
            ctx, session_id, release_id, mode = args[1], args[2], args[3], args[4]
            try:
                status, _rec = acquire(workspace, ctx, session_id, release_id, mode)
            except LockHeldError as exc:
                print(str(exc))
                return 1
            print(status)
            return 0
        if cmd == "steal":
            ctx, session_id = args[1], args[2]
            ok, _srec = steal(workspace, ctx, session_id)
            print("STOLEN" if ok else "LIVE")
            return 0 if ok else 1
        if cmd == "release":
            ctx, session_id = args[1], args[2]
            print("RELEASED" if release(workspace, ctx, session_id) else "NOOP")
            return 0
        if cmd == "status":
            ctx = args[1]
            print("HELD" if is_held(workspace, ctx) else "FREE")
            return 0
    except (IndexError, ValueError) as exc:
        # Bad args / invalid name → fail-open (allow); never deadlock the gate.
        print(f"LEASE_ARG_ERROR: {exc}", file=sys.stderr)
        return 0

    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
