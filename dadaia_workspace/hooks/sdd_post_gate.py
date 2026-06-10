"""PostToolUse session-heartbeat hook (the canonical, cross-platform gate surface).

Runs after every tool call. Its sole purpose: keep the active session alive by renewing
``last_seen_at`` in the session file and appending a HEARTBEAT event to
``.dadaia/logs/lock-events.jsonl``. It NEVER blocks a tool call; it always returns 0.

Parity invariants preserved verbatim from the rc-4 shell hook:

- Session identity comes from ``DADAIA_SESSION_ID``; absent → no-op (fail-open). The
  value is sanitized to ``[A-Za-z0-9_-]`` (CWE-22) before use as a filename component.
- Session-file renewal is ATOMIC via ``os.replace`` (atomic on POSIX *and* Windows).
- The HEARTBEAT append uses ``encoding='utf-8'``.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.hooks import _common


def _resolve_workspace() -> Path:
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def main() -> int:
    """Renew the session heartbeat. Returns 0 always (never blocks)."""
    sess_id = _common.sanitize_session_id(os.environ.get("DADAIA_SESSION_ID"))
    if not sess_id:
        return 0

    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open: never block a tool call
        return 0

    sess_file = workspace / ".dadaia" / "sessions" / f"{sess_id}.json"
    if not sess_file.is_file():
        return 0

    try:
        data = json.loads(sess_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(data, dict):
        return 0

    now = datetime.now(tz=UTC).isoformat()

    # Renew session file last_seen_at atomically (tmp -> os.replace).
    data["last_seen_at"] = now
    try:
        tmp = sess_file.with_suffix(f".{uuid.uuid4().hex}.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, sess_file)
    except OSError:
        return 0

    # Append HEARTBEAT event to lock-events.jsonl.
    record = {
        "ts": now,
        "event": "HEARTBEAT",
        "context": data.get("context", ""),
        "release": data.get("release", "") or "",
        "session_id": sess_id,
        "runtime": data.get("runtime", "unknown"),
        "pid": data.get("pid", 0),
    }
    audit_path = workspace / ".dadaia" / "logs" / "lock-events.jsonl"
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
