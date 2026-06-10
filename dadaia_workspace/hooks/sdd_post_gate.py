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
OpenCode) exports ``DADAIA_SESSION_ID`` to a hook subprocess (audit 2026-06-10 finding 2;
bug ``lease-stolen…`` D2/D3). A holder running a long (>120 s) Bash call therefore never
renewed, its lease went TTL-stale, and a concurrent session auto-TAKEOVER'd it — the
lease-theft incident. Three corrections (FR-R2-01):

1. **Session id is resolved from the stdin payload** via
   :func:`_common.resolve_session_id` — the harness-native id var
   (``CLAUDE_CODE_SESSION_ID`` / ``CODEX_SESSION_ID`` / ``OPENCODE_SESSION_ID``) or the
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

import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.hooks import _common


def _resolve_workspace() -> Path:
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def _iter_lease_contexts(workspace: Path) -> list[str]:
    """Context names with a present lock record, derived from the lock dir filenames.

    Returns ``[]`` (fail-soft) when the directory is absent or unreadable. Each entry is
    the ``<ctx>`` of a ``<ctx>.lock.json`` file; the suffix is stripped so the name is fed
    back through ``lease`` (which re-validates ``[A-Za-z0-9_-]``).
    """
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
    for ctx in _iter_lease_contexts(workspace):
        try:
            if lease.renew_heartbeat(workspace, ctx, sess_id):
                renewed += 1
        except (OSError, ValueError):
            # A malformed ctx name or a transient write error on one record must not
            # stop the others from renewing, and must never break the harness.
            continue
    return renewed


def _refresh_session_record(workspace: Path, sess_id: str) -> dict[str, object] | None:
    """Best-effort refresh of ``sessions/<id>.json`` ``last_seen_at``. Returns the record.

    Returns ``None`` (no-op) when the session file is absent or unreadable — unlike the
    lease renewal above, this *is* gated on the session file existing, because there is
    nothing to refresh otherwise. Renewal of the session record is atomic (tmp +
    ``os.replace``).
    """
    sess_file = workspace / ".dadaia" / "sessions" / f"{sess_id}.json"
    if not sess_file.is_file():
        return None
    try:
        data = json.loads(sess_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None

    data["last_seen_at"] = datetime.now(tz=UTC).isoformat()
    try:
        tmp = sess_file.with_suffix(f".{uuid.uuid4().hex}.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, sess_file)
    except OSError:
        return None
    return data


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


def main() -> int:
    """Renew this session's lease heartbeat(s). Returns 0 always (never blocks)."""
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
        # renews if the lock names it.
        leases_renewed = _renew_held_leases(workspace, sess_id)
        record = _refresh_session_record(workspace, sess_id)
        _append_heartbeat_event(workspace, sess_id, record, leases_renewed=leases_renewed)
    except Exception:  # noqa: BLE001 — fail-open: any error ⇒ exit 0, never break harness
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
