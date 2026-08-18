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

import contextlib
import json
import os
import re
import subprocess  # noqa: S404 — see _reconcile_working_tree (documented FR-W1-03 exemption).
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.kernel_tunables import (
    PRESENCE_TTL_SECONDS,
    RECONCILER_REAP_TTL_MULTIPLIER,
    RECONCILER_THROTTLE_TTL_SECONDS,
    SESSION_GC_TTL_SECONDS,
)
from dadaia_workspace.core.record_liveness import is_stale
from dadaia_workspace.features.spec_context import gate_policy, presence, session_identity
from dadaia_workspace.features.spec_context.gate_policy import PathClass
from dadaia_workspace.hooks import _common
from dadaia_workspace.infrastructure.jsonl_log_rotation import append_rotating_jsonl


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
    """The context this session resolves to, for the advisory reconciler's own read side.

    ``DADAIA.md`` §3 law order (F-03, v0.5.0 review): rung 1 ``DADAIA_CONTEXT`` first —
    presence attribution always agrees with the gate and ctx_inject on the same prompt,
    and the env rung is also kimi-code's bridge (launched with ``DADAIA_CONTEXT``
    exported, the SPEC coupling-2 disposition, since T-50-04 deleted the
    marker-attributed self-adoption that used to key a kimi session's record). Rung 2 is
    the session binding: this session's OWN record (``session_identity.read_session``
    keyed by ``sess_id``), then the authority
    (:func:`dadaia_workspace.core.specs_resolver.resolve_context` — hooks are sanctioned
    DIRECT importers per the seam contract; the container never loads on a hook path,
    F-01), which adds rung 3, the repo containing the current working directory.
    """
    # Law order (F-03, v0.5.0 code review): rung 1 `DADAIA_CONTEXT` first, so presence
    # attribution always agrees with the gate and ctx_inject on the same prompt.
    env_context = os.environ.get("DADAIA_CONTEXT")
    if env_context:
        return env_context

    record = session_identity.read_session(workspace, sess_id)
    if isinstance(record, dict):
        ctx = record.get("context")
        if isinstance(ctx, str) and ctx:
            return ctx

    # Direct core import (F-01): never pay the container's import graph in a hook.
    from dadaia_workspace.core.specs_resolver import resolve_context

    return resolve_context()


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


def _append_reconciler_event(workspace: Path, event: dict[str, object]) -> None:
    """Append one JSON *event* to the shared ``.dadaia/logs/reconciler-events.jsonl``.

    FR27 (T-043-42): funneled through the single shared rotation helper
    (``infrastructure/jsonl_log_rotation.append_rotating_jsonl``) so this file caps at
    ~1 MB and keeps current+1 like every other ``.dadaia/logs/*.jsonl`` writer. Both
    reconciler-events writers (``_append_reconciler_flag``, ``_append_reap_event``)
    share this ONE call site instead of each duplicating the write.
    """
    audit_path = workspace / ".dadaia" / "logs" / "reconciler-events.jsonl"
    append_rotating_jsonl(audit_path, json.dumps(event))


def _append_reconciler_flag(workspace: Path, sess_id: str, ctx: str, count: int) -> None:
    """Append a ``RECONCILER_FLAG`` advisory event (best-effort)."""
    _append_reconciler_event(
        workspace,
        {
            "ts": datetime.now(tz=UTC).isoformat(),
            "event": "RECONCILER_FLAG",
            "context": ctx,
            "session_id": sess_id,
            "dirty_mutating_paths": count,
            "note": "dirty MUTATING path(s); advisory only, no action taken",
        },
    )


# ---------------------------------------------------------------------------------------
# Stale-record reaper (FR26, T-043-41) — NEVER blocks, always best-effort/fail-open.
#
# Extends the reconciler's own domain (the session/presence state it already touches via
# ``presence.renew``/``_refresh_session_record`` earlier in ``main()``) to also DELETE what
# has gone stale well beyond any legitimate live session's heartbeat window: session and
# presence records stale beyond N×TTL (``RECONCILER_REAP_TTL_MULTIPLIER`` — deliberately
# more conservative than ``dadaia doctor --fix``'s manually-invoked 1×TTL graveyard GC,
# since this reaper fires automatically), their tmp markers (``reconciler-last-*``,
# ``ctx-inject-fired-*``), now-empty presence context dirs, and zombie
# ``.dadaia/states/lifecycle/*.json`` run records left by the retired workflow engine
# (status "running"/"completed" — a "blocked" run is a paused, still-relevant operator
# decision, never a zombie).
#
# AG.1 lane guard, uniformly across every target: resolved before deletion, refused if the
# resolved path falls outside ``.dadaia/``, and a symlinked directory is never followed
# (mirrors ``features.chokepoints.service``'s FR24 lane guard — the T-043-39 precedent).
# ---------------------------------------------------------------------------------------

#: Marker filename prefixes this reaper owns, matching exactly what the reconciler
#: (``_stamp_throttle``) and ``ctx_inject`` write under ``.dadaia/tmp/``.
_TMP_MARKER_PREFIXES: tuple[str, ...] = ("reconciler-last-", "ctx-inject-fired-")

#: A lifecycle/state run record is a zombie iff its status is one of these — "blocked" is
#: excluded on purpose (a paused run still awaiting an operator decision, never a zombie).
_ZOMBIE_LIFECYCLE_STATUSES: frozenset[str] = frozenset({"running", "completed"})

#: Path-traversal allowlist (CWE-22/CWE-59), matching ``session_identity``/``presence``'s
#: own ``_NAME_RE`` — a marker's extracted session id must look like a real id before it is
#: ever used to probe ``.dadaia/sessions/``.
_MARKER_ID_RE = re.compile(r"[A-Za-z0-9_-]+")


@dataclass(frozen=True)
class ReapOutcome:
    """Result of one FR26 stale-record reap pass.

    Every field is a tuple of identifiers (never full paths, sorted by discovery order —
    mirrors ``features.chokepoints.service.GcOutcome``'s convention): reaped session ids,
    ``<ctx>/<session_id>.json`` presence keys, reaped tmp marker filenames, removed
    (now-)empty presence context-dir names, and reaped lifecycle run-record filenames.
    """

    sessions: tuple[str, ...] = ()
    presence: tuple[str, ...] = ()
    markers: tuple[str, ...] = ()
    empty_context_dirs: tuple[str, ...] = ()
    lifecycle_runs: tuple[str, ...] = ()


def _resolved_within(path: Path, boundary: Path) -> bool:
    """AG.1: True iff *path*, fully resolved (symlinks included), falls under *boundary*
    (already resolved). Mirrors ``features.chokepoints.service._resolved_within`` — the
    established deletion-lane-guard idiom in this codebase: resolve, then ``relative_to``
    inside ``try/except``, never a string-prefix check (CWE-22 class: a sibling directory
    whose name string-prefixes the boundary)."""
    try:
        path.resolve().relative_to(boundary)
    except (ValueError, OSError):
        return False
    return True


def _iter_files(root: Path) -> Iterator[Path]:
    """Yield every file under *root*, sorted, never following a symlinked directory.

    AG.1: mirrors ``features.chokepoints.service._iter_handoff_paths`` — an EXPLICIT
    ``os.walk(..., followlinks=False)``, not an incidental ``Path.rglob`` default.
    """
    if not root.is_dir():
        return
    found: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        for filename in filenames:
            found.append(Path(dirpath) / filename)
    yield from sorted(found)


def _read_json_dict(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _reap_ttl(record: dict[str, object]) -> int:
    """This session record's own TTL (seconds) — the workspace default otherwise —
    multiplied by the reconciler's own N× reap multiplier (FR26: "stale beyond N×TTL")."""
    raw = record.get(session_identity.SESSION_GC_TTL_FIELD, SESSION_GC_TTL_SECONDS)
    base: int = SESSION_GC_TTL_SECONDS
    with contextlib.suppress(TypeError, ValueError):
        base = int(raw)  # type: ignore[call-overload]
    return base * RECONCILER_REAP_TTL_MULTIPLIER


def _reap_sessions(workspace: Path, dadaia_root: Path, sess_id: str) -> list[str]:
    """A26.1 — session records stale beyond N×TTL. The CALLING session's own record is
    NEVER a candidate (identity check, independent of whatever TTL math would say)."""
    reaped: list[str] = []
    sessions_dir = session_identity.sessions_dir(workspace)
    for path in _iter_files(sessions_dir):
        if path.suffix != ".json":
            continue
        sid = path.stem
        if sid == sess_id:
            continue
        if not _resolved_within(path, dadaia_root):
            continue
        data = session_identity.read_session(workspace, sid)
        if data is None:
            continue
        gc_check: dict[str, object] = {
            "heartbeat": session_identity.liveness_timestamp(data),
            "ttl": _reap_ttl(data),
        }
        if not is_stale(gc_check):
            continue
        try:
            path.unlink()
        except OSError:
            continue
        reaped.append(sid)
    return reaped


def _reap_markers(
    workspace: Path,
    dadaia_root: Path,
    reaped_session_ids: set[str],
    *,
    now: float,
) -> list[str]:
    """A26.1 — tmp markers paired with a session reaped THIS pass are deleted
    unconditionally; a marker with NO owning session record at all (orphaned by a prior
    GC pass, or a pseudo-session like ``doctor``) falls back to its own mtime staleness.
    A marker whose session record still exists (still live, or simply not yet judged
    stale) is never touched."""
    reaped: list[str] = []
    tmp_dir = workspace / ".dadaia" / "tmp"
    sessions_dir = session_identity.sessions_dir(workspace)
    ttl = SESSION_GC_TTL_SECONDS * RECONCILER_REAP_TTL_MULTIPLIER
    for path in _iter_files(tmp_dir):
        name = path.name
        sid: str | None = None
        for prefix in _TMP_MARKER_PREFIXES:
            if name.startswith(prefix):
                sid = name[len(prefix) :]
                break
        if not sid or not _MARKER_ID_RE.fullmatch(sid):
            continue

        if sid in reaped_session_ids:
            stale = True
        elif (sessions_dir / f"{sid}.json").exists():
            continue  # still-present session record — never touch its marker here.
        else:
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            stale = (now - mtime) >= ttl

        if not stale:
            continue
        if not _resolved_within(path, dadaia_root):
            continue
        try:
            path.unlink()
        except OSError:
            continue
        reaped.append(name)
    return reaped


def _reap_presence(
    workspace: Path,
    dadaia_root: Path,
    sess_id: str,
) -> tuple[list[str], list[str]]:
    """A26.1 — presence records stale beyond N×TTL, and any context dir left (or already)
    empty. The calling session's OWN presence records (any context) are never touched.

    AG.1: walked with ``os.walk(..., followlinks=False)`` — a symlinked context dir is
    never descended into, so nothing inside it is ever discovered, reaped, or removed.
    """
    reaped: list[str] = []
    empty_dirs: list[str] = []
    presence_root = workspace / ".dadaia" / "states" / "presence"
    if not presence_root.is_dir():
        return reaped, empty_dirs

    ttl = PRESENCE_TTL_SECONDS * RECONCILER_REAP_TTL_MULTIPLIER
    for dirpath, dirnames, filenames in os.walk(presence_root, followlinks=False):
        dirnames.sort()
        current = Path(dirpath)
        if current == presence_root:
            continue  # only per-context subdirectories are reap/removal targets.

        remaining = 0
        for filename in sorted(f for f in filenames if f.endswith(".json")):
            path = current / filename
            data = _read_json_dict(path)
            owner = data.get("session_id") if isinstance(data, dict) else None
            if owner == sess_id:
                remaining += 1
                continue
            gc_check: dict[str, object] = {
                "heartbeat": data.get("last_seen_at") if isinstance(data, dict) else None,
                "ttl": ttl,
            }
            if not is_stale(gc_check):
                remaining += 1
                continue
            if not _resolved_within(path, dadaia_root):
                remaining += 1
                continue
            try:
                path.unlink()
            except OSError:
                remaining += 1
                continue
            reaped.append(f"{current.name}/{filename}")

        if remaining == 0:
            try:
                current.rmdir()
            except OSError:
                continue
            empty_dirs.append(current.name)

    return reaped, empty_dirs


def _reap_zombie_lifecycle_runs(workspace: Path, dadaia_root: Path) -> list[str]:
    """A26.2 — zombie ``.dadaia/states/lifecycle/*.json`` run records left by the retired
    workflow engine (no code in this tree reads or writes this directory any more): status
    "running" or "completed" is a zombie; "blocked" is a paused, still-relevant operator
    decision and is never touched."""
    reaped: list[str] = []
    lifecycle_dir = workspace / ".dadaia" / "states" / "lifecycle"
    for path in _iter_files(lifecycle_dir):
        if path.suffix != ".json":
            continue
        if not _resolved_within(path, dadaia_root):
            continue
        data = _read_json_dict(path)
        if data is None:
            continue
        run = data.get("run")
        status = run.get("status") if isinstance(run, dict) else None
        if status not in _ZOMBIE_LIFECYCLE_STATUSES:
            continue
        try:
            path.unlink()
        except OSError:
            continue
        reaped.append(path.name)
    return reaped


def _reap_stale_records(
    workspace: Path,
    sess_id: str,
    *,
    now: float | None = None,
) -> ReapOutcome:
    """FR26/AG.1 — best-effort GC of stale session/presence records, their tmp markers,
    now-empty presence context dirs, and zombie lifecycle/state run records.

    Best-effort/fail-open throughout (A26.3): each lane runs in its OWN try/except so one
    lane's catastrophic failure (a permission error listing a whole directory, for
    example) can never prevent the others from completing their own sweep — this is a
    second, inner safety net; the caller (``_reconcile_working_tree``) wraps the whole
    call in one more, outer net, never the only one.
    """
    epoch_now = now if now is not None else time.time()
    dadaia_root = (workspace / ".dadaia").resolve()

    # Each lane is wrapped in its own ``contextlib.suppress(Exception)`` — one lane's
    # catastrophic failure (a permission error listing a whole directory, for example)
    # must never prevent the others from completing their own sweep (A26.3).
    sessions: list[str] = []
    with contextlib.suppress(Exception):
        sessions = _reap_sessions(workspace, dadaia_root, sess_id)

    markers: list[str] = []
    with contextlib.suppress(Exception):
        markers = _reap_markers(workspace, dadaia_root, set(sessions), now=epoch_now)

    presence_reaped: list[str] = []
    empty_dirs: list[str] = []
    with contextlib.suppress(Exception):
        presence_reaped, empty_dirs = _reap_presence(workspace, dadaia_root, sess_id)

    lifecycle_runs: list[str] = []
    with contextlib.suppress(Exception):
        lifecycle_runs = _reap_zombie_lifecycle_runs(workspace, dadaia_root)

    return ReapOutcome(
        sessions=tuple(sessions),
        presence=tuple(presence_reaped),
        markers=tuple(markers),
        empty_context_dirs=tuple(empty_dirs),
        lifecycle_runs=tuple(lifecycle_runs),
    )


def _append_reap_event(workspace: Path, sess_id: str, outcome: ReapOutcome) -> None:
    """Append a ``RECONCILER_REAP`` advisory event (best-effort) — only ever called when
    something was actually reaped, so an ordinary no-op pass adds no log noise."""
    _append_reconciler_event(
        workspace,
        {
            "ts": datetime.now(tz=UTC).isoformat(),
            "event": "RECONCILER_REAP",
            "session_id": sess_id,
            "sessions_reaped": len(outcome.sessions),
            "presence_reaped": len(outcome.presence),
            "markers_reaped": len(outcome.markers),
            "empty_context_dirs_removed": len(outcome.empty_context_dirs),
            "lifecycle_runs_reaped": len(outcome.lifecycle_runs),
            "note": "FR26 stale-record reap; best-effort, fail-open",
        },
    )


def _reconcile_working_tree(workspace: Path, sess_id: str) -> None:
    """Advisory reconciler pass — flags dirty MUTATING paths in the bound repo. NEVER blocks.

    Order (throttle FIRST, before any git child):
      1. throttled within the window ⇒ return (no git spawned).
      2. FR26/T-043-41: reap stale session/presence records + their tmp markers + now-empty
         presence context dirs + zombie lifecycle run records, on the SAME throttle cadence
         ("the reconciler reaps what it already walks" — no second, independent, unthrottled
         sweep on every tool call).
      3. no bound context ⇒ nothing to reconcile.
      4. ``git status --porcelain`` of the context repo fails ⇒ no event (fail-open).
      5. any dirty path classifies MUTATING ⇒ append RECONCILER_FLAG.

    Every branch stamps the throttle marker on exit so the next call inside the window is a
    no-op. Any exception is swallowed by the caller's ``main`` try/except (fail-open).
    """
    now = time.time()
    if _throttled(workspace, sess_id, now=now):
        return
    # Stamp immediately so even a slow/erroring pass throttles the next invocation.
    _stamp_throttle(workspace, sess_id)

    # FR26 (T-043-41): isolated in its own try/except so a reap failure can never prevent
    # the advisory git-status pass below — best-effort/fail-open (A26.3), matching every
    # other branch of this reconciler.
    try:
        outcome = _reap_stale_records(workspace, sess_id, now=now)
        if (
            outcome.sessions
            or outcome.presence
            or outcome.markers
            or outcome.empty_context_dirs
            or outcome.lifecycle_runs
        ):
            _append_reap_event(workspace, sess_id, outcome)
    except Exception:  # noqa: BLE001 — fail-open: a reap bug must never break the reconciler.
        pass

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
