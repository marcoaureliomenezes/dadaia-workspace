"""PostToolUse session-heartbeat hook (the canonical, cross-platform gate surface).

Runs after every tool call. Its sole purpose: keep this session's lease(s) alive by
renewing their ``heartbeat`` in the lock record(s) this session holds, and (best-effort)
refreshing ``last_seen_at`` in the session record. It NEVER blocks a tool call; it always
returns 0.

R2a (release v0.1.10, FR-R2-01/02 / AC-R2-01) — what changed vs the rc-4 parity hook
------------------------------------------------------------------------------------
The previous implementation gated the *entire* hook on ``DADAIA_SESSION_ID`` being set in
the process environment::

    sess_id = sanitize_session_id(os.environ.get("DADAIA_SESSION_ID"))
    if not sess_id:
        return 0

That guard made the heartbeat a **permanent no-op**: no real harness (Claude Code, Codex,
Codex) exports ``DADAIA_SESSION_ID`` to a hook subprocess (audit 2026-06-10 finding 2;
bug ``lease-stolen…`` D2/D3). A holder running a long (>120 s) Bash call therefore never
renewed, its lease went TTL-stale, and a concurrent session auto-TAKEOVER'd it — the
lease-theft incident. Three corrections (FR-R2-01):

1. **Session id is resolved from the stdin payload** via
   :func:`_common.resolve_session_id` — the harness-native id var
   (``CLAUDE_CODE_SESSION_ID`` / ``CODEX_SESSION_ID``) or the
   stdin ``session_id`` field. ``DADAIA_SESSION_ID`` is honored only as an *operator
   override* (it sits first in ``resolve_session_id``'s order). The old no-op guard is
   gone.
2. **The renewal context is the lease(s) this session actually holds.** We scan the lock
   directory and renew every record whose ``session_id`` equals this sid (via
   :func:`lease.renew_heartbeat`, which is itself holder-guarded and no-ops for a foreign
   or stale record). We deliberately do **not** resolve the context via
   ``DADAIA_CONTEXT`` → first-ALIVE: that path renews *whatever* context happens to be
   first-ALIVE, which is exactly the cross-context lease-contamination bug. (first-ALIVE is
   not used here at all; if a future need arises it must be a documented last resort, never
   the default.)
3. **Lease renewal runs OUTSIDE any session-file-existence guard.** A holder whose session
   record was GC'd or never written still renews its lease as long as the lock record names
   it. The optional session-record ``last_seen_at`` refresh is the only thing still gated on
   the session file existing.

Parity invariants preserved verbatim from the rc-4 shell hook:

- Session ids are sanitized to ``[A-Za-z0-9_-]`` (CWE-22) before use as a filename
  component (``resolve_session_id`` sanitizes).
- Session-record renewal is ATOMIC via ``os.replace`` (atomic on POSIX *and* Windows).
- The HEARTBEAT append uses ``encoding='utf-8'``.
- Fail-open: any exception ⇒ exit 0. The hook must never break the harness.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess  # noqa: S404 — see _reconcile_working_tree (documented FR-W1-03 exemption).
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.kernel_tunables import RECONCILER_THROTTLE_TTL_SECONDS
from dadaia_workspace.features.spec_context import gate_policy, lease, presence, session_identity
from dadaia_workspace.features.spec_context.gate_policy import PathClass
from dadaia_workspace.hooks import _common


def _resolve_workspace() -> Path:
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def _iter_lease_contexts(workspace: Path, sess_id: str) -> list[str]:
    """Contexts this session holds — index-driven (FR-W4-02), no full lock-dir scan.

    Resolution order:

    1. **By-session index present** (``ctx_locks/by-session/`` dir exists): read this
       session's entry (``by-session/<sid>.json``) and return only the contexts it names.
       A session holding nothing has no entry → ``[]`` and the lock dir is never scanned.
       This is the FS-op-counting acceptance: PostToolUse does not iterate the lock dir
       when the session holds nothing.
    2. **By-session DIR absent** (migration window — a workspace whose leases predate the
       index): fall back to the legacy full lock-dir scan so a pre-index holder still
       renews. ``lease.renew_heartbeat`` is holder-guarded, so scanning every record is a
       safe (if less efficient) superset.

    Returns ``[]`` (fail-soft) on any read error. Each name is fed back through ``lease``
    (which re-validates ``[A-Za-z0-9_-]``).
    """
    by_session_dir = workspace / ".dadaia" / "states" / "ctx_locks" / "by-session"
    if by_session_dir.is_dir():
        return sorted(lease.contexts_for_session(workspace, sess_id))

    # Migration fallback: no by-session index yet → full lock-dir scan.
    lock_dir = workspace / ".dadaia" / "states" / "ctx_locks"
    try:
        entries = list(lock_dir.iterdir())
    except OSError:
        return []
    suffix = ".lock.json"
    return sorted(p.name[: -len(suffix)] for p in entries if p.name.endswith(suffix))


def _renew_held_leases(workspace: Path, sess_id: str) -> int:
    """Renew the heartbeat of every lease this session holds. Returns the count renewed.

    The renewal target is resolved from the lock records this ``sess_id`` actually holds —
    NOT from ``DADAIA_CONTEXT`` → first-ALIVE (which would re-import the cross-context
    contamination bug). ``lease.renew_heartbeat`` is holder-guarded and stale-guarded, so a
    foreign or expired record is a safe no-op. Each renewal is isolated: one bad record
    never aborts the others (fail-open per FR-R2-01).
    """
    renewed = 0
    for ctx in _iter_lease_contexts(workspace, sess_id):
        try:
            if lease.renew_heartbeat(workspace, ctx, sess_id):
                renewed += 1
        except (OSError, ValueError):
            # A malformed ctx name or a transient write error on one record must not
            # stop the others from renewing, and must never break the harness.
            continue
    return renewed


def _refresh_session_record(workspace: Path, sess_id: str) -> dict[str, object] | None:
    """Best-effort refresh of the session record's ``last_seen_at``. Returns the record.

    Routed through ``session_identity`` (NF-3 fix, WS-R3 FR-R3-01): the single owner of the
    ``sessions/<id>.json`` namespace constructs the path, reads the record, and writes it
    atomically. This hook no longer builds the session-record path itself, so it drops off
    the session-store ownership allowlist. Returns ``None`` (no-op) when the record is absent
    or unreadable — unlike the lease renewal above, this is gated on the record existing,
    because there is nothing to refresh otherwise.

    This ``last_seen_at`` refresh is the bind-record liveness renewal (T-011-04 / FR-W1-04,
    ADR-8 amended): the workspace doctor's graveyard GC measures TTL against ``last_seen_at``,
    so a still-active session — including a READ-mode bind that takes no lease — renews on
    every tool use and never silently decays.
    """
    now = datetime.now(tz=UTC).isoformat()
    return session_identity.touch_last_seen_at(workspace, sess_id, now=now)


def _append_heartbeat_event(
    workspace: Path,
    sess_id: str,
    record: dict[str, object] | None,
    *,
    leases_renewed: int,
) -> None:
    """Append a HEARTBEAT event to ``.dadaia/logs/lock-events.jsonl`` (best-effort)."""
    now = datetime.now(tz=UTC).isoformat()
    rec = record or {}
    event = {
        "ts": now,
        "event": "HEARTBEAT",
        "context": rec.get("context", ""),
        "release": rec.get("release", "") or "",
        "session_id": sess_id,
        "runtime": rec.get("runtime", "unknown"),
        "pid": rec.get("pid", 0),
        "leases_renewed": leases_renewed,
    }
    audit_path = workspace / ".dadaia" / "logs" / "lock-events.jsonl"
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
    except OSError:
        return


# ---------------------------------------------------------------------------------------
# Advisory working-tree reconciler (FR-W1-03, T-014-16) — NEVER blocks, always exit 0.
#
# Flags the case where the bound context's repo has dirty MUTATING paths while this session
# holds NO lease for that context: an out-of-lease production edit landed (e.g. a Bash-tool
# write the deterministic gate cannot see, Decision D-2). It only ever appends a
# ``RECONCILER_FLAG`` event to the lock-events log — it never mutates a lease, never raises,
# and never changes the hook's exit code. The four never-blocks acceptance criteria are:
# (1) always exit-allow, (2) advisory output only, (3) fail-open on error, (4) no lease
# mutation.
# ---------------------------------------------------------------------------------------
def _throttle_marker(workspace: Path, sess_id: str) -> Path:
    """Per-session throttle marker path (``.dadaia/tmp/reconciler-last-<sid>``)."""
    return workspace / ".dadaia" / "tmp" / f"reconciler-last-{sess_id}"


def _throttled(workspace: Path, sess_id: str, *, now: float) -> bool:
    """True iff a reconciler run for ``sess_id`` happened within the throttle window.

    Checked BEFORE any git child is spawned (acceptance: a throttled invocation spawns no
    git process). A missing/unreadable marker means "not throttled" (fail-open → run).
    """
    marker = _throttle_marker(workspace, sess_id)
    try:
        last = marker.stat().st_mtime
    except OSError:
        return False
    return (now - last) < RECONCILER_THROTTLE_TTL_SECONDS


def _stamp_throttle(workspace: Path, sess_id: str) -> None:
    """Record that the reconciler ran now (best-effort; failure must never break the hook)."""
    marker = _throttle_marker(workspace, sess_id)
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(datetime.now(tz=UTC).isoformat(), encoding="utf-8")
    except OSError:
        return


def _bound_context(workspace: Path, sess_id: str) -> str | None:
    """The context this session is bound to (from its session record), or ``None``."""
    record = session_identity.read_session(workspace, sess_id)
    if not isinstance(record, dict):
        return None
    ctx = record.get("context")
    return ctx if isinstance(ctx, str) and ctx else None


def _porcelain_paths(repo_root: Path) -> list[str] | None:
    """Return ``git status --porcelain`` path entries for ``repo_root``, or ``None`` on error.

    DOCUMENTED EXEMPTION (FR-W1-03): the advisory reconciler is a hook (not a ``features``
    module), and reads the working-tree status via a direct, read-only
    ``git status --porcelain`` with a hard timeout. Any failure (no git, not a repo, timeout)
    returns ``None`` → the caller emits nothing and exits 0 (fail-open).
    """
    try:
        proc = subprocess.run(  # noqa: S603 — fixed read-only argv, no shell, hard timeout.
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        # Porcelain v1: 2 status chars + space + path (rename uses "orig -> new").
        entry = line[3:].strip()
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        if entry:
            paths.append(entry)
    return paths


def _has_dirty_mutating_path(ctx: str, paths: list[str]) -> bool:
    """True iff any dirty path classifies MUTATING under ``ctx`` (context-relative)."""
    for p in paths:
        rel = f"repos/{ctx}/{p}"
        if gate_policy.classify_path(rel) is PathClass.MUTATING:
            return True
    return False


def _append_reconciler_flag(workspace: Path, sess_id: str, ctx: str, count: int) -> None:
    """Append a ``RECONCILER_FLAG`` advisory event (best-effort)."""
    event = {
        "ts": datetime.now(tz=UTC).isoformat(),
        "event": "RECONCILER_FLAG",
        "context": ctx,
        "session_id": sess_id,
        "dirty_mutating_paths": count,
        "note": "out-of-lease dirty MUTATING path(s); advisory only, no action taken",
    }
    audit_path = workspace / ".dadaia" / "logs" / "lock-events.jsonl"
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
    except OSError:
        return


def _reconcile_working_tree(workspace: Path, sess_id: str) -> None:
    """Advisory reconciler pass — flags out-of-lease dirty MUTATING paths. NEVER blocks.

    Order (throttle FIRST, before any git child):
      1. throttled within the window ⇒ return (no git spawned).
      2. session holds a lease for its bound context ⇒ no event (its dirt is in-lease).
      3. no bound context ⇒ nothing to reconcile.
      4. ``git status --porcelain`` of the context repo fails ⇒ no event (fail-open).
      5. any dirty path classifies MUTATING ⇒ append RECONCILER_FLAG.

    Every branch stamps the throttle marker on exit so the next call inside the window is a
    no-op. Any exception is swallowed by the caller's ``main`` try/except (fail-open).
    """
    if _throttled(workspace, sess_id, now=time.time()):
        return
    # Stamp immediately so even a slow/erroring pass throttles the next invocation.
    _stamp_throttle(workspace, sess_id)

    ctx = _bound_context(workspace, sess_id)
    if ctx is None:
        return

    # A session that holds the lease for its bound context is acting in-lease — never flag it.
    if ctx in lease.contexts_for_session(workspace, sess_id):
        return

    repo_root = workspace / "repos" / ctx
    if not repo_root.is_dir():
        return

    paths = _porcelain_paths(repo_root)
    if not paths:
        return
    if not _has_dirty_mutating_path(ctx, paths):
        return

    count = sum(
        1 for p in paths if gate_policy.classify_path(f"repos/{ctx}/{p}") is PathClass.MUTATING
    )
    _append_reconciler_flag(workspace, sess_id, ctx, count)


def main() -> int:
    """Renew this session's lease heartbeat(s) + advisory presence. Never blocks (exit 0)."""
    payload = _common.read_stdin_json()
    sess_id = _common.resolve_session_id(payload)
    if not sess_id:
        return 0

    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open: never block a tool call
        return 0

    try:
        # Lease renewal is the primary, correctness-critical job and runs OUTSIDE any
        # session-file guard (FR-R2-01): a holder whose session record is missing still
        # renews if the lock names it. Kept as-is for v0.1.76 T-2 (T-3 removes the lease
        # machinery entirely); presence renewal is additive, not a replacement here.
        leases_renewed = _renew_held_leases(workspace, sess_id)
        record = _refresh_session_record(workspace, sess_id)
        _append_heartbeat_event(workspace, sess_id, record, leases_renewed=leases_renewed)
    except Exception:  # noqa: BLE001 — fail-open: any error ⇒ exit 0, never break harness
        return 0

    # v0.1.76 FR2: refresh every advisory presence record this session owns. Isolated
    # from the heartbeat exit code (presence must never affect it) and
    # ``presence.renew`` itself never raises — belt-and-suspenders here.
    with contextlib.suppress(Exception):
        presence.renew(workspace, sess_id)

    # Advisory working-tree reconciler (FR-W1-03) — strictly advisory, isolated in its own
    # try/except so a reconciler bug can never affect the heartbeat or the exit code.
    try:
        _reconcile_working_tree(workspace, sess_id)
    except Exception:  # noqa: BLE001 — never blocks; any error ⇒ still exit 0.
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
