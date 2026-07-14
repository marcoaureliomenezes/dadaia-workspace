"""Advisory session presence: races are surfaced and never prevented.

This module is not a lock:

* :func:`upsert` can NEVER fail a write — every exception is swallowed.
* :func:`others_alive` is a pure, best-effort read used only to compose an ADVISORY
  warning; it never blocks, never raises, and excludes self/stale/corrupt records.
* :func:`renew`, :func:`clear`, and :func:`sweep` are the PostToolUse / release /
  doctor-GC counterparts — all fail-soft.

Storage
-------
One record per (context, session) at::

    .dadaia/states/presence/<ctx>/<session_id>.json

carrying ``{session_id, runtime, pid, started_at, last_seen_at}``. Records are written
atomically (temp file + ``os.replace``). Staleness reuses the single canonical TTL,
``core.kernel_tunables.PRESENCE_TTL_SECONDS`` — a
sibling whose ``last_seen_at`` is older than the TTL is excluded from
:func:`others_alive` and opportunistically swept.

A simple atomic upsert can never fail another session's work by construction.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import kernel_tunables

__all__ = [
    "PresenceRecord",
    "StaleRecordRef",
    "clear",
    "others_alive",
    "renew",
    "stale_records",
    "sweep",
    "upsert",
]

#: Path-traversal allowlist (CWE-22/CWE-59), matching
#: ``session_identity._validate``. Context names and session ids are filename
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


def _ctx_dir(workspace: Path, ctx: str) -> Path:
    return _presence_root(workspace) / ctx


def _record_path(workspace: Path, ctx: str, session_id: str) -> Path:
    return _ctx_dir(workspace, ctx) / f"{session_id}.json"


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _atomic_write_json(path: Path, data: dict[str, object]) -> None:
    """Atomic write via unique temp file + ``os.replace`` (POSIX + Windows safe)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.{uuid.uuid4().hex}.tmp"
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _is_stale(record: dict[str, object], *, now: datetime) -> bool:
    """True iff ``record``'s heartbeat is missing, unparseable, or TTL-expired.

    Presence has no process/release veto. It is advisory-only, so simple TTL-only
    staleness is both correct and sufficient.
    """
    raw = record.get("last_seen_at")
    if not isinstance(raw, str) or not raw:
        return True
    try:
        seen = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return True
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=UTC)
    elapsed = (now - seen).total_seconds()
    return elapsed >= kernel_tunables.PRESENCE_TTL_SECONDS


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
        _atomic_write_json(path, record)
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
                _atomic_write_json(path, data)
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
    """Workspace-wide, READ-ONLY report of stale/corrupt presence records (doctor --check).

    Pure predicate companion to :func:`sweep` — never deletes, never raises. ``sweep``
    reuses this exact predicate so ``check()``/``--fix`` can never disagree on what is
    reclaimable (single source of truth). A missing presence root yields ``[]``.
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


def sweep(workspace: Path) -> list[str]:
    """Workspace-wide GC of stale/corrupt presence records (doctor ``--fix`` path).

    Returns the session ids removed (best-effort; never raises). A missing presence
    root yields ``[]``. Deletes exactly what :func:`stale_records` reports.
    """
    try:
        removed: list[str] = []
        for ref in stale_records(workspace):
            path = _record_path(workspace, ref.context, ref.session_id)
            with contextlib.suppress(OSError):
                path.unlink(missing_ok=True)
            removed.append(ref.session_id)
        return removed
    except Exception:  # noqa: BLE001 — doctor GC must never raise.
        return []
