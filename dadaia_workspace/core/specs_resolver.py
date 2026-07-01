"""Session-bound specs directory resolution helpers."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import typer

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

#: Path-traversal allowlist (CWE-22/CWE-59). ``DADAIA_SESSION_ID`` becomes a filename
#: component, so it must be validated before use — mirrors ``session_identity._NAME_RE``.
_SESSION_ID_RE = re.compile(r"[A-Za-z0-9_-]+")

#: Bind-epoch marker name allowlist (W1-8). A marker's filename IS the context slug and
#: becomes a ``repos/<slug>/specs`` path component, so it is validated before use
#: (CWE-22/CWE-59 defence in depth) — mirrors ``session_identity._NAME_RE``.
_CONTEXT_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")


def _session_context(workspace_root: Path) -> str | None:
    """Read the ``context`` field of the bound session record (fail-soft).

    The session-record path schema (``.dadaia/sessions/<id>.json``) is canonically owned
    by ``features.spec_context.session_identity`` (WS-R3). This ``core`` resolver cannot
    import that ``features`` module without violating the layering law (constitution §6 —
    ``core`` imports nothing upward), so it performs a self-contained, read-only,
    fail-soft read of the same canonical path. It never writes, never opens the pointer
    namespace, and is recorded as the documented core-layer reader in the
    ``test_session_store_ownership`` residue contract.
    """
    session_id = os.environ.get("DADAIA_SESSION_ID")
    if not session_id or not _SESSION_ID_RE.fullmatch(session_id):
        return None
    session_file = workspace_root / ".dadaia" / "sessions" / f"{session_id}.json"
    if not session_file.is_file():
        return None
    try:
        data = json.loads(session_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    context = data.get("context")
    return str(context) if context else None


def _persisted_bind_context(workspace_root: Path) -> str | None:
    """Resolve the context of the single bind-epoch marker attributed to this session.

    W1-8 (T-47-17). After the ``DADAIA_CONTEXT`` env var and the bound session record, a
    workspace shell that ran ``dadaia context bind <ctx>`` still exports no env — but the
    bind wrote ``.dadaia/states/bind_epoch/<ctx>`` recording the invoking harness pid (W1-7).
    This resolver runs inside a ``dadaia`` CLI child of that SAME shell, so its
    ``os.getppid()`` equals the pid the bind recorded; a marker whose recorded pid matches is
    attributable to this session and its context resolves. It reuses the bind CLI's ancestry
    seam (``os.getppid()`` — the parent shell), staying pure-stdlib so this ``core`` module
    needs no upward import (constitution §6): exactly like ``_session_context`` above, it
    performs a self-contained, read-only, fail-soft read of the canonical bind-epoch path
    rather than importing ``features.spec_context.session_identity``.

    Exactly ONE attributable marker ⇒ that context name. None, or MORE THAN ONE (ambiguous),
    ⇒ ``None`` (the caller's cwd fallback / error path is unchanged). Legacy/empty markers,
    foreign-pid markers, and any OS/parse error are ignored — the fallback is best-effort and
    never raises.
    """
    epoch_dir = workspace_root / ".dadaia" / "states" / "bind_epoch"
    try:
        entries = list(epoch_dir.iterdir())
    except OSError:
        return None
    harness_pid = os.getppid()
    matched: list[str] = []
    for entry in entries:
        if not _CONTEXT_NAME_RE.fullmatch(entry.name) or not entry.is_file():
            continue
        try:
            text = entry.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not text:
            continue  # legacy/empty marker — unattributable
        try:
            marker_pid = int(text)
        except ValueError:
            continue
        if marker_pid > 0 and marker_pid == harness_pid:
            matched.append(entry.name)
    if len(matched) == 1:
        return matched[0]
    return None


def resolve_bound_context_name(explicit: str | None = None) -> str | None:
    """Resolve the session-bound context name.

    Resolution order is explicit argument, ``DADAIA_CONTEXT``, the bound session file
    addressed by ``DADAIA_SESSION_ID``, then the persisted bind-epoch marker attributed to
    this session's harness ancestry (W1-8 — so a bound workspace shell resolves its context
    with no env). This helper deliberately does not inspect retired global context state.
    """
    if explicit:
        return explicit
    env_context = os.environ.get("DADAIA_CONTEXT")
    if env_context:
        return env_context
    try:
        workspace_root = resolve_workspace_root()
    except WorkspaceNotInitializedError:
        return None
    session_context = _session_context(workspace_root)
    if session_context:
        return session_context
    return _persisted_bind_context(workspace_root)


def resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve a specs/ directory from explicit input or bound session context."""
    if specs_dir:
        return Path(specs_dir).resolve()

    cwd = Path.cwd()
    try:
        workspace_root = resolve_workspace_root(cwd)
    except WorkspaceNotInitializedError:
        workspace_root = None

    if workspace_root is not None:
        context = resolve_bound_context_name()
        if context:
            return (workspace_root / "repos" / context / "specs").resolve()

    candidate = cwd / "specs"
    if candidate.exists():
        return candidate.resolve()

    raise typer.BadParameter(
        "Could not resolve specs_dir. Pass --specs-dir or bind a context with "
        "`eval $(dadaia context bind <name> --mode read)`."
    )
