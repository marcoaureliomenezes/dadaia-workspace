"""Session record storage — the sole reader/writer of ``.dadaia/sessions/<id>.json``.

Caller-scoped records only; every read fails soft. ``last_seen_at`` is the one liveness
clock (stamped at bind, renewed by every hook event carrying the session's id); a record
dies only after a day of silence, never a pause. The bind-CLI ``pid`` is never consulted.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write

__all__ = [
    "SESSION_HEARTBEAT_FIELD",
    "read_session",
    "session_record_path",
    "sessions_dir",
    "touch_last_seen_at",
    "write_session",
]

#: Path-traversal allowlist (CWE-22/CWE-59) for filename components.
_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")

SESSION_HEARTBEAT_FIELD = "last_seen_at"
SESSION_GC_TTL_SECONDS = 86400


def _validate(name: str, *, field: str) -> str:
    if not _NAME_RE.fullmatch(name):
        raise ValueError(f"invalid {field} {name!r}: must match [A-Za-z0-9_-]+ (CWE-22/CWE-59)")
    return name


def sessions_dir(workspace: Path, *, create: bool = False) -> Path:
    d = workspace / ".dadaia" / "sessions"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def session_record_path(workspace: Path, session_id: str, *, create: bool = False) -> Path:
    _validate(session_id, field="session_id")
    return sessions_dir(workspace, create=create) / f"{session_id}.json"


def read_session(workspace: Path, session_id: str) -> dict[str, object] | None:
    """The session record, or ``None`` on any error."""
    try:
        data = json.loads(session_record_path(workspace, session_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_session(workspace: Path, session_id: str, record: dict[str, object]) -> None:
    """Write the session record atomically. Raises on validation/OS error."""
    path = session_record_path(workspace, session_id, create=True)
    atomic_write(path, json.dumps(record, indent=2), ensure_parent=True, newline=None)


def touch_last_seen_at(workspace: Path, session_id: str, *, now: str) -> dict[str, object] | None:
    """The heartbeat: renew ``last_seen_at``; the updated record, or ``None`` when absent or
    unwritable."""
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
    *, session_id: str, context: str, runtime: str, pid: int, now: str
) -> dict[str, object]:
    """The one session-binding record author; readers use ``.get``, so extra keys are ignored."""
    return {
        "session_id": session_id,
        "context": context,
        "runtime": runtime,
        "pid": pid,
        "bound_at": now,
        SESSION_HEARTBEAT_FIELD: now,
    }


def is_live(record: dict[str, object], *, clock: Callable[[], datetime] | None = None) -> bool:
    """``last_seen_at`` younger than the TTL; a missing or unparsable one is not live."""
    try:
        seen = datetime.fromisoformat(str(record.get(SESSION_HEARTBEAT_FIELD)))
    except ValueError:
        return False
    now = clock() if clock is not None else datetime.now(tz=UTC)
    age = now - (seen if seen.tzinfo else seen.replace(tzinfo=UTC))
    return age.total_seconds() < SESSION_GC_TTL_SECONDS


def live_session(workspace: Path, session_id: str) -> dict[str, object] | None:
    record = read_session(workspace, session_id)
    return record if record is not None and is_live(record) else None


def _records(workspace: Path) -> list[tuple[Path, dict[str, object] | None]]:
    directory = sessions_dir(workspace)
    entries = sorted(directory.glob("*.json")) if directory.is_dir() else []
    return [(e, read_session(workspace, e.stem)) for e in entries if e.is_file()]


def stale_records(workspace: Path) -> list[Path]:
    """Every TTL-expired session record file — deleted by the reaper."""
    return [
        entry for entry, record in _records(workspace) if record is not None and not is_live(record)
    ]


def unreadable_records(workspace: Path) -> list[Path]:
    """Every record file that does not read — never stale, so doctor holds it as slop."""
    return [entry for entry, record in _records(workspace) if record is None]
