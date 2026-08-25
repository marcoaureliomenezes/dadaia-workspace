"""Session identity storage.

This module owns caller-scoped records at ``.dadaia/sessions/<id>.json``. It has no
context-global incumbent pointer and no concurrency authority: one session's bind can
never change another session's mode. The retired per-context marker subsystem this
module used to also own is gone — T-50-04 (SPEC v0.5.0 FR1): context-memory injection is
now driven by the session record's own ``bound_at`` field (see
``hooks.ctx_inject._session_bound_at``), and context resolution is the single authority
(``core.specs_resolver.resolve_context``).

Stale legacy artifacts and expired session records are ignored and superseded. Every
read fails soft on malformed or absent input.

Atomic writes use temp-file + ``os.replace`` (atomic over an existing target on both
POSIX and Windows). No fcntl/os.kill/``/proc`` — Windows-safe.

Bind-record liveness
--------------------
The session/bind record's ``last_seen_at`` is the GC liveness clock, refreshed by the
PostToolUse heartbeat (``hooks/sdd_post_gate._refresh_session_record``) on every tool use.
The workspace doctor's graveyard GC measures TTL against this field, so a still-active
session renews and never decays (no silent READ→IMPLEMENTATION decay), while a dead
session's bind expires after its ``ttl_seconds`` window. :func:`touch_last_seen_at` is the
single accessor the heartbeat uses to stamp+persist the field; :func:`liveness_timestamp`
is the single accessor the GC uses to read the effective liveness clock.

**TTL-from-creation fallback.** A record that carries no
``last_seen_at`` decays from its CREATION time instead — :func:`liveness_timestamp` falls
back to ``bound_at`` (the bind-CLI creation field) and then ``created_at``. This preserves
the original TTL-from-creation behavior for records written before this field existed; it
is never silently kept alive. The session-record ``pid`` is **NOT** consulted for bind GC:
it is the transient bind-CLI pid (``context.py``'s ``os.getpid()``), dead by construction,
so a pid-keyed bind GC would collect every legitimate READ bind (ADR-8 amended rationale).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write

__all__ = [
    "SESSION_CREATION_FIELDS",
    "SESSION_GC_TTL_FIELD",
    "SESSION_HEARTBEAT_FIELD",
    "liveness_timestamp",
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

#: Creation-timestamp fields, tried in order when ``last_seen_at`` is absent (TTL-from-
#: creation fallback for pre-heartbeat records). ``bound_at`` is the bind-CLI creation key.
SESSION_CREATION_FIELDS: tuple[str, ...] = ("bound_at", "created_at")


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

    The single accessor for the session-store directory. The 2 legal consumers
    (``cli/commands/context.py``, ``spec_context/doctor.py``) call this instead of
    constructing the ``.dadaia/sessions`` path themselves (ADR-12);
    ``core/specs_resolver.py`` stays the documented allowlist exception because ``core``
    cannot import this features-layer owner (constitution §6).
    """
    return _sessions_dir(workspace, create=create)


# ---------------------------------------------------------------------------
# Atomic write primitive (temp + os.replace) — POSIX + Windows safe.
# ---------------------------------------------------------------------------


def _atomic_write_text(path: Path, text: str) -> None:
    """Thin call-through shim (T-045-13) onto core.atomic_write.atomic_write (AR-1).

    ``ensure_parent=True`` matches this writer's original ``path.parent.mkdir(...)``
    call; ``newline=None`` matches its original ``Path.write_text(...)`` with no
    ``newline=""`` override (platform-default translation).
    """
    atomic_write(path, text, ensure_parent=True, newline=None)


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

    The caller owns the record schema (id, mode, pid, context, release, created_at,
    last_seen_at, …); this module owns only where and how it is persisted.
    """
    _validate(session_id, field="session_id")
    path = session_record_path(workspace, session_id, create=True)
    _atomic_write_text(path, json.dumps(record, indent=2))


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


def liveness_timestamp(record: dict[str, object]) -> str:
    """Return the effective GC liveness timestamp for a session/bind record.

    Prefers the heartbeat-renewed ``last_seen_at``; when absent (a pre-heartbeat record),
    falls back to the creation timestamp (``bound_at`` then ``created_at``) so GC decays
    such a record TTL-from-creation. Returns ``""`` when no timestamp is present at all.
    The consumer (``doctor.py`` graveyard-GC) feeds this string into
    ``core.record_liveness.is_stale`` as the record's ``heartbeat``, and that predicate
    treats an empty/non-string heartbeat as **STALE** (fail-open) — so a record that
    carries no timestamp whatsoever is collected, not preserved. The ``pid`` field is never
    consulted here (ADR-8 amended: the bind-CLI pid is dead by construction).
    """
    raw = record.get(SESSION_HEARTBEAT_FIELD)
    if isinstance(raw, str) and raw:
        return raw
    for field in SESSION_CREATION_FIELDS:
        candidate = record.get(field)
        if isinstance(candidate, str) and candidate:
            return candidate
    return ""
