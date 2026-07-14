"""Session identity and bind-epoch storage.

This module owns caller-scoped records at ``.dadaia/sessions/<id>.json`` and bind-epoch
markers used for context injection. It has no context-global incumbent pointer and no
concurrency authority: one session's bind can never change another session's mode.

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
import os
import re
import uuid
from collections.abc import Sequence
from pathlib import Path

__all__ = [
    "SESSION_CREATION_FIELDS",
    "SESSION_GC_TTL_FIELD",
    "SESSION_HEARTBEAT_FIELD",
    "bind_epoch_dir",
    "bind_epoch_path",
    "iter_bind_epochs",
    "liveness_timestamp",
    "read_bind_epoch_pid",
    "read_bind_epoch_pids",
    "read_session",
    "session_record_path",
    "sessions_dir",
    "touch_last_seen_at",
    "write_bind_epoch",
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

#: Cap on the number of ancestry pids kept in a bind-epoch marker (W1-7/W1-8, v0.1.47). A
#: real harness ancestry chain (harness → shell → cli) is far shallower; the cap guards a
#: corrupt/cyclic chain and bounds the marker size. Applied on both write and read.
_BIND_EPOCH_MAX_CHAIN = 8


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
# Bind-epoch marker — .dadaia/states/bind_epoch/<ctx>  (FR-W2-02, ADR-G5)
# ---------------------------------------------------------------------------
#
# A standalone marker file written by ``dadaia context bind`` on every successful
# bind. The marker doubles as the ctx-inject hook's harness-real
# context-discovery source: the bind CLI mints its own sid, so a harness session's
# ``read_session(harness_sid)`` is structurally None in the default flow, and the
# marker's mtime + name (the slug) is what the hook scans to re-inject after a bind.


def bind_epoch_dir(workspace: Path, *, create: bool = False) -> Path:
    """Path of the bind-epoch marker directory ``.dadaia/states/bind_epoch/``."""
    d = workspace / ".dadaia" / "states" / "bind_epoch"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def bind_epoch_path(workspace: Path, ctx: str, *, create: bool = False) -> Path:
    """Path of the bind-epoch marker ``.dadaia/states/bind_epoch/<ctx>``."""
    _validate(ctx, field="context")
    return bind_epoch_dir(workspace, create=create) / ctx


def write_bind_epoch(workspace: Path, ctx: str, pids: Sequence[int] | None = None) -> None:
    """Stamp the bind-epoch marker for ``ctx`` (create-or-refresh mtime), recording *pids*.

    Written on every successful bind. The marker dir is created on demand. Re-binding
    the same context refreshes the file's mtime (the hook compares it against a session
    sentinel's mtime to decide whether to re-inject).

    Session attribution (W1-7/W1-8, v0.1.47 ancestry-chain amendment): the bind process's
    ANCESTRY PID CHAIN — nearest-first (line 1 = the bind CLI's ``os.getppid()``, then its
    successive ancestors up to :data:`_BIND_EPOCH_MAX_CHAIN`) — is recorded, one decimal
    pid per line. Recording the *chain* rather than a single pid fixes the ephemeral-shell
    gap: when ``dadaia context bind`` runs through a harness Bash tool the immediate parent
    is a short-lived shell that dies, so a single-pid marker could never be matched on a
    later call; the long-lived harness pid deeper in the chain is the stable anchor both
    consumers test for **membership** against. The format is backward-compatible: a
    single-line legacy marker still reads back as a one-element chain, and ``pids`` empty
    or ``None`` writes an EMPTY marker (the legacy shape) that reads back as "no
    attribution" (ignored for injection, never a crash). Raises on validation/OS error.
    """
    path = bind_epoch_path(workspace, ctx, create=True)
    valid = [p for p in (pids or ()) if isinstance(p, int) and p > 0][:_BIND_EPOCH_MAX_CHAIN]
    if not valid:
        # Legacy shape: an empty marker. ``Path.touch`` + ``os.utime`` bumps mtime to now
        # whether or not the file already existed (the epoch-refresh contract).
        path.touch()
        os.utime(path, None)
        return
    # An atomic content write refreshes mtime to now (new inode via os.replace) — the
    # epoch-refresh contract is preserved while the chain is recorded for attribution.
    _atomic_write_text(path, "".join(f"{p}\n" for p in valid))


def read_bind_epoch_pids(workspace: Path, ctx: str) -> list[int]:
    """Return the ancestry pid chain recorded in ``ctx``'s bind-epoch marker (nearest-first).

    Each non-empty line is parsed as a positive integer; blank lines and any line that is
    not a positive integer are skipped (fail-soft). Returns ``[]`` for a legacy/empty
    marker, an all-garbage marker, an absent marker, or any OS/validation error — i.e. any
    marker that is not attributable to a specific harness session. The list is capped at
    :data:`_BIND_EPOCH_MAX_CHAIN`. Consumers test ``harness_pid in chain`` (membership),
    so the stable harness pid deep in the chain matches even after the ephemeral shell dies.
    """
    try:
        path = bind_epoch_path(workspace, ctx)
    except ValueError:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    pids: list[int] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = int(stripped)
        except ValueError:
            continue
        if value > 0:
            pids.append(value)
    return pids[:_BIND_EPOCH_MAX_CHAIN]


def read_bind_epoch_pid(workspace: Path, ctx: str) -> int | None:
    """Return the FIRST attributed pid (line 1 — nearest ancestor) of ``ctx``'s marker.

    The single-pid compatibility reader over :func:`read_bind_epoch_pids`: returns the
    first (nearest) pid of the recorded ancestry chain, or ``None`` for a legacy/empty,
    all-garbage, or absent marker. Fail-soft — never raises.
    """
    pids = read_bind_epoch_pids(workspace, ctx)
    return pids[0] if pids else None


def iter_bind_epochs(workspace: Path) -> list[tuple[str, float]]:
    """Return ``(ctx_slug, mtime)`` for every bind-epoch marker (empty if absent).

    The hook scans this to find the newest qualifying marker. Fails soft: a marker whose
    name is not a valid context slug, or that cannot be ``stat``'d, is skipped. The list
    is unsorted — the caller picks the newest by ``mtime``.
    """
    base = bind_epoch_dir(workspace)
    out: list[tuple[str, float]] = []
    try:
        entries = list(base.iterdir())
    except OSError:
        return out
    for entry in entries:
        if not _NAME_RE.fullmatch(entry.name):
            continue
        try:
            if entry.is_file():
                out.append((entry.name, entry.stat().st_mtime))
        except OSError:
            continue
    return out


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
