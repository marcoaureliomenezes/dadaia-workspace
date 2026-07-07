"""Canonical harness-native session-id environment resolution (single source).

The two environment variables a Layer-1 harness exports for its live session. Consolidated
here (v0.1.55 FR4, bug ``bugs-append-ignores-persisted-bind``) so the three consumers read
the SAME list instead of duplicating the env-name literals across layers:

* ``hooks/_common.resolve_session_id`` — the shared hook seam (gate / heartbeat / ctx-inject).
* ``cli/commands/context.py`` — ``bind`` persists a session record keyed by this id.
* ``core/specs_resolver.py`` — resolves a codex/claude session's bound context via this id
  when ``DADAIA_SESSION_ID`` is absent (the CLI's calls are non-descendants of the bind, so
  the ancestry-marker path can never attribute them).

This is a ``core`` leaf: stdlib only, no upward import (constitution §6), importable by every
layer above.
"""

from __future__ import annotations

import os
import re

__all__ = [
    "ENTRY_HARNESS_ENV_VAR",
    "HARNESS_SESSION_ID_ENV_VARS",
    "entry_harness",
    "harness_session_id",
    "sanitize_session_id",
]

#: The operator / PI-seam entry-harness pin (v0.1.64 FR3/FR4). Exported by the operator's
#: shell or by the post-trust PI Ring-1 extension (set-only-when-unset — an operator pin
#: always wins). Values other than the Layer-2 worker names below are ignored.
ENTRY_HARNESS_ENV_VAR = "DADAIA_ENTRY_HARNESS"

#: The only values :func:`entry_harness` may return — the Layer-2 worker harnesses.
#: ``claude`` is deliberately absent: Claude Code is Layer-1-only (LAW 1) and is never
#: auto-defaulted as a workflow worker.
_LAYER2_ENTRY_HARNESSES: frozenset[str] = frozenset({"codex", "pi"})

#: Harness-native session-id env vars in resolution order — Claude before Codex, matching
#: ``hooks/_common.resolve_session_id``. Each is exported by its harness for the live session
#: and may be INHERITED from a parent shell and stale (the audit F-1 rotated-sid source), so a
#: consumer that maps this id to a bound context MUST guard on the record's liveness.
HARNESS_SESSION_ID_ENV_VARS: tuple[str, ...] = ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID")

_SESSION_ID_STRIP = re.compile(r"[^A-Za-z0-9_-]")


def sanitize_session_id(raw: str | None) -> str:
    """Strip a session id to ``[A-Za-z0-9_-]`` (CWE-22 path-traversal defense).

    Mirrors ``hooks/_common.sanitize_session_id`` so a session id used as a filename
    component can never escape its directory.
    """
    return _SESSION_ID_STRIP.sub("", raw or "")


def harness_session_id() -> str | None:
    """First non-empty harness-native session id from the environment, sanitized, or ``None``.

    Reads :data:`HARNESS_SESSION_ID_ENV_VARS` in order and returns the first that yields a
    non-empty sanitized value. ``DADAIA_SESSION_ID`` is deliberately NOT consulted here — this
    is specifically the harness-native id (the eval-flow override is handled by the caller).
    """
    for name in HARNESS_SESSION_ID_ENV_VARS:
        sanitized = sanitize_session_id(os.environ.get(name))
        if sanitized:
            return sanitized
    return None


def entry_harness() -> str | None:
    """Resolve the entry-session Layer-2 harness for the ``--harness auto`` sentinel.

    v0.1.64 FR3 (SPEC §9 ADR-3) resolution order:

    1. :data:`ENTRY_HARNESS_ENV_VAR` (``DADAIA_ENTRY_HARNESS``) when it holds ``codex`` or
       ``pi`` — the operator pin, or the post-trust PI Ring-1 extension's seam (FR4).
       Any other value (garbage, ``claude``, empty) is IGNORED and resolution falls through.
    2. ``CODEX_SESSION_ID`` present ⇒ ``"codex"`` (a codex entry session; may be inherited
       and stale — which is why the CLI's auto-default echoes loudly and ``--harness``
       always overrides).
    3. ``None`` — covers a Claude Code entry (Layer-1-only, never a workflow worker) and
       plain shells / CI, where the caller keeps its previous default (``fake``).

    ``claude`` is never returned. Stdlib-only; this stays a ``core`` leaf (constitution §6).
    """
    pin = (os.environ.get(ENTRY_HARNESS_ENV_VAR) or "").strip().lower()
    if pin in _LAYER2_ENTRY_HARNESSES:
        return pin
    if os.environ.get("CODEX_SESSION_ID"):
        return "codex"
    return None
