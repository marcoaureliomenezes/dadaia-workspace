"""Single-record cross-platform TTL-lease — DEMOTED to diagnostics-only (v0.1.76 FR2).

NO-LOCKS DOCTRINE (v0.1.76, SPEC ``specs/releases/v0.1.76/SPEC.md``): races between
sessions are ACCEPTED and SURFACED, never prevented. This module is **no longer the
concurrency kernel** — ``features/spec_context/presence.py`` is the ONLY concurrency-signal
surface the gate consults (``gate_policy.evaluate`` never imports this module; T-2).

T-3 DELETES the whole acquisition/blocking machinery: :func:`acquire` and its six-rung
decision tree, :class:`~dadaia_workspace.core.exceptions.LockHeldError`-raising, the
O_EXCL sentinel CAS helpers that existed *only* to serialize acquire/steal/adopt,
``adopt_if_own_lineage`` (the eager same-lineage rewrite ``dadaia context bind`` used to
call), ``steal`` and its CLI verb (``dadaia lock steal`` — gone), and the by-session
heartbeat index (``ctx_locks/by-session/<sid>.json`` — nothing writes it anymore, so a
read-only index is a permanently-empty structure; deleted rather than kept as a lie).

What legitimately survives here, and why — pure reads / dormant no-op writers over
whatever residual record a pre-doctrine install may still carry on disk:

* :func:`read_record` / :func:`is_held` / :func:`reclaim` / :func:`holder_in_lineage` —
  pure reads consumed by ``doctor``/``doctor_coherence``/``container.py`` diagnostics
  (staleness display, coherence backstop, preflight lease panel). Repointing these
  T-4-territory consumers to ``presence`` is out of T-3's declared write set
  (``spec_context/**``, ``chokepoints/**``, ``cli/**``, ``tests/**``).
* :func:`release` / :func:`renew_heartbeat` — kept as simple, holder-guarded no-ops (a
  single atomic read-verify-write, no CAS sentinel, no index) — harmless when no lease
  record exists (the common case going forward), and correct if a residual one does.
  ``cli/commands/context.py``'s ``context release``/``context heartbeat`` call these as a
  belt-and-suspenders alongside the real (``presence``) mechanism.

One liveness record per context, when one exists at all::

    .dadaia/states/ctx_locks/<ctx>.lock.json

Liveness is **TTL with a PID veto** (``core.lock_liveness.is_stale``; WS-R2 FR-R2-03),
consumed here only as a pure predicate for :func:`is_held`/:func:`reclaim` diagnostics —
never to gate a write.

Cross-harness honesty (v0.1.76): this module no longer gates any PreToolUse write on any
harness — ``presence.py`` is the sole cross-harness signal now. ``doctor`` GC over a
residual record remains meaningful only as diagnostic hygiene.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.exceptions import PlatformSecurityError
from dadaia_workspace.core.lock_liveness import is_stale
from dadaia_workspace.core.protocols.platform_services import FilePermissionSetter

#: Injected PID-liveness probe (WS-R2 FR-R2-03): ``(pid) -> alive?``. Threaded into
#: ``core.lock_liveness.is_stale`` so a TTL-expired-but-still-running foreign holder is
#: NOT taken over. ``None`` ⇒ TTL-only fallback. The concrete ``OsProcessProbe`` is
#: supplied by the hook layer via the container — this module never imports the adapter.
PidProbe = Callable[[int], bool]

__all__ = [
    "PidProbe",
    "holder_in_lineage",
    "is_held",
    "read_record",
    "reclaim",
    "release",
    "renew_heartbeat",
]

#: Heartbeat TTL in seconds lives in ``core.kernel_tunables.LEASE_TTL_SECONDS`` (the single
#: canonical home, DP-1 v0.1.14). Every liveness comparison references that constant; no
#: inline magic numbers are permitted anywhere in the liveness path. The lease-local
#: re-export was removed in v0.1.53 — import ``LEASE_TTL_SECONDS`` from ``core.kernel_tunables``.
_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")


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
    """Atomic write via unique tmp + ``os.replace``."""
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


def holder_in_lineage(
    record: dict[str, object] | None, ancestry_pids: frozenset[int] | None
) -> bool:
    """True iff the lease record's holder ``pid`` is in the CURRENT process lineage.

    Pure predicate — zero I/O. Kept for ``container.py``'s preflight diagnostics (T-4
    territory, out of T-3's write set): a residual record whose holder pid is our own
    process lineage is never reported as a "live foreign holder" in the preflight panel.
    """
    if record is None or not ancestry_pids:
        return False
    rec_pid = record.get("pid")
    return isinstance(rec_pid, int) and rec_pid in ancestry_pids


def renew_heartbeat(
    workspace: Path,
    ctx: str,
    session_id: str,
    *,
    clock: Callable[[], datetime] = _utcnow,
) -> bool:
    """Renew heartbeat iff a residual record is held by ``session_id``. No-op otherwise.

    Dormant simple read-verify-write (no CAS sentinel — nothing else writes this record
    anymore, so the historical concurrent-acquirer race this CAS guarded against cannot
    occur). A non-holder, or an absent record (the common case post-doctrine), is a
    guarded no-op returning ``False``.
    """
    rec = read_record(workspace, ctx)
    if rec is None or rec.get("session_id") != session_id:
        return False
    rec["heartbeat"] = clock().isoformat()
    _write_record(_record_path(workspace, ctx), rec)
    return True


def release(
    workspace: Path,
    ctx: str,
    session_id: str,
) -> bool:
    """Delete a residual record iff held by ``session_id``. No-op otherwise.

    Dormant simple guarded delete (no CAS sentinel, no by-session index — both deleted in
    T-3 along with ``acquire``/``steal``, their sole writers).
    """
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
    """True if a live (non-stale) residual record exists. Pure read.

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
    """Return ``True`` if a residual lease record is safe to reclaim (GC/delete).

    Reclaimability is the single liveness verdict (``core.lock_liveness.is_stale``) —
    unchanged predicate, kept so the workspace doctor's ``LOCK-GC`` sweep and diagnostics
    stay meaningful over a residual record from a pre-doctrine install, without any
    acquisition path consuming the verdict anymore.
    """
    return is_stale(record, clock=clock, pid_probe=pid_probe)
