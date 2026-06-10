"""Session-identity consolidation — the single owner of "who is this session".

WS-R3 / FR-R3-01..03 (release v0.1.10). Before this module, four fragmented
identity/liveness artifacts answered "who is this session" with two key schemes and
no single owner (arch F7):

- ``.dadaia/states/ctx_locks/<ctx>.lock.json``    (the lease record — owned by ``lease.py``)
- ``.dadaia/sessions/runtime/<ctx>.ptr``          (lease incumbent pointer)
- ``.dadaia/sessions/runtime/<session_id>.ptr``   (ctx_inject session pointer)
- ``.dadaia/sessions/<id>.json``                  (session record: id, mode, pid, …)

This module is the **sole reader/writer** of the two pointer namespaces and the session
record. ``lease.py`` keeps ownership of the *lease record itself* (its acquire/CAS/liveness
logic), but routes every pointer read/write through here. ``hooks/ctx_inject.py``,
``hooks/sdd_post_gate.py`` (next wave), the bind CLI (next wave), and the workspace doctor
GC all consume this module instead of constructing those paths directly.

Storage law (FR-R3-03): every artifact lives under PROTECTED ``.dadaia/sessions/`` or
``.dadaia/states/ctx_locks/``. No new gate classes are introduced — the existing PROTECTED
classification of ``.dadaia/sessions/`` already fences these from agent forgery.

Coherence law (FR-R3-02): the lease-record holder, the incumbent pointer, and the session
record may never name three different sessions for one context. :func:`coherence` reports
any divergence; the doctor consumes it as a backstop.

Migration law: stale legacy artifacts (older layouts, drifted ``.ptr`` files, expired
session records) are **ignored-and-superseded**, never migrated and never fatal. Every
read fails soft (returns ``None``/``""``) on malformed or absent input.

Atomic writes use temp-file + ``os.replace`` (atomic over an existing target on both
POSIX and Windows), matching the convention in ``hooks/_common.atomic_write_text`` and
``lease._write_record``. No fcntl/os.kill/``/proc`` — Windows-safe.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

__all__ = [
    "coherence",
    "gc_orphan_session_ptr",
    "incumbent",
    "iter_ptr_files",
    "ptr_path",
    "read_incumbent_ptr",
    "read_session",
    "read_session_ptr",
    "resolve_identity",
    "session_ptr_path",
    "session_record_path",
    "set_incumbent",
    "write_incumbent_ptr",
    "write_session",
    "write_session_ptr",
]

#: Path-traversal allowlist (CWE-22/CWE-59) shared with ``lease._validate``. Context names
#: and session ids are filename components and must never escape their directory.
_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")

#: Session-record TTL/heartbeat field names. These match the keys the bind CLI and the
#: PostToolUse heartbeat write, and the keys the doctor graveyard-GC reads.
_SESSION_HEARTBEAT_FIELD = "last_seen_at"
_SESSION_GC_TTL_FIELD = "ttl_seconds"


def _validate(name: str, *, field: str) -> str:
    if not _NAME_RE.fullmatch(name):
        raise ValueError(f"invalid {field} {name!r}: must match [A-Za-z0-9_-]+ (CWE-22/CWE-59)")
    return name


# ---------------------------------------------------------------------------
# Canonical paths — the ONLY place these path schemas are constructed.
# ---------------------------------------------------------------------------


def _runtime_dir(workspace: Path, *, create: bool = False) -> Path:
    d = workspace / ".dadaia" / "sessions" / "runtime"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _sessions_dir(workspace: Path, *, create: bool = False) -> Path:
    d = workspace / ".dadaia" / "sessions"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def ptr_path(workspace: Path, ctx: str, *, create: bool = False) -> Path:
    """Path of the lease-incumbent pointer ``sessions/runtime/<ctx>.ptr``."""
    _validate(ctx, field="context")
    return _runtime_dir(workspace, create=create) / f"{ctx}.ptr"


def session_ptr_path(workspace: Path, session_id: str, *, create: bool = False) -> Path:
    """Path of the session pointer ``sessions/runtime/<session_id>.ptr`` (ctx_inject hint)."""
    _validate(session_id, field="session_id")
    return _runtime_dir(workspace, create=create) / f"{session_id}.ptr"


def session_record_path(workspace: Path, session_id: str, *, create: bool = False) -> Path:
    """Path of the session record ``sessions/<id>.json``."""
    _validate(session_id, field="session_id")
    return _sessions_dir(workspace, create=create) / f"{session_id}.json"


def iter_ptr_files(workspace: Path) -> list[Path]:
    """Return all ``*.ptr`` files under the runtime dir (sorted, empty if absent)."""
    runtime = _runtime_dir(workspace)
    if not runtime.exists():
        return []
    return sorted(p for p in runtime.iterdir() if p.name.endswith(".ptr"))


# ---------------------------------------------------------------------------
# Atomic write primitive (temp + os.replace) — POSIX + Windows safe.
# ---------------------------------------------------------------------------


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.{uuid.uuid4().hex}.tmp"
    tmp.write_text(text, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Incumbent pointer (lease) — <ctx>.ptr
# ---------------------------------------------------------------------------


def read_incumbent_ptr(workspace: Path, ctx: str) -> str | None:
    """Read the lease incumbent pointer; returns the session_id or ``None`` (fail-soft)."""
    try:
        content = ptr_path(workspace, ctx).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return content or None


def write_incumbent_ptr(workspace: Path, ctx: str, session_id: str) -> None:
    """Write the lease incumbent pointer atomically. Raises on validation/OS error."""
    _validate(session_id, field="session_id")
    _atomic_write_text(ptr_path(workspace, ctx, create=True), session_id)


#: Aliases expressing the "incumbent of a context" concept (PLAN §R3 vocabulary).
incumbent = read_incumbent_ptr
set_incumbent = write_incumbent_ptr


# ---------------------------------------------------------------------------
# Session pointer (ctx_inject hint) — <session_id>.ptr
# ---------------------------------------------------------------------------


def read_session_ptr(workspace: Path, session_id: str) -> str | None:
    """Read the ctx_inject session pointer; returns its content or ``None`` (fail-soft)."""
    try:
        content = session_ptr_path(workspace, session_id).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return content or None


def write_session_ptr(workspace: Path, session_id: str) -> None:
    """Best-effort session-keyed pointer write (mirrors the old ctx_inject ``.ptr``).

    Fail-soft: a write failure (e.g. read-only ``.dadaia``) is swallowed — the pointer is
    a hint, never a correctness dependency. The sentinel ``"workspace"`` id is skipped, as
    it is the no-session fallback and must not create a graveyard entry.
    """
    if session_id == "workspace":
        return
    try:
        _atomic_write_text(session_ptr_path(workspace, session_id, create=True), session_id)
    except (OSError, ValueError):
        return


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


def record_for(workspace: Path, session_id: str) -> dict[str, object] | None:
    """Alias for :func:`read_session` (PLAN §R3 ``record_for(sid)`` vocabulary)."""
    return read_session(workspace, session_id)


# ---------------------------------------------------------------------------
# Identity resolution — the union view a consumer needs.
# ---------------------------------------------------------------------------


def resolve_identity(workspace: Path, ctx: str) -> dict[str, str | None]:
    """Resolve the identity view for a context: incumbent ptr + its session record mode.

    Returns a dict with ``incumbent`` (session_id from ``<ctx>.ptr`` or ``None``) and
    ``mode`` (the incumbent session record's ``mode`` if resolvable, else ``None``). Pure
    read; never raises on missing/legacy artifacts.
    """
    sid = read_incumbent_ptr(workspace, ctx)
    mode: str | None = None
    if sid is not None:
        rec = read_session(workspace, sid)
        if rec is not None:
            raw = rec.get("mode")
            mode = str(raw) if raw is not None else None
    return {"incumbent": sid, "mode": mode}


# ---------------------------------------------------------------------------
# Coherence contract (FR-R3-02): lease holder vs incumbent vs session record.
# ---------------------------------------------------------------------------


def coherence(
    workspace: Path,
    ctx: str,
    *,
    lock_holder: str | None,
) -> str | None:
    """Return a divergence message if the three identity sources disagree, else ``None``.

    The three sources for one context:

    * ``lock_holder``  — ``session_id`` from the live lease record (passed in; ``lease.py``
      owns reading it, so this module does not duplicate the lock-record path).
    * incumbent ptr    — ``<ctx>.ptr`` content.
    * session record   — the ``id``/``session_id`` field of ``sessions/<incumbent>.json``.

    Coherence (FR-R3-02): no two **present** sources may name different sessions. Absent
    sources (``None``) are not a violation — partial state is legal during acquire/relaunch.
    A drifted ptr that still has a matching session record but disagrees with a live lock
    holder is the canonical incoherence the doctor backstop reports.
    """
    ptr = read_incumbent_ptr(workspace, ctx)

    rec_id: str | None = None
    if ptr is not None:
        rec = read_session(workspace, ptr)
        if rec is not None:
            raw = rec.get("id") or rec.get("session_id")
            rec_id = str(raw) if raw else None

    present: list[tuple[str, str]] = []
    if lock_holder:
        present.append(("lock-holder", lock_holder))
    if ptr:
        present.append(("incumbent-ptr", ptr))
    if rec_id:
        present.append(("session-record", rec_id))

    names = {value for _label, value in present}
    if len(names) <= 1:
        return None

    detail = ", ".join(f"{label}={value!r}" for label, value in present)
    return f"session-identity incoherence for context {ctx!r}: {detail}"


# ---------------------------------------------------------------------------
# Doctor GC helpers (routed through this module so the doctor never opens the
# pointer namespace directly — FR-R3-01).
# ---------------------------------------------------------------------------


def gc_orphan_session_ptr(workspace: Path, session_id: str) -> bool:
    """Delete the session pointer ``<session_id>.ptr`` if present. Returns True if removed."""
    try:
        path = session_ptr_path(workspace, session_id)
    except ValueError:
        return False
    if path.exists():
        path.unlink(missing_ok=True)
        return True
    return False
