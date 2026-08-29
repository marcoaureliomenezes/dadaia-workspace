"""Advisory session presence: races are surfaced and never prevented.

This module is not a lock:

* :func:`upsert` can NEVER fail a write — every exception is swallowed.
* :func:`others_alive` is a pure, best-effort read used only to compose an ADVISORY
  warning; it never blocks, never raises, and excludes self/stale/corrupt records.
* :func:`renew` and :func:`clear` are the PostToolUse / release counterparts — fail-soft.
* :func:`gc` is the ONLY reaper of presence records, throttle/sentinel markers, and
  now-empty presence context dirs (release 0.5.1 K2 — "presence owns liveness
  end-to-end"). Before this release four separate reapers (the workspace doctor, the
  PostToolUse reconciler, ``ctx_inject``'s own sentinel sweep, and ``tmp gc``'s marker
  lane) each re-derived staleness against a different TTL/multiplier for overlapping
  record classes — one of them (the PostToolUse reap) could delete a session's own bind
  record because a CLI-minted id and the harness-native id never matched (bug family
  ``doctor-ptr-gc-deletes-valid-lock-free-bind`` /
  ``context-release-leaves-lease-heartbeat-renewing`` /
  ``doctor-stale-lease-misdiagnosed-as-forgery``). This module now owns the whole
  domain; its only callers are ``doctor --fix`` and the PostToolUse reconciler on its
  own throttle cadence.

Storage
-------
One presence record per (context, session) at::

    .dadaia/states/presence/<ctx>/<session_id>.json

carrying ``{session_id, runtime, pid, started_at, last_seen_at}``. Records are written
atomically (temp file + ``os.replace``). Staleness reuses the single canonical TTL,
``core.kernel_tunables.PRESENCE_TTL_SECONDS``, through the ONE staleness predicate
(:func:`dadaia_workspace.core.record_liveness.is_stale`) — a sibling whose
``last_seen_at`` is older than the TTL is excluded from :func:`others_alive` and
opportunistically swept.

Every advisory throttle/sentinel marker this codebase writes under ``.dadaia/tmp/``
(``reconciler-last-<sid>``, ``presence-warn-<sid>-<ctx>``, ``ctx-inject-fired-<sid>``,
``ctx-compact-<sid>``) is a spent, self-contained throttle stamp with zero live
authority — reaping one early or late has no functional effect beyond one redundant
re-run of whatever it throttled. :func:`gc` therefore reaps every one of them by a
single, generous, mtime-only TTL (:data:`kernel_tunables.SENTINEL_GC_TTL_SECONDS`), with
no session cross-reference to get wrong. :func:`throttled`/:func:`stamp_throttle` are
the ONE mtime-throttle-marker idiom (replacing two near-identical copies, one in the
PostToolUse reconciler and one in the gate's advisory-warning throttle).

A simple atomic upsert can never fail another session's work by construction.
"""

from __future__ import annotations

import contextlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.record_liveness import is_stale

__all__ = [
    "GcReport",
    "PresenceRecord",
    "StaleRecordRef",
    "clear",
    "gc",
    "others_alive",
    "renew",
    "stale_records",
    "stamp_throttle",
    "throttled",
    "upsert",
]

#: Marker filename prefixes under ``.dadaia/tmp/`` this module owns and reaps — the SAME
#: prefixes ``hooks.sdd_post_gate`` (reconciler throttle), ``features.spec_context.
#: gate_policy`` (advisory throttle) and ``hooks.ctx_inject`` (sentinel/compact markers)
#: write. One reaper for all four (release 0.5.1 K2) — no marker prefix is ever "reaped
#: by nobody" again.
_MARKER_PREFIXES: tuple[str, ...] = (
    "reconciler-last-",
    "presence-warn-",
    "ctx-inject-fired-",
    "ctx-compact-",
)

#: GC TTL (mtime-only) for every advisory marker :func:`gc` owns — one generous floor
#: (24h) for all four throttle/sentinel idioms; see the module docstring.
_MARKER_GC_TTL_SECONDS = kernel_tunables.SENTINEL_GC_TTL_SECONDS

#: Path-traversal allowlist (CWE-22/CWE-59), matching
#: ``session_store._validate``. Context names and session ids are filename
#: components and must never escape their directory.
_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")


@dataclass(frozen=True)
class PresenceRecord:
    """A live sibling presence record surfaced by :func:`others_alive`."""

    session_id: str
    runtime: str
    pid: int | None
    started_at: str
    last_seen_at: str


@dataclass(frozen=True)
class StaleRecordRef:
    """A stale-or-corrupt presence record surfaced by :func:`stale_records` (read-only)."""

    context: str
    session_id: str


def _valid_name(name: str) -> bool:
    return bool(_NAME_RE.fullmatch(name))


def _presence_root(workspace: Path) -> Path:
    return workspace / ".dadaia" / "states" / "presence"


def _within_dadaia(path: Path, workspace: Path) -> bool:
    """AG.1/FR17: True iff *path*, fully resolved (symlinks included), falls under
    ``<workspace>/.dadaia`` (also resolved). The ONE deletion-lane guard shared by both
    reap lanes in :func:`gc` — resolve, then ``relative_to`` inside ``try/except``, never
    a string-prefix check (CWE-22 class: a sibling directory whose name string-prefixes
    the boundary)."""
    boundary = (workspace / ".dadaia").resolve()
    try:
        path.resolve().relative_to(boundary)
    except (ValueError, OSError):
        return False
    return True


def _ctx_dir(workspace: Path, ctx: str) -> Path:
    return _presence_root(workspace) / ctx


def _record_path(workspace: Path, ctx: str, session_id: str) -> Path:
    return _ctx_dir(workspace, ctx) / f"{session_id}.json"


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _is_stale(record: dict[str, object], *, now: datetime) -> bool:
    """True iff ``record``'s heartbeat is missing, unparseable, or TTL-expired.

    Presence has no process/release veto. It is advisory-only, so simple TTL-only
    staleness is both correct and sufficient. A thin adapter over the ONE staleness
    predicate (:func:`dadaia_workspace.core.record_liveness.is_stale`) — presence no
    longer parses ISO8601/computes elapsed time itself.
    """
    return is_stale(
        {"heartbeat": record.get("last_seen_at"), "ttl": kernel_tunables.PRESENCE_TTL_SECONDS},
        clock=lambda: now,
    )


def upsert(workspace: Path, ctx: str, session_id: str, *, runtime: str, pid: int) -> None:
    """Create-or-refresh this session's presence record for ``ctx``.

    NEVER raises — every exception (invalid name, permission error, disk failure) is
    swallowed. Presence is a pure side-signal; a presence I/O failure must never fail
    the write it is attached to (FR2 acceptance bar).
    """
    try:
        if not _valid_name(ctx) or not _valid_name(session_id):
            return
        path = _record_path(workspace, ctx, session_id)
        existing = _read_json(path)
        started_at = None
        if isinstance(existing, dict):
            raw_started = existing.get("started_at")
            if isinstance(raw_started, str) and raw_started:
                started_at = raw_started
        now = _utcnow_iso()
        record: dict[str, object] = {
            "session_id": session_id,
            "runtime": runtime,
            "pid": pid,
            "started_at": started_at or now,
            "last_seen_at": now,
        }
        atomic_write(path, json.dumps(record, indent=2), ensure_parent=True, newline=None)
    except Exception:  # noqa: BLE001 — presence must never fail a write (FR2).
        return


def others_alive(workspace: Path, ctx: str, session_id: str) -> list[PresenceRecord]:
    """Return every OTHER live presence record on ``ctx`` (self excluded).

    Fail-soft: an unreadable context dir, a corrupt sibling record, or an invalid name
    yields ``[]``/skips that entry — never raises. Stale siblings (heartbeat older than
    ``PRESENCE_TTL_SECONDS``) are excluded and opportunistically removed (best-effort GC).
    """
    try:
        if not _valid_name(ctx):
            return []
        ctx_dir = _ctx_dir(workspace, ctx)
        try:
            entries = list(ctx_dir.iterdir())
        except OSError:
            return []
        now = datetime.now(tz=UTC)
        alive: list[PresenceRecord] = []
        for entry in entries:
            if not entry.name.endswith(".json"):
                continue
            sid = entry.name[: -len(".json")]
            if sid == session_id:
                continue
            data = _read_json(entry)
            if data is None:
                with contextlib.suppress(OSError):
                    entry.unlink(missing_ok=True)
                continue
            if _is_stale(data, now=now):
                with contextlib.suppress(OSError):
                    entry.unlink(missing_ok=True)
                continue
            raw_pid = data.get("pid")
            alive.append(
                PresenceRecord(
                    session_id=str(data.get("session_id", sid)),
                    runtime=str(data.get("runtime", "unknown")),
                    pid=raw_pid if isinstance(raw_pid, int) else None,
                    started_at=str(data.get("started_at", "")),
                    last_seen_at=str(data.get("last_seen_at", "")),
                )
            )
        return alive
    except Exception:  # noqa: BLE001 — advisory read must never raise.
        return []


def renew(workspace: Path, session_id: str) -> int:
    """Refresh ``last_seen_at`` on every presence record ``session_id`` owns.

    Scans every context directory under the presence root (fail-soft: an absent root
    yields 0, an unreadable entry is skipped). Returns the count refreshed. Never raises
    — the PostToolUse heartbeat must never break on a presence-renewal error.
    """
    try:
        if not _valid_name(session_id):
            return 0
        root = _presence_root(workspace)
        try:
            ctx_dirs = [p for p in root.iterdir() if p.is_dir()]
        except OSError:
            return 0
        renewed = 0
        for ctx_dir in ctx_dirs:
            path = ctx_dir / f"{session_id}.json"
            data = _read_json(path)
            if data is None:
                continue
            data["last_seen_at"] = _utcnow_iso()
            with contextlib.suppress(OSError):
                atomic_write(path, json.dumps(data, indent=2), ensure_parent=True, newline=None)
                renewed += 1
        return renewed
    except Exception:  # noqa: BLE001 — heartbeat renewal must never raise.
        return 0


def clear(workspace: Path, session_id: str, ctx: str | None = None) -> int:
    """Delete ``session_id``'s own presence record(s). Idempotent; never raises.

    When ``ctx`` is given, only that context's record is removed; otherwise every
    context this session has a record in is cleared. Returns the count removed.
    """
    try:
        if not _valid_name(session_id):
            return 0
        root = _presence_root(workspace)
        removed = 0
        if ctx is not None:
            if not _valid_name(ctx):
                return 0
            path = _record_path(workspace, ctx, session_id)
            if path.exists():
                with contextlib.suppress(OSError):
                    path.unlink(missing_ok=True)
                    removed += 1
            return removed
        try:
            ctx_dirs = [p for p in root.iterdir() if p.is_dir()]
        except OSError:
            return 0
        for ctx_dir in ctx_dirs:
            path = ctx_dir / f"{session_id}.json"
            if path.exists():
                with contextlib.suppress(OSError):
                    path.unlink(missing_ok=True)
                    removed += 1
        return removed
    except Exception:  # noqa: BLE001 — release/cleanup must never raise.
        return 0


def stale_records(workspace: Path) -> list[StaleRecordRef]:
    """Workspace-wide, READ-ONLY report of stale/corrupt presence records.

    Pure predicate; never deletes, never raises. Used by ``cli.commands.doctor``'s
    ``--redact`` candidate discovery (a presence record can outlive its context's
    registry entry). Presence-record RECLAMATION itself is :func:`gc`'s job — this stays
    read-only. A missing presence root yields ``[]``.
    """
    try:
        root = _presence_root(workspace)
        try:
            ctx_dirs = [p for p in root.iterdir() if p.is_dir()]
        except OSError:
            return []
        now = datetime.now(tz=UTC)
        stale: list[StaleRecordRef] = []
        for ctx_dir in ctx_dirs:
            try:
                entries = list(ctx_dir.iterdir())
            except OSError:
                continue
            for entry in entries:
                if not entry.name.endswith(".json"):
                    continue
                sid = entry.name[: -len(".json")]
                data = _read_json(entry)
                if data is None or _is_stale(data, now=now):
                    stale.append(StaleRecordRef(context=ctx_dir.name, session_id=sid))
        return stale
    except Exception:  # noqa: BLE001 — doctor read-only report must never raise.
        return []


# ---------------------------------------------------------------------------
# throttled / stamp_throttle — the ONE mtime-throttle-marker idiom.
# ---------------------------------------------------------------------------


def throttled(workspace: Path, marker_name: str, *, window_seconds: float, now: float) -> bool:
    """True iff ``marker_name`` under ``.dadaia/tmp/`` was stamped within
    ``window_seconds`` of ``now`` (an epoch float, matching ``time.time()``).

    The ONE mtime-throttle-marker idiom (release 0.5.1 K2) — used by the PostToolUse
    reconciler (before spawning a git child) and the gate's advisory-warning throttle,
    replacing two near-identical copies. A traversal-shaped or otherwise invalid
    ``marker_name`` (anything outside ``[A-Za-z0-9_-]+`` — CWE-22/CWE-59) is rejected:
    never throttled (the caller degrades to "run now"). A missing/unreadable marker is
    likewise never throttled (fail-open -> run).
    """
    if not _valid_name(marker_name):
        return False
    marker = workspace / ".dadaia" / "tmp" / marker_name
    try:
        last = marker.stat().st_mtime
    except OSError:
        return False
    return (now - last) < window_seconds


def stamp_throttle(workspace: Path, marker_name: str) -> None:
    """Record that ``marker_name`` fired now (best-effort; never raises).

    A traversal-shaped or otherwise invalid ``marker_name`` is rejected outright — never
    written outside ``.dadaia/tmp/`` (CWE-22/CWE-59).
    """
    if not _valid_name(marker_name):
        return
    marker = workspace / ".dadaia" / "tmp" / marker_name
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(_utcnow_iso(), encoding="utf-8")
    except OSError:
        return


# ---------------------------------------------------------------------------
# gc — the ONLY reaper of presence records, throttle/sentinel markers, and now-empty
# presence context dirs (release 0.5.1 K2). See the module docstring.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GcReport:
    """Result of one :func:`gc` pass.

    Every field is a tuple of identifiers (never full paths), sorted for determinism.
    ``presence`` entries are ``"<ctx>/<session_id>"``; ``markers`` and
    ``empty_context_dirs`` are bare filenames/dirnames under ``.dadaia/tmp/`` and
    ``.dadaia/states/presence/`` respectively.
    """

    presence: tuple[str, ...] = ()
    markers: tuple[str, ...] = ()
    empty_context_dirs: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        return len(self.presence) + len(self.markers) + len(self.empty_context_dirs)


def _reap_presence_records(
    workspace: Path, *, own_session_id: str, now: datetime
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Presence records stale beyond ``PRESENCE_TTL_SECONDS``, and any context dir left
    empty afterward. ``own_session_id``'s own records are NEVER a candidate — the calling
    session (e.g. the PostToolUse reconciler) must never reap its own just-renewed
    record out from under itself.

    AG.1/FR17: a symlinked context dir is never followed (``p.is_symlink()`` skipped
    before ``p.is_dir()`` would otherwise say yes), and every unlink target is
    re-checked against :func:`_within_dadaia` — the two guards a symlinked directory
    AND a symlinked entry inside a real one, respectively."""
    root = _presence_root(workspace)
    try:
        ctx_dirs = sorted(p for p in root.iterdir() if p.is_dir() and not p.is_symlink())
    except OSError:
        return (), ()

    reaped: list[str] = []
    empty_dirs: list[str] = []
    for ctx_dir in ctx_dirs:
        try:
            entries = sorted(ctx_dir.iterdir())
        except OSError:
            continue
        remaining = 0
        for entry in entries:
            if not entry.name.endswith(".json"):
                remaining += 1
                continue
            sid = entry.name[: -len(".json")]
            if own_session_id and sid == own_session_id:
                remaining += 1
                continue
            if not _within_dadaia(entry, workspace):
                remaining += 1
                continue
            data = _read_json(entry)
            if data is not None and not _is_stale(data, now=now):
                remaining += 1
                continue
            with contextlib.suppress(OSError):
                entry.unlink(missing_ok=True)
            reaped.append(f"{ctx_dir.name}/{sid}")
        if remaining == 0:
            with contextlib.suppress(OSError):
                ctx_dir.rmdir()
                empty_dirs.append(ctx_dir.name)
    return tuple(reaped), tuple(empty_dirs)


def _reap_markers(workspace: Path, *, now: float) -> tuple[str, ...]:
    """Advisory markers under ``.dadaia/tmp/`` matching :data:`_MARKER_PREFIXES`, older
    than :data:`_MARKER_GC_TTL_SECONDS` by mtime. No session cross-reference (see the
    module docstring: every marker this reaps is a spent throttle stamp).

    AG.1/FR17: shares :func:`_within_dadaia` with the presence lane — the same guard,
    one home."""
    tmp_dir = workspace / ".dadaia" / "tmp"
    try:
        entries = sorted(tmp_dir.iterdir())
    except OSError:
        return ()
    reaped: list[str] = []
    for path in entries:
        if not path.name.startswith(_MARKER_PREFIXES):
            continue
        if not _within_dadaia(path, workspace):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if (now - mtime) < _MARKER_GC_TTL_SECONDS:
            continue
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)
            reaped.append(path.name)
    return tuple(reaped)


def gc(workspace: Path, *, now: datetime, own_session_id: str) -> GcReport:
    """The ONLY reaper of presence records, throttle/sentinel markers under
    ``.dadaia/tmp/``, and now-empty presence context dirs. NEVER raises (each lane is
    independently best-effort, mirroring :func:`upsert`/:func:`others_alive`).

    Callers: ``DoctorService.fix()`` and the PostToolUse reconciler, on its own throttle
    cadence (never on every single tool call — see ``hooks.sdd_post_gate``).
    """
    presence_reaped: tuple[str, ...] = ()
    empty_dirs: tuple[str, ...] = ()
    with contextlib.suppress(Exception):  # GC must never raise (best-effort, per lane).
        presence_reaped, empty_dirs = _reap_presence_records(
            workspace, own_session_id=own_session_id, now=now
        )

    markers: tuple[str, ...] = ()
    with contextlib.suppress(Exception):  # GC must never raise (best-effort, per lane).
        markers = _reap_markers(workspace, now=now.timestamp())

    return GcReport(presence=presence_reaped, markers=markers, empty_context_dirs=empty_dirs)
