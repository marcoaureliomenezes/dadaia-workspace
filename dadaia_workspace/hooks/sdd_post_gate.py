"""PostToolUse advisory presence, session heartbeat, and reconciler hook.

Runs after every tool call. It renews this session's advisory presence record(s),
best-effort refreshes ``last_seen_at`` in the CLI session record, and flags dirty
mutating paths. It always returns zero and never blocks a tool call.

Session id resolution (unchanged, FR-R2-01): via :func:`_common.resolve_session_id` — the
harness-native id var (``CLAUDE_CODE_SESSION_ID`` / ``CODEX_SESSION_ID``) or the stdin
``session_id`` field. ``DADAIA_SESSION_ID`` is honored only as an *operator override* (it
sits first in ``resolve_session_id``'s order).

- Session ids are sanitized to ``[A-Za-z0-9_-]`` (CWE-22) before use as a filename
  component (``resolve_session_id`` sanitizes).
- Session-record renewal is ATOMIC via ``os.replace`` (atomic on POSIX *and* Windows).
- Fail-open: any exception ⇒ exit 0. The hook must never break the harness.
"""

from __future__ import annotations

import json
import os
import subprocess  # noqa: S404 — see _reconcile_working_tree (documented FR-W1-03 exemption).
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.kernel_tunables import RECONCILER_THROTTLE_TTL_SECONDS
from dadaia_workspace.features.spec_context import gate_policy, presence, session_identity
from dadaia_workspace.features.spec_context.gate_policy import PathClass
from dadaia_workspace.hooks import _common


def _resolve_workspace() -> Path:
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def _refresh_session_record(workspace: Path, sess_id: str) -> dict[str, object] | None:
    """Best-effort refresh of the session record's ``last_seen_at``. Returns the record.

    Routed through ``session_identity`` (NF-3 fix, WS-R3 FR-R3-01): the single owner of the
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
    return session_identity.touch_last_seen_at(workspace, sess_id, now=now)


# ---------------------------------------------------------------------------------------
# Advisory working-tree reconciler (FR-W1-03, T-014-16) — NEVER blocks, always exit 0.
#
# Flags the case where the bound context's repo has dirty MUTATING paths while this session
# has dirty mutating paths (for example, a Bash write the file-tool gate cannot see). It
# only ever appends a
# ``RECONCILER_FLAG`` event to the reconciler log — it never changes session state, never raises,
# and never changes the hook's exit code.
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
        "note": "dirty MUTATING path(s); advisory only, no action taken",
    }
    audit_path = workspace / ".dadaia" / "logs" / "reconciler-events.jsonl"
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
    except OSError:
        return


def _reconcile_working_tree(workspace: Path, sess_id: str) -> None:
    """Advisory reconciler pass — flags dirty MUTATING paths in the bound repo. NEVER blocks.

    Order (throttle FIRST, before any git child):
      1. throttled within the window ⇒ return (no git spawned).
      2. no bound context ⇒ nothing to reconcile.
      3. ``git status --porcelain`` of the context repo fails ⇒ no event (fail-open).
      4. any dirty path classifies MUTATING ⇒ append RECONCILER_FLAG.

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
    """Renew this session's advisory presence record(s). Never blocks (exit 0)."""
    payload = _common.read_stdin_json()
    sess_id = _common.resolve_session_id(payload)
    if not sess_id:
        return 0

    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open: never block a tool call
        return 0

    try:
        presence.renew(workspace, sess_id)
        _refresh_session_record(workspace, sess_id)
    except Exception:  # noqa: BLE001 — fail-open: any error ⇒ exit 0, never break harness
        return 0

    # Advisory working-tree reconciler (FR-W1-03) — strictly advisory, isolated in its own
    # try/except so a reconciler bug can never affect the heartbeat or the exit code.
    try:
        _reconcile_working_tree(workspace, sess_id)
    except Exception:  # noqa: BLE001 — never blocks; any error ⇒ still exit 0.
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
