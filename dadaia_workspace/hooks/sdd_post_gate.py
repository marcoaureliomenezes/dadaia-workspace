"""PostToolUse hook: refreshes the session record's ``last_seen_at`` (the liveness the
doctor's graveyard GC measures) and nothing else — the reaper runs at SessionStart and on
``doctor --fix``, never on a tool call. Fail-open: always exit 0, never blocks a tool call."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import invocation, session_store
from dadaia_workspace.hooks import _common


def main() -> int:
    _common.read_stdin_json()  # drain the harness payload; the session id is env-only
    sess_id = invocation.resolve_session_id(os.environ)
    if not sess_id:
        return 0
    try:
        workspace = invocation.resolve(env=os.environ, cwd=Path.cwd()).workspace_root
        if workspace is not None:
            session_store.touch_last_seen_at(
                workspace, sess_id, now=datetime.now(tz=UTC).isoformat()
            )
    except Exception:  # noqa: BLE001 — fail-open: never break the harness
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
