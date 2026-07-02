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

Cross-harness honesty: this record + ``doctor`` GC are the real enforcement
backstop across harnesses; Claude Code / Codex / Pi also get a real PreToolUse
block.
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

from dadaia_workspace.core import kernel_tunables
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
    "contexts_for_session",
    "is_held",
    "read_record",
    "reclaim",
    "release",
    "release_context_if_caller_owned",
    "release_for_session",
    "renew_heartbeat",
    "steal",
]

#: Heartbeat TTL in seconds — OQ-1 operator decision 2026-06-06 (short heartbeat).
#: Every liveness comparison must reference this constant; no inline magic numbers
#: are permitted anywhere in the liveness path. DP-1 (v0.1.14): the canonical home is now
#: ``core.kernel_tunables.LEASE_TTL_SECONDS``; this name is a re-export kept for one release
#: (deprecation note) so external importers (``from ...lease import LEASE_TTL_SECONDS``) and
#: tests keep working. New code should import from ``core.kernel_tunables``.
LEASE_TTL_SECONDS = kernel_tunables.LEASE_TTL_SECONDS

_MAX_RETRIES = kernel_tunables.CAS_MAX_RETRIES
_INITIAL_BACKOFF = kernel_tunables.CAS_INITIAL_BACKOFF_SECONDS
#: A sentinel older than this is an orphan (process SIGKILLed between CAS and unlink).
_SENTINEL_ORPHAN_AGE = kernel_tunables.SENTINEL_ORPHAN_AGE_SECONDS
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


# --- By-session heartbeat index (FR-W4-02) -------------------------------------
# ``ctx_locks/by-session/<sid>.json`` maps a session id to the set of contexts that
# session currently holds. PostToolUse renewal reads this index instead of scanning
# the whole lock dir, so a session holding nothing does no FS scan at all. The index
# entry is written/removed INSIDE the SAME O_EXCL sentinel CAS as the lock record in
# ``acquire``/``steal``/``release`` — record-write and index-write form one atomic
# unit; a lost index entry must be structurally impossible (a silent miss starves
# renewal and reopens the lease-theft class). ``_iter_lease_contexts`` falls back to a
# full lock-dir scan whenever the by-session DIR is absent (migration window).


def _by_session_dir(workspace: Path) -> Path:
    return workspace / ".dadaia" / "states" / "ctx_locks" / "by-session"


def _by_session_path(workspace: Path, session_id: str) -> Path:
    _validate(session_id, field="session_id")
    return _by_session_dir(workspace) / f"{session_id}.json"


def _read_by_session(workspace: Path, session_id: str) -> list[str]:
    """Read the contexts a session holds per its index entry (empty if absent/corrupt)."""
    path = _by_session_path(workspace, session_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        ctxs = data.get("contexts")
        if isinstance(ctxs, list):
            return [c for c in ctxs if isinstance(c, str)]
    return []


def _index_add(workspace: Path, ctx: str, session_id: str) -> None:
    """Add ``ctx`` to ``session_id``'s by-session index entry (inside the CAS)."""
    contexts = sorted({*_read_by_session(workspace, session_id), ctx})
    path = _by_session_path(workspace, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_record(path, {"session_id": session_id, "contexts": list(contexts)})


def _index_remove(workspace: Path, ctx: str, session_id: str) -> None:
    """Remove ``ctx`` from ``session_id``'s index entry; unlink the entry when empty."""
    remaining = [c for c in _read_by_session(workspace, session_id) if c != ctx]
    path = _by_session_path(workspace, session_id)
    if remaining:
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_record(path, {"session_id": session_id, "contexts": sorted(remaining)})
    else:
        path.unlink(missing_ok=True)


def release_for_session(workspace: Path, session_id: str) -> list[str]:
    """Eval-flow release (FR-W4-03 a): drop every lease the ``session_id`` holds.

    The env sid is the same key hooks renew on, so releasing every lock record naming
    it is exact — there is no foreign-holder ambiguity. Returns the contexts released.
    Falls back to a full lock-dir scan when the by-session index is absent (migration).
    """
    released: list[str] = []
    contexts = contexts_for_session(workspace, session_id)
    if not contexts:
        contexts = _scan_contexts_held_by(workspace, session_id)
    for ctx in contexts:
        try:
            if release(workspace, ctx, session_id):
                released.append(ctx)
        except (OSError, ValueError):
            continue
    return released


def _scan_contexts_held_by(workspace: Path, session_id: str) -> list[str]:
    """Migration fallback: scan lock records for those whose holder == ``session_id``."""
    lock_dir = _lock_dir(workspace)
    try:
        entries = list(lock_dir.iterdir())
    except OSError:
        return []
    suffix = ".lock.json"
    out: list[str] = []
    for p in entries:
        if not p.name.endswith(suffix):
            continue
        ctx = p.name[: -len(suffix)]
        rec = read_record(workspace, ctx)
        if rec is not None and rec.get("session_id") == session_id:
            out.append(ctx)
    return sorted(out)


def release_context_if_caller_owned(
    workspace: Path,
    ctx: str,
    *,
    caller_pid: int,
    pid_probe: PidProbe | None = None,
    ancestry: Callable[[int, int], bool] | None = None,
) -> str | None:
    """Default-flow release (FR-W4-03 b): drop ``ctx``'s lease only when caller-owned.

    The CLI-minted sid never matches the harness sid recorded in the lock, so we cannot
    release by sid. Instead, release the bound context's lease ONLY when its holder is:

    * **dead** — the holder ``pid`` is no longer alive (``pid_probe`` reports dead), OR
    * **the caller's own process** — the holder ``pid`` is an ancestor of ``caller_pid``
      (the ``ancestry(holder_pid, caller_pid)`` predicate), i.e. the bind belongs to the
      same harness tree issuing the release.

    A live foreign holder (alive pid, not in the caller's ancestry) is NEVER released by
    context name alone — that is exactly the cross-session theft the chokepoint forbids.
    Indeterminate ancestry is treated as NOT-owned (conservative: do not release).

    Returns the holder sid that was released, or ``None`` when nothing was released.
    """
    rec = read_record(workspace, ctx)
    if rec is None:
        return None
    holder_sid = str(rec.get("session_id", ""))
    holder_pid_raw = rec.get("pid")
    holder_pid = int(holder_pid_raw) if isinstance(holder_pid_raw, int) else None

    owned = False
    if holder_pid is None:
        # Legacy record without a pid — nothing to probe; treat as dead/releasable.
        owned = True
    else:
        alive = pid_probe(holder_pid) if pid_probe is not None else False
        if not alive:
            owned = True
        elif ancestry is not None and holder_pid != caller_pid:
            owned = ancestry(holder_pid, caller_pid)
        elif holder_pid == caller_pid:
            owned = True

    if not owned or not holder_sid:
        return None
    if release(workspace, ctx, holder_sid):
        return holder_sid
    return None


def contexts_for_session(workspace: Path, session_id: str) -> list[str]:
    """Public read of the by-session index: contexts ``session_id`` holds (FR-W4-02).

    Consumed by ``hooks/sdd_post_gate._iter_lease_contexts`` to drive renewal without a
    full lock-dir scan. Returns ``[]`` when the session holds nothing or its entry is
    absent/corrupt. An invalid session id returns ``[]`` rather than raising (the hook
    must never break the harness).
    """
    try:
        return sorted(_read_by_session(workspace, session_id))
    except ValueError:
        return []


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


#: Sentinel: "no explicit veto release supplied — use ``release``" (v0.1.50 FR1).
_UNSET_RELEASE: str = "\x00unset"


def _session_record_pid(workspace: Path, session_id: str) -> int | None:
    """Fail-soft pid of a CLI session record (self-recognition lineage evidence).

    Lazy import: ``session_identity`` owns the record path schema; ``lease`` only
    reads through the owner's helper (no cycle — session_identity does not import
    lease). Missing/corrupt record ⇒ ``None`` ⇒ no self-recognition (safe default).
    """
    from dadaia_workspace.features.spec_context.session_identity import (
        session_record_pid,
    )

    return session_record_pid(workspace, session_id)


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
    active_release: str | None = _UNSET_RELEASE,
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
                    _index_add(workspace, ctx, session_id)
                    _write_ptr(workspace, ctx, session_id)
                    return "RENEWED", rec
                else:
                    # No record (e.g. GC'd) → create fresh.
                    new = _new_record(
                        ctx, release, session_id, mode, clock=clock, ttl=ttl, pid=holder_pid
                    )
                    _write_record(record_path, new)
                    _index_add(workspace, ctx, session_id)
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
                _index_add(workspace, ctx, session_id)
                _write_ptr(workspace, ctx, session_id)
                return "RENEWED", rec

            # --- Foreign / absent: stale ⇒ takeover, live (TTL or pid-veto) ⇒ yield ---
            # ``active_release=release`` (T-43-10): the release this session is acquiring FOR is
            # the context's live ACTIVE release. A foreign lease pinned to a *different*
            # (closed/archived) release is reclaimable despite a live holder pid, so an archived
            # -release lease can no longer deadlock the next release. A foreign lease on the SAME
            # release keeps the pid-veto (a genuinely-active holder is never stolen).
            if rec is None or is_stale(
                rec,
                clock=clock,
                pid_probe=pid_probe,
                # v0.1.50 FR1 (audit F-3): the veto release is decoupled from the
                # RECORD release. Callers that could not READ ACTIVE.md pass
                # ``active_release=None`` (veto-preserving) while still writing a
                # "none" record release; the default keeps the legacy coupling.
                active_release=(release if active_release == _UNSET_RELEASE else active_release),
            ):
                # A takeover transfers holder identity: drop the stale holder's index
                # entry for this ctx, then claim it for the new session — same CAS.
                stale_holder = str(rec.get("session_id", "")) if rec else ""
                if stale_holder and stale_holder != session_id:
                    with contextlib.suppress(OSError, ValueError):
                        _index_remove(workspace, ctx, stale_holder)
                new = _new_record(
                    ctx, release, session_id, mode, clock=clock, ttl=ttl, pid=holder_pid
                )
                _write_record(record_path, new)
                _index_add(workspace, ctx, session_id)
                _write_ptr(workspace, ctx, session_id)
                _audit(workspace, "acquire", ctx, session_id, clock=clock)
                return "ACQUIRED", new

            # --- Self-recognition (v0.1.50 FR1, audit F-1): third identity rung ---
            # The live record's holder pid IS this very process (same harness pid,
            # rotated session id) AND the record's old sid demonstrably belonged to
            # this pid (its CLI session record — written by `dadaia context bind` —
            # carries the same pid: LINEAGE EVIDENCE). A process can never be foreign
            # to itself: RENEW under the current sid instead of self-blocking. Bare
            # pid equality is NOT enough — unit fixtures and eval flows legitimately
            # model foreign holders with the current process pid and no session
            # record, and those must keep blocking (yield-iff-live-foreign).
            rec_pid = rec.get("pid")
            old_sid = str(rec.get("session_id", ""))
            if (
                isinstance(rec_pid, int)
                and rec_pid == holder_pid
                and old_sid
                and old_sid != session_id
                and _session_record_pid(workspace, old_sid) == holder_pid
            ):
                with contextlib.suppress(OSError, ValueError):
                    _index_remove(workspace, ctx, old_sid)
                rec["session_id"] = session_id
                rec["pid"] = holder_pid
                rec["heartbeat"] = clock().isoformat()
                _write_record(record_path, rec)
                _index_add(workspace, ctx, session_id)
                _write_ptr(workspace, ctx, session_id)
                return "RENEWED", rec

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


def release(
    workspace: Path,
    ctx: str,
    session_id: str,
    *,
    permission_setter: FilePermissionSetter | None = None,
) -> bool:
    """Delete the record iff held by ``session_id``. No-op otherwise.

    Record-unlink and by-session-index removal happen inside the SAME O_EXCL sentinel
    CAS as ``acquire``/``steal`` (FR-W4-02): the two removals are one atomic unit, so a
    concurrent ``acquire`` can never interleave between them and observe a dangling index
    entry whose record is gone (or vice versa). A non-holder is a guarded no-op.
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
                return False  # contended release is a safe no-op.
            time.sleep(backoff)
            backoff *= 2
            continue
        try:
            rec = read_record(workspace, ctx)
            if rec is None or rec.get("session_id") != session_id:
                return False
            record_path.unlink(missing_ok=True)
            with contextlib.suppress(OSError, ValueError):
                _index_remove(workspace, ctx, session_id)
            _audit(workspace, "release", ctx, session_id, clock=_utcnow)
            return True
        finally:
            sentinel.unlink(missing_ok=True)
    return False


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


def reclaim(
    record: dict[str, object] | None,
    *,
    clock: Callable[[], datetime] = _utcnow,
    pid_probe: PidProbe | None = None,
) -> bool:
    """Return ``True`` if a lease record is safe to reclaim (GC/delete) — T-011-02.

    Reclaimability is the single liveness verdict (``core.lock_liveness.is_stale``):

    * TTL-expired **and** the holder pid is dead/absent (per ``pid_probe``) ⇒ reclaimable.
    * TTL-expired **but** the record carries **no** ``pid`` field (legacy/pre-pid record,
      observed in the ``doctor-stale-lease-misdiagnosed-as-forgery`` bug) ⇒ reclaimable —
      there is nothing to veto on, so it degrades to the TTL rule and is no longer
      permanently un-reclaimable.
    * TTL-expired **but** the holder pid is demonstrably **alive** (``pid_probe`` veto) ⇒
      **NOT** reclaimable, regardless of how far past TTL the heartbeat is. A
      genuinely-running session is never garbage-collected.
    * TTL-fresh ⇒ NOT reclaimable.
    * absent / corrupt record ⇒ reclaimable (fail-open: a corrupt lock never deadlocks).

    This is the GC counterpart to ``acquire``'s reclaim-iff-stale branch and exposes the
    same predicate to the workspace doctor's ``LOCK-GC`` sweep, so an idle workspace can
    garbage-collect a dead session's stale lease without a MUTATING-write acquisition.
    """
    return is_stale(record, clock=clock, pid_probe=pid_probe)


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
    active_release: str | None = None,
) -> tuple[bool, dict[str, object] | None]:
    """Reclaim a *stale* lease for ``session_id`` via the same O_EXCL CAS as acquire.

    Refuses (returns ``(False, record)``) if the lease is live — including a
    TTL-expired-but-pid-alive holder when ``pid_probe`` is wired (WS-R2 FR-R2-03: no
    stealing a genuinely-running session). Returns ``(True, new_record)`` on success.
    The CAS prevents a double-steal race.

    ``active_release`` (T-43-10): the context's live ACTIVE release. When provided, a lease
    pinned to a *different* (closed/archived) release is reclaimable despite a live holder pid
    — ``lock steal`` can break an archived-release deadlock. A lease on the live ACTIVE release
    keeps the pid-veto (no false steal of a genuinely-active session). ``None`` ⇒ legacy
    release-agnostic behavior.
    """
    _validate(ctx, field="context")
    _validate(session_id, field="session_id")
    holder_pid = os.getpid() if pid is None else pid
    rec = read_record(workspace, ctx)
    if rec is not None and not is_stale(
        rec, clock=clock, pid_probe=pid_probe, active_release=active_release
    ):
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
            if rec2 is not None and not is_stale(
                rec2, clock=clock, pid_probe=pid_probe, active_release=active_release
            ):
                return False, rec2  # became live during the race
            release_id = str(rec2.get("release", "")) if rec2 else ""
            mode = str(rec2.get("mode", "")) if rec2 else ""
            stale_holder = str(rec2.get("session_id", "")) if rec2 else ""
            if stale_holder and stale_holder != session_id:
                with contextlib.suppress(OSError, ValueError):
                    _index_remove(workspace, ctx, stale_holder)
            new = _new_record(
                ctx, release_id, session_id, mode, clock=clock, ttl=ttl, pid=holder_pid
            )
            _write_record(record_path, new)
            _index_add(workspace, ctx, session_id)
            _write_ptr(workspace, ctx, session_id)
            _audit(workspace, "steal", ctx, session_id, clock=clock)
            return True, new
        finally:
            sentinel.unlink(missing_ok=True)
    return False, read_record(workspace, ctx)


def _main_pid_probe() -> PidProbe | None:
    """Resolve the PID-liveness probe for the ``_main`` CLI side door (T-011-01).

    ``_main`` is the SDD gate's single acquisition point; its ``acquire``/``steal``
    paths must consult the SAME probe the MUTATING gate path uses, so a TTL-expired
    foreign holder whose pid is still alive is never taken over via this side door
    (residual R1; bug ``doctor-stale-lease-misdiagnosed-as-forgery``).

    The concrete probe is the container's ``OsProcessProbe``. ``features/`` must not
    import ``infrastructure/`` — not even transitively through the hook layer
    (import-linter law). The canonical builder lives in the hook layer
    (``hooks/sdd_gate._build_pid_probe``, which itself wires the adapter); we resolve it
    here through a **dynamic** ``importlib`` lookup at the composition boundary (this
    entrypoint is the lease's own composition root, analogous to the doctor's
    composition-root-wired probe seam — never a static feature→infrastructure import).
    The dynamic resolution keeps the static import graph clean: ``features/lease.py`` has
    zero static edge into ``infrastructure`` or ``hooks``. Any failure ⇒ ``None`` ⇒
    TTL-only fallback (Windows-safe, legacy-record-safe), exactly as the gate degrades.
    """
    try:
        import importlib

        sdd_gate = importlib.import_module("dadaia_workspace.hooks.sdd_gate")
        builder: Callable[[], PidProbe | None] = sdd_gate._build_pid_probe
        return builder()
    except Exception:  # noqa: BLE001 — probe wiring must never deadlock the gate side door.
        return None


def _main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: the SDD gate's SINGLE acquisition point.

    Usage::

        python -m dadaia_workspace.features.spec_context.lease acquire <ctx> <sid> <release> <mode>

    Prints ``ACQUIRED`` / ``RENEWED`` and exits 0 on success; prints the unblock
    message and exits 1 on a live conflict. Any unexpected failure exits 0
    (fail-open) so the gate never deadlocks on a lease-subsystem bug.

    Both the ``acquire`` and ``steal`` paths thread the pid-liveness probe
    (``_main_pid_probe``) so this side door honours the no-steal veto (T-011-01).
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

    # Single probe for every side-door path so the no-steal veto holds (T-011-01).
    pid_probe = _main_pid_probe()

    cmd = args[0]
    try:
        if cmd == "acquire":
            ctx, session_id, release_id, mode = args[1], args[2], args[3], args[4]
            try:
                status, _rec = acquire(
                    workspace, ctx, session_id, release_id, mode, pid_probe=pid_probe
                )
            except LockHeldError as exc:
                print(str(exc))
                return 1
            print(status)
            return 0
        if cmd == "steal":
            ctx, session_id = args[1], args[2]
            ok, _srec = steal(workspace, ctx, session_id, pid_probe=pid_probe)
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
