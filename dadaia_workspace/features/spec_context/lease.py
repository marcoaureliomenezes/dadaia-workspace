"""Single-record cross-platform TTL-lease (v0.1.6 + D1 soul-fold).

One liveness record per context governs release-mutation serialization::

    .dadaia/states/ctx_locks/<ctx>.lock.json

This module replaces the four desynchronized stores (workspace fcntl, per-context
fcntl, per-release implementation lock, per-context semaphore) that soft-deadlocked
the workspace and grew a 188-file session graveyard. fcntl Lock-1/Lock-2 in
``locking.py`` are retained — they serialize short same-process git ops.

Acquisition is an **O_EXCL compare-and-swap** via a sentinel file (``open(path, "x")``):
this closes the read→stale-check→write TOCTOU gap that caused the double-acquire
race. No read-then-write acquire path exists anywhere — this is a security red line.

Liveness is **TTL with a PID veto** (``core.lock_liveness.is_stale``; WS-R2 FR-R2-03).
The record carries the holder's ``pid``. A holder whose heartbeat has aged past
``LEASE_TTL_SECONDS`` is reclaimable **unless** an injected ``pid_probe`` reports that
pid is still alive — in which case ``acquire`` BLOCKs rather than taking over a
genuinely-running foreign session (the no-steal half that killed live-session lease
theft). The probe is **injected** from the hook layer (``hooks/sdd_gate.py`` sources the
container's ``OsProcessProbe``); this feature module never imports
``infrastructure/process_probe_adapter`` — no new import-linter ignore. When no probe is
wired (platforms without ``PLATFORM.has_os_kill_liveness``, or legacy records lacking a
``pid``), liveness degrades cleanly to TTL-only and remains Windows-safe. An idle-but-alive
holder still renews its heartbeat on every PreToolUse / PostToolUse, and a **confirmed
holder renews even past TTL** (same session_id or ``.ptr`` match ⇒ no self-loss).

**Stable session identity (D1 soul-fold):**  On first acquire for a (context,
session_id) pair, a pointer file is written::

    .dadaia/sessions/runtime/<ctx>.ptr

On every subsequent acquire, if the ``.ptr`` file exists and its content matches
``session_id``, the caller is treated as the incumbent → RENEW (no conflict, no
freeze). This eliminates false-conflict from session-id instability across relaunches.

**Yield-iff-live-foreign (FR-P1-15):** If the ``.ptr`` does not match and the
existing lease holder is genuinely live (heartbeat < ``LEASE_TTL_SECONDS`` ago),
``acquire`` raises :class:`~dadaia_workspace.core.exceptions.LockHeldError` with an
informative yield message. The message never instructs the operator to rebind, relaunch,
or steal — there is no manual unblock ceremony. A finished or dead holder is freed
automatically by reclaim-iff-stale after ``LEASE_TTL_SECONDS`` without a heartbeat.

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

from dadaia_workspace.core.exceptions import LockHeldError, PlatformSecurityError
from dadaia_workspace.core.lock_liveness import is_stale
from dadaia_workspace.core.protocols.platform_services import FilePermissionSetter
from dadaia_workspace.features.spec_context import session_identity

#: Injected PID-liveness probe (WS-R2 FR-R2-03): ``(pid) -> alive?``. Threaded into
#: ``core.lock_liveness.is_stale`` so a TTL-expired-but-still-running foreign holder is
#: NOT taken over. ``None`` ⇒ TTL-only fallback. The concrete ``OsProcessProbe`` is
#: supplied by the hook layer via the container — this module never imports the adapter.
PidProbe = Callable[[int], bool]

__all__ = [
    "LEASE_TTL_SECONDS",
    "PidProbe",
    "acquire",
    "is_held",
    "read_record",
    "release",
    "renew_heartbeat",
    "steal",
]

#: Heartbeat TTL in seconds — OQ-1 operator decision 2026-06-06 (short heartbeat).
#: Every liveness comparison must reference this constant; no inline magic numbers
#: are permitted anywhere in the liveness path.
LEASE_TTL_SECONDS = 120

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


def _lock_dir(
    workspace: Path,
    permission_setter: FilePermissionSetter | None = None,
) -> Path:
    d = workspace / ".dadaia" / "states" / "ctx_locks"
    d.mkdir(parents=True, exist_ok=True)
    # Tier-2: try to restrict the lock dir; if it fails (e.g. Windows icacls error)
    # log INFO and continue — the lock itself still functions, just without ACL restriction.
    if permission_setter is not None:
        try:
            permission_setter.restrict_dir_to_owner(d)
        except PlatformSecurityError as exc:
            import logging as _logging

            _logging.getLogger(__name__).info(
                "lease: cannot restrict ctx_locks dir permissions (%s) — continuing.",
                exc,
            )
    else:
        with contextlib.suppress(OSError):
            d.chmod(0o700)
    return d


def _record_path(
    workspace: Path,
    ctx: str,
    permission_setter: FilePermissionSetter | None = None,
) -> Path:
    _validate(ctx, field="context")
    return _lock_dir(workspace, permission_setter) / f"{ctx}.lock.json"


def _sentinel_path(
    workspace: Path,
    ctx: str,
    permission_setter: FilePermissionSetter | None = None,
) -> Path:
    _validate(ctx, field="context")
    return _lock_dir(workspace, permission_setter) / f"{ctx}.lock.sentinel"


# Stable-identity pointer reads/writes are owned by ``session_identity`` (WS-R3,
# FR-R3-01). ``lease.py`` keeps these thin wrappers so its acquire/CAS logic and the
# existing test seams read naturally, but it no longer constructs the
# ``sessions/runtime/*.ptr`` path itself — the single owner does.


def _ptr_path(workspace: Path, ctx: str) -> Path:
    """Path for the stable-identity pointer file (delegated to ``session_identity``)."""
    _validate(ctx, field="context")
    return session_identity.ptr_path(workspace, ctx, create=True)


def _read_ptr(workspace: Path, ctx: str) -> str | None:
    """Read the stable-identity pointer; returns session_id string or None."""
    _validate(ctx, field="context")
    return session_identity.read_incumbent_ptr(workspace, ctx)


def _write_ptr(workspace: Path, ctx: str, session_id: str) -> None:
    """Write session_id to the incumbent pointer atomically (via ``session_identity``)."""
    _validate(ctx, field="context")
    session_identity.write_incumbent_ptr(workspace, ctx, session_id)


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
    pid: int,
) -> dict[str, object]:
    now = clock().isoformat()
    return {
        "context": ctx,
        "release": release,
        "session_id": session_id,
        "mode": mode,
        "pid": pid,
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


def _yield_message(ctx: str, holder_id: str, heartbeat: str) -> str:
    """Build the informative yield-iff-live-foreign message (FR-P1-15).

    HARD CONSTRAINT (operator forbidden-law): this message MUST NOT instruct the
    operator to ``bind --mode write``, ``relaunch``, or ``lock steal`` — not even
    as a conditional/emergency step. There is no manual unblock ceremony: the lease
    auto-reclaims after ``LEASE_TTL_SECONDS`` without a heartbeat, so a finished or
    dead holder frees it automatically and this session acquires on its next write.
    """
    return (
        f"[SDD LOCK] Session {holder_id!r} is actively mutating context {ctx!r} "
        f"(last heartbeat: {heartbeat}). "
        "This session will not mutate to avoid a race. "
        "Additive writes (backlog/audit/reports/handoff) are still allowed. "
        f"The lease auto-reclaims after ~{LEASE_TTL_SECONDS}s without a heartbeat, "
        "so a finished or dead session frees it automatically and this session "
        "then acquires on its next write. No manual action is needed."
    )


def acquire(
    workspace: Path,
    ctx: str,
    session_id: str,
    release: str,
    mode: str,
    *,
    clock: Callable[[], datetime] = _utcnow,
    ttl: int = LEASE_TTL_SECONDS,
    permission_setter: FilePermissionSetter | None = None,
    pid_probe: PidProbe | None = None,
    pid: int | None = None,
) -> tuple[str, dict[str, object]]:
    """Acquire (or renew) the lease via O_EXCL CAS.

    Decision tree (FR-P1-15 + WS-R2 FR-R2-03/04):

    1. ``.ptr`` file matches ``session_id`` → **RENEW** unconditionally (stable identity:
       this is the incumbent session, even if the lock record shows a different session_id
       due to a relaunch). Updates the lock record to ``session_id`` (holder-safe past TTL).
    2. Record present and ``session_id`` matches → **RENEWED**, *even past TTL* — a
       confirmed holder never loses its own lease to its own staleness (FR-R2-04).
    3. Record absent, or TTL-stale **and** the holder pid is dead/absent (per the injected
       ``pid_probe``) → **ACQUIRED** / **TAKEOVER** (fresh write).
    4. Record TTL-stale **but** the holder pid is still alive (``pid_probe`` veto), or
       record TTL-fresh, with a foreign ``session_id`` and no ``.ptr`` match → raises
       :class:`~dadaia_workspace.core.exceptions.LockHeldError` with the informative
       yield-iff-live-foreign message (FR-P1-15/FR-R2-03). The caller must not proceed.

    ``pid_probe`` (``(pid) -> alive?``) is injected from the hook layer (container's
    ``OsProcessProbe``); ``None`` ⇒ TTL-only fallback (Windows-safe, legacy-record-safe).
    ``pid`` defaults to this process's pid and is written into the record at acquire/takeover.

    The only other :class:`LockHeldError` raised is transient sentinel-contention
    (a genuinely simultaneous CAS that loses all retries); the SDD gate treats that
    as fail-open (ALLOW), so it never freezes the flow either.

    On every successful acquire/renew, the ``.ptr`` file is written or refreshed.
    """
    _validate(ctx, field="context")
    _validate(session_id, field="session_id")
    record_path = _record_path(workspace, ctx, permission_setter)
    sentinel = _sentinel_path(workspace, ctx, permission_setter)
    holder_pid = os.getpid() if pid is None else pid

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

            # --- Stable session identity (D1): check .ptr first ---
            ptr_id = _read_ptr(workspace, ctx)
            if ptr_id is not None and ptr_id == session_id:
                # Incumbent session recognised via .ptr — RENEW unconditionally.
                # Update the lock record to the current session_id (it may have
                # drifted to a foreign id due to a relaunch without .ptr cleanup).
                rec = read_record(workspace, ctx)
                if rec is not None:
                    rec["session_id"] = session_id
                    rec["pid"] = holder_pid
                    rec["heartbeat"] = clock().isoformat()
                    _write_record(record_path, rec)
                    _write_ptr(workspace, ctx, session_id)
                    return "RENEWED", rec
                else:
                    # No record (e.g. GC'd) → create fresh.
                    new = _new_record(
                        ctx, release, session_id, mode, clock=clock, ttl=ttl, pid=holder_pid
                    )
                    _write_record(record_path, new)
                    _write_ptr(workspace, ctx, session_id)
                    _audit(workspace, "acquire", ctx, session_id, clock=clock)
                    return "ACQUIRED", new

            rec = read_record(workspace, ctx)

            # --- Holder-safe renew (FR-R2-04): a confirmed holder renews even past TTL.
            # Checked BEFORE the staleness branch so a holder never loses its own lease
            # to its own heartbeat ageing.
            if rec is not None and rec.get("session_id") == session_id:
                rec["pid"] = holder_pid
                rec["heartbeat"] = clock().isoformat()
                _write_record(record_path, rec)
                _write_ptr(workspace, ctx, session_id)
                return "RENEWED", rec

            # --- Foreign / absent: stale ⇒ takeover, live (TTL or pid-veto) ⇒ yield ---
            if rec is None or is_stale(rec, clock=clock, pid_probe=pid_probe):
                new = _new_record(
                    ctx, release, session_id, mode, clock=clock, ttl=ttl, pid=holder_pid
                )
                _write_record(record_path, new)
                _write_ptr(workspace, ctx, session_id)
                _audit(workspace, "acquire", ctx, session_id, clock=clock)
                return "ACQUIRED", new

            # Foreign lease that is still live — either TTL-fresh, or TTL-stale but the
            # holder pid is demonstrably alive (WS-R2 FR-R2-03 no-steal veto).
            # NEVER take over a live foreign lease: that violates exactly-one-mutating.
            holder_id = str(rec.get("session_id", "<unknown>"))
            heartbeat = str(rec.get("heartbeat", "unknown"))
            raise LockHeldError(_yield_message(ctx, holder_id, heartbeat))

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
    permission_setter: FilePermissionSetter | None = None,
) -> bool:
    """Renew heartbeat iff held by ``session_id``. No-op otherwise.

    Atomic w.r.t. a foreign ``acquire`` (FR-R2-04): the read→verify→write runs **inside
    the same O_EXCL sentinel CAS** that ``acquire``/``steal`` use, so a concurrent
    takeover can never interleave between this renewal's read and write. Without the CAS
    (the historical race at this site), a foreign acquirer could take over a stale record
    *after* this read but *before* this write, and the write would then stamp the foreign
    record back to ``session_id`` — producing a lock-file history in which two different
    holders each believe they hold the lease. The CAS serializes them: whoever wins the
    sentinel runs to completion; the loser observes the committed record.

    Holder-safe past TTL: a confirmed holder renews even if its own heartbeat aged out —
    it never loses its own lease to its own staleness (mirrors ``acquire``'s holder branch).
    A non-holder is a guarded no-op (returns ``False``); it never overwrites a foreign
    record.
    """
    sentinel = _sentinel_path(workspace, ctx, permission_setter)
    record_path = _record_path(workspace, ctx, permission_setter)
    backoff = _INITIAL_BACKOFF
    for attempt in range(_MAX_RETRIES + 1):
        _gc_orphan_sentinel(sentinel)
        try:
            with open(sentinel, "x", encoding="utf-8"):  # O_CREAT|O_EXCL CAS
                pass
        except FileExistsError:
            if attempt >= _MAX_RETRIES:
                return False  # contended renewal is a safe no-op (gate fail-open).
            time.sleep(backoff)
            backoff *= 2
            continue
        try:
            rec = read_record(workspace, ctx)
            if rec is None or rec.get("session_id") != session_id:
                return False
            rec["heartbeat"] = clock().isoformat()
            _write_record(record_path, rec)
            return True
        finally:
            sentinel.unlink(missing_ok=True)
    return False


def release(workspace: Path, ctx: str, session_id: str) -> bool:
    """Delete the record iff held by ``session_id``. No-op otherwise."""
    rec = read_record(workspace, ctx)
    if rec is None or rec.get("session_id") != session_id:
        return False
    _record_path(workspace, ctx).unlink(missing_ok=True)
    _audit(workspace, "release", ctx, session_id, clock=_utcnow)
    return True


def is_held(
    workspace: Path,
    ctx: str,
    *,
    clock: Callable[[], datetime] = _utcnow,
    pid_probe: PidProbe | None = None,
) -> bool:
    """True if a live (non-stale) record exists. Pure read.

    ``pid_probe`` (when wired) keeps a TTL-expired-but-still-running holder reported
    as held (WS-R2 FR-R2-03); ``None`` ⇒ TTL-only.
    """
    rec = read_record(workspace, ctx)
    return rec is not None and not is_stale(rec, clock=clock, pid_probe=pid_probe)


def steal(
    workspace: Path,
    ctx: str,
    session_id: str,
    *,
    clock: Callable[[], datetime] = _utcnow,
    ttl: int = LEASE_TTL_SECONDS,
    permission_setter: FilePermissionSetter | None = None,
    pid_probe: PidProbe | None = None,
    pid: int | None = None,
) -> tuple[bool, dict[str, object] | None]:
    """Reclaim a *stale* lease for ``session_id`` via the same O_EXCL CAS as acquire.

    Refuses (returns ``(False, record)``) if the lease is live — including a
    TTL-expired-but-pid-alive holder when ``pid_probe`` is wired (WS-R2 FR-R2-03: no
    stealing a genuinely-running session). Returns ``(True, new_record)`` on success.
    The CAS prevents a double-steal race.
    """
    _validate(ctx, field="context")
    _validate(session_id, field="session_id")
    holder_pid = os.getpid() if pid is None else pid
    rec = read_record(workspace, ctx)
    if rec is not None and not is_stale(rec, clock=clock, pid_probe=pid_probe):
        return False, rec

    sentinel = _sentinel_path(workspace, ctx, permission_setter)
    record_path = _record_path(workspace, ctx, permission_setter)
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
            if rec2 is not None and not is_stale(rec2, clock=clock, pid_probe=pid_probe):
                return False, rec2  # became live during the race
            release_id = str(rec2.get("release", "")) if rec2 else ""
            mode = str(rec2.get("mode", "")) if rec2 else ""
            new = _new_record(
                ctx, release_id, session_id, mode, clock=clock, ttl=ttl, pid=holder_pid
            )
            _write_record(record_path, new)
            _write_ptr(workspace, ctx, session_id)
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
