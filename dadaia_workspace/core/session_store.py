"""Session record storage — the sole reader/writer of ``.dadaia/sessions/<id>.json``.

Moved into ``core`` from ``features.spec_context.session_identity`` (release K1, the
"One Invocation" deepening — 2026-08-28 audit): session/bind-record persistence is a
leaf concern with no policy of its own, and :mod:`dadaia_workspace.core.invocation`
(the single context/session/root/mode resolution authority) needs to read it directly
without reaching into ``features`` (``core`` cannot import ``features`` — constitution
§6). This module owns caller-scoped records only: no context-global incumbent pointer,
no concurrency authority — one session's bind can never change another session's mode.

Stale legacy artifacts and expired session records are ignored and superseded. Every
read fails soft on malformed or absent input.

Atomic writes use temp-file + ``os.replace`` (atomic over an existing target on both
POSIX and Windows). No fcntl/os.kill/``/proc`` — Windows-safe.

Bind-record liveness
--------------------
The record's ``last_seen_at`` is the one liveness clock: stamped at bind by
:func:`new_binding_record`, renewed by the PostToolUse heartbeat through
:func:`touch_last_seen_at`, and judged by :func:`is_live` against ``ttl_seconds``. A record
without it is not live. The ``pid`` is never consulted: it is the transient bind-CLI pid,
dead by construction (ADR-8 amended).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write

__all__ = [
    "SESSION_GC_TTL_FIELD",
    "SESSION_HEARTBEAT_FIELD",
    "read_session",
    "session_record_path",
    "sessions_dir",
    "touch_last_seen_at",
    "write_session",
]

#: Path-traversal allowlist (CWE-22/CWE-59). Context names and session ids are filename
#: components and must never escape their directory.
_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")

#: Session-record TTL/heartbeat field names. These match the keys the bind CLI and the
#: PostToolUse heartbeat write, and the keys the doctor graveyard-GC reads. Public so the
#: hook and the doctor consume the canonical names from their single owner (no duplication).
SESSION_HEARTBEAT_FIELD = "last_seen_at"
SESSION_GC_TTL_FIELD = "ttl_seconds"
#: The TTL a record carries from bind, and the one a record without it is judged by.
SESSION_GC_TTL_SECONDS = 300


def _validate(name: str, *, field: str) -> str:
    if not _NAME_RE.fullmatch(name):
        raise ValueError(f"invalid {field} {name!r}: must match [A-Za-z0-9_-]+ (CWE-22/CWE-59)")
    return name


# ---------------------------------------------------------------------------
# Canonical paths — the ONLY place these path schemas are constructed.
# ---------------------------------------------------------------------------


def _sessions_dir(workspace: Path, *, create: bool = False) -> Path:
    d = workspace / ".dadaia" / "sessions"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def session_record_path(workspace: Path, session_id: str, *, create: bool = False) -> Path:
    """Path of the session record ``sessions/<id>.json``."""
    _validate(session_id, field="session_id")
    return _sessions_dir(workspace, create=create) / f"{session_id}.json"


def sessions_dir(workspace: Path, *, create: bool = False) -> Path:
    """Path of the session-record directory ``.dadaia/sessions/`` (T-011-05 / FR-W1-05).

    The single accessor for the session-store directory. Every consumer (the bind CLI,
    the workspace doctor, :mod:`core.invocation`) calls this instead of constructing the
    ``.dadaia/sessions`` path itself (ADR-12).
    """
    return _sessions_dir(workspace, create=create)


# ---------------------------------------------------------------------------
# Session record — <id>.json
# ---------------------------------------------------------------------------


def read_session(workspace: Path, session_id: str) -> dict[str, object] | None:
    """Read the session record; returns the dict or ``None`` (fail-soft on any error)."""
    try:
        sanitized = _validate(session_id, field="session_id")
    except ValueError:
        return None
    path = session_record_path(workspace, sanitized)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_session(
    workspace: Path,
    session_id: str,
    record: dict[str, object],
) -> None:
    """Write the session record atomically. Raises on validation/OS error.

    This module owns the record schema (:func:`new_binding_record`), the liveness
    predicate (:func:`is_live`/:func:`live_session`), the stale selection (:func:`stale_records`)
    and where/how records persist (F002, 20260830 audit — the record finally has an
    owning module; callers stop hand-assembling schema dicts and TTL checks).
    """
    _validate(session_id, field="session_id")
    path = session_record_path(workspace, session_id, create=True)
    atomic_write(path, json.dumps(record, indent=2), ensure_parent=True, newline=None)


# ---------------------------------------------------------------------------
# Bind-record liveness (T-011-04 / FR-W1-04) — last_seen_at read/write.
# ---------------------------------------------------------------------------


def touch_last_seen_at(
    workspace: Path,
    session_id: str,
    *,
    now: str,
) -> dict[str, object] | None:
    """Refresh the session record's ``last_seen_at`` to ``now`` and persist it atomically.

    This is the single writer the PostToolUse heartbeat uses to renew a bind's liveness
    clock. Fail-soft: returns ``None`` (no-op) when the record is absent or unwritable —
    there is nothing to refresh otherwise. Returns the updated record on success.
    """
    data = read_session(workspace, session_id)
    if data is None:
        return None
    data[SESSION_HEARTBEAT_FIELD] = now
    try:
        write_session(workspace, session_id, data)
    except (OSError, ValueError):
        return None
    return data


def new_binding_record(
    *,
    session_id: str,
    context: str,
    runtime: str,
    pid: int,
    now: str,
) -> dict[str, object]:
    """Author one session-binding record — the ONE schema author (F002).

    0.4.7 FR4: ``mode`` and ``release`` are gone — nothing reads them since the gate's
    READ block and phase rule died. Readers stay TOLERANT by construction: every reader
    in the codebase (``live_session``, ``is_live``, the Bind resolution)
    reaches for named keys with ``.get``, never iterates or validates the key set, so an
    OLD record still carrying ``mode``/``release`` parses exactly as before and its extra
    keys are simply never read. No migration, no version bump, no compatibility branch.
    """
    return {
        "session_id": session_id,
        "context": context,
        "runtime": runtime,
        "pid": pid,
        "bound_at": now,
        SESSION_HEARTBEAT_FIELD: now,
        SESSION_GC_TTL_FIELD: SESSION_GC_TTL_SECONDS,
    }


def binding_env_lines(context: str, session_id: str) -> tuple[str, str]:
    """The two eval-ready ``export`` lines that carry a binding into a shell.

    The ONE author of the `eval $(...)` contract: `context bind --print-env` and the
    `init --repo` bootstrap both print exactly these, so the two can never drift into
    two spellings of the same handshake.
    """
    return (f"export DADAIA_CONTEXT={context}", f"export DADAIA_SESSION_ID={session_id}")


def is_live(
    record: dict[str, object],
    *,
    clock: Callable[[], datetime] | None = None,
) -> bool:
    """The ONE session-record liveness rule: ``last_seen_at`` younger than ``ttl_seconds``.
    A missing or unparsable clock or TTL is not live."""
    try:
        seen = datetime.fromisoformat(str(record.get(SESSION_HEARTBEAT_FIELD)))
        ttl = int(str(record.get(SESSION_GC_TTL_FIELD, SESSION_GC_TTL_SECONDS)))
    except (TypeError, ValueError):
        return False
    now = clock() if clock is not None else datetime.now(tz=UTC)
    return (now - (seen if seen.tzinfo else seen.replace(tzinfo=UTC))).total_seconds() < ttl


def live_session(workspace: Path, session_id: str) -> dict[str, object] | None:
    """This session's record when present AND live, else ``None`` (fail-soft)."""
    record = read_session(workspace, session_id)
    if record is None or not is_live(record):
        return None
    return record


def stale_records(workspace: Path) -> list[Path]:
    """Every TTL-expired session record file — the deleter (``sweep``) removes them.
    Non-``.json`` entries are skipped; an unreadable record is never stale."""
    directory = _sessions_dir(workspace)
    entries = sorted(directory.glob("*.json")) if directory.is_dir() else []
    return [
        entry
        for entry in entries
        if entry.is_file()
        and (record := read_session(workspace, entry.stem)) is not None
        and not is_live(record)
    ]
