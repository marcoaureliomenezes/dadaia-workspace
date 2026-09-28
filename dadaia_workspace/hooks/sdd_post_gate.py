"""PostToolUse hook: refreshes the session record's ``last_seen_at`` (the liveness the
doctor's graveyard GC measures) and, on a throttle cadence, runs the one reaper
:func:`doctor.reap`. Fail-open: always exit 0, never blocks a tool call."""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import invocation, session_store
from dadaia_workspace.features.spec_context import markers
from dadaia_workspace.hooks import _common

#: A second PostToolUse inside this window runs no GC reaper and spawns no git child.
RECONCILER_THROTTLE_TTL_SECONDS = 30


def _throttled_gc(workspace: Path, sess_id: str) -> None:
    """Run :func:`doctor.reap` unless throttled; the marker is stamped first, so even an
    erroring pass throttles the next call."""
    marker = f"reconciler-last-{sess_id}"
    if markers.throttled(
        workspace, marker, window_seconds=RECONCILER_THROTTLE_TTL_SECONDS, now=time.time()
    ):
        return
    markers.stamp_throttle(workspace, marker)
    # imported here: the throttled-out path, the common one, pays no reaper import
    from dadaia_workspace.features.spec_context import doctor

    doctor.reap(workspace)


def main() -> int:
    payload = _common.read_stdin_json()
    sess_id = _common.resolve_session_id(payload)
    if not sess_id:
        return 0
    try:
        workspace = invocation.resolve(env=os.environ, cwd=Path.cwd()).workspace_root
        if workspace is not None:
            session_store.touch_last_seen_at(
                workspace, sess_id, now=datetime.now(tz=UTC).isoformat()
            )
            _throttled_gc(workspace, sess_id)
    except Exception:  # noqa: BLE001 — fail-open: never break the harness
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
