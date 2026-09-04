"""PostToolUse advisory presence, session heartbeat, and throttled-GC hook.

Runs after every tool call. It renews this session's advisory presence record(s),
best-effort refreshes ``last_seen_at`` in the CLI session record, and, on a throttle
cadence, runs the one GC reaper. It always returns zero and never blocks a tool call.

Session id resolution (unchanged, FR-R2-01): via :func:`_common.resolve_session_id` — the
harness-native id var (``CLAUDE_CODE_SESSION_ID`` / ``CODEX_SESSION_ID``) or the stdin
``session_id`` field. ``DADAIA_SESSION_ID`` is honored only as an *operator override* (it
sits first in ``resolve_session_id``'s order).

- Session ids are sanitized to ``[A-Za-z0-9_-]`` (CWE-22) before use as a filename
  component (``resolve_session_id`` sanitizes).
- Session-record renewal is ATOMIC via ``os.replace`` (atomic on POSIX *and* Windows).
- Fail-open: any exception ⇒ exit 0. The hook must never break the harness.

GC (release 0.5.1 K2): this hook no longer reaps anything itself. On its own throttle
cadence (never on every single tool call) it calls the ONE reaper, :func:`presence.gc`,
for presence records,
throttle/sentinel markers and now-empty presence context dirs. Session-record graveyard
GC stays exclusively owned by ``DoctorService.fix()`` — this hook used to duplicate it at
a different TTL multiplier via its own ``sid`` guard, which is exactly how it could reap
a session's own bind record (bug family ``doctor-ptr-gc-deletes-valid-lock-free-bind`` /
``context-release-leaves-lease-heartbeat-renewing`` /
``doctor-stale-lease-misdiagnosed-as-forgery``).
"""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import invocation, session_store
from dadaia_workspace.core.kernel_tunables import RECONCILER_THROTTLE_TTL_SECONDS
from dadaia_workspace.features.spec_context import presence
from dadaia_workspace.hooks import _common


def _refresh_session_record(workspace: Path, sess_id: str) -> dict[str, object] | None:
    """Best-effort refresh of the session record's ``last_seen_at``. Returns the record.

    Routed through ``session_store`` (NF-3 fix, WS-R3 FR-R3-01): the single owner of the
    ``sessions/<id>.json`` namespace constructs the path, reads the record, and writes it
    atomically. This hook no longer builds the session-record path itself, so it drops off
    the session-store ownership allowlist. Returns ``None`` (no-op) when the record is absent
    or unreadable because there is nothing to refresh otherwise.

    This ``last_seen_at`` refresh is the bind-record liveness renewal (T-011-04 / FR-W1-04,
    ADR-8 amended): the workspace doctor's graveyard GC measures TTL against ``last_seen_at``,
    so a still-active session — including a READ-mode bind — renews on
    every tool use and never silently decays.
    """
    now = datetime.now(tz=UTC).isoformat()
    return session_store.touch_last_seen_at(workspace, sess_id, now=now)


# ---------------------------------------------------------------------------------------
# Throttled GC cadence (FR-W1-03 throttle, release 0.5.1 K2 reaper) — NEVER blocks.
#
# Throttle marker: ``.dadaia/tmp/reconciler-last-<sid>``, via :func:`presence.throttled` /
# :func:`presence.stamp_throttle` — the ONE mtime-throttle-marker idiom. A second
# PostToolUse invocation inside the window does nothing; outside it, the hook calls the
# ONE reaper, :func:`presence.gc`. The git-status reconciler that used to share this
# cadence died with the log line that was its only output (FR11).
# ---------------------------------------------------------------------------------------


def _throttled_gc(workspace: Path, sess_id: str) -> None:
    """On the throttle cadence, run :func:`presence.gc`; inside the window, do nothing.

    The marker is stamped BEFORE the reaper runs so even a slow or erroring pass throttles
    the next invocation. Any exception is swallowed by the caller's ``main`` try/except
    (fail-open).
    """
    marker = f"reconciler-last-{sess_id}"
    if presence.throttled(
        workspace, marker, window_seconds=RECONCILER_THROTTLE_TTL_SECONDS, now=time.time()
    ):
        return
    presence.stamp_throttle(workspace, marker)
    presence.gc(workspace, now=datetime.now(tz=UTC), own_session_id=sess_id)


def main() -> int:
    """Renew this session's advisory presence record(s). Never blocks (exit 0)."""
    payload = _common.read_stdin_json()
    sess_id = _common.resolve_session_id(payload)
    if not sess_id:
        return 0

    try:
        workspace = invocation.resolve(env=os.environ, cwd=Path.cwd()).workspace_root
        if workspace is None:
            raise RuntimeError("workspace not resolved")
    except Exception:  # noqa: BLE001 — fail-open: never block a tool call
        return 0

    try:
        presence.renew(workspace, sess_id)
        _refresh_session_record(workspace, sess_id)
    except Exception:  # noqa: BLE001 — fail-open: any error ⇒ exit 0, never break harness
        return 0

    # Throttled GC cadence — isolated in its own try/except so a reaper bug can never
    # affect the heartbeat or the exit code.
    try:
        _throttled_gc(workspace, sess_id)
    except Exception:  # noqa: BLE001 — never blocks; any error ⇒ still exit 0.
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
