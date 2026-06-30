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


def _read_session_record(workspace_root: Path, session_id: str) -> dict[str, object] | None:
    """Read a bound session record by id (fail-soft).

    The session-record path schema (``.dadaia/sessions/<id>.json``) is canonically owned
    by ``features.spec_context.session_identity`` (WS-R3). This ``core`` resolver cannot
    import that ``features`` module without violating the layering law (constitution §6 —
    ``core`` imports nothing upward), so it performs a self-contained, read-only,
    fail-soft read of the same canonical path. It never writes and is recorded as the
    documented core-layer reader in the ``test_session_store_ownership`` residue contract.
    """
    if not session_id or not _SESSION_ID_RE.fullmatch(session_id):
        return None
    session_file = workspace_root / ".dadaia" / "sessions" / f"{session_id}.json"
    if not session_file.is_file():
        return None
    try:
        data = json.loads(session_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _session_context(workspace_root: Path, session_id: str) -> str | None:
    data = _read_session_record(workspace_root, session_id)
    if data is None:
        return None
    context = data.get("context")
    return str(context) if context else None


def _latest_persisted_session_id(workspace_root: Path) -> str | None:
    """Return the most recently bound incumbent session id (fail-soft)."""
    runtime_dir = workspace_root / ".dadaia" / "sessions" / "runtime"
    try:
        ptrs = sorted(
            (p for p in runtime_dir.glob("*.ptr") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    for ptr in ptrs:
        try:
            session_id = ptr.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not _SESSION_ID_RE.fullmatch(session_id):
            continue
        if _read_session_record(workspace_root, session_id) is not None:
            return session_id
    return None


def resolve_bound_session_id(
    explicit: str | None = None, *, workspace_root: Path | None = None
) -> str | None:
    """Resolve a bound session id from explicit input, env, or persisted bind state."""
    if explicit:
        return explicit
    env_session = os.environ.get("DADAIA_SESSION_ID")
    if env_session:
        return env_session
    try:
        root = workspace_root or resolve_workspace_root()
        return _latest_persisted_session_id(root)
    except WorkspaceNotInitializedError:
        return None


def resolve_bound_context_name(explicit: str | None = None) -> str | None:
    """Resolve the session-bound context name.

    Resolution order is explicit argument, ``DADAIA_CONTEXT``, then the bound session
    file addressed by ``DADAIA_SESSION_ID`` or the latest persisted incumbent pointer.
    This helper deliberately does not inspect retired global context state.
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
    session_id = resolve_bound_session_id(workspace_root=workspace_root)
    return _session_context(workspace_root, session_id) if session_id else None


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
        "`dadaia context bind <name> --mode read`."
    )
