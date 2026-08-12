"""The single context-resolution authority (``DADAIA.md`` §3) and specs-dir resolution.

:func:`resolve_context` is the ONE function every consumer (CLI seam, SDD gate,
``container``, ``ctx_inject``) resolves a Spec Context NAME through; :func:`resolve_specs_dir`
layers a specs/ dir lookup on top of it.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.record_liveness import is_stale
from dadaia_workspace.core.session_env import harness_session_id
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

#: Path-traversal allowlist (CWE-22/CWE-59); reused by ``cli._specs_resolution``.
_SESSION_ID_RE = re.compile(r"[A-Za-z0-9_-]+")
_CONTEXT_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")

#: Session-record fields (mirrors ``session_identity``; ``core`` can't import ``features`` — §6).
_SESSION_HEARTBEAT_FIELD = "last_seen_at"
_SESSION_TTL_FIELD = "ttl_seconds"


def _read_session_record(workspace_root: Path, session_id: str) -> dict[str, object] | None:
    """Fail-soft, read-only ``.dadaia/sessions/<session_id>.json`` read (never writes)."""
    if not _SESSION_ID_RE.fullmatch(session_id):
        return None
    session_file = workspace_root / ".dadaia" / "sessions" / f"{session_id}.json"
    if not session_file.is_file():
        return None
    try:
        data = json.loads(session_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _context_registered(workspace_root: Path, name: str) -> bool:
    """True while *name* is registered (missing registry -> ``False``; unreadable fails
    OPEN -> ``True``, so a transient FS hiccup never invalidates every live bind)."""
    registry = workspace_root / ".dadaia" / "states" / "spec_contexts.json"
    if not registry.is_file():
        return False
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return True
    contexts = data.get("contexts", []) if isinstance(data, dict) else []
    if not isinstance(contexts, list):
        return True
    return any(
        isinstance(entry, dict) and (entry.get("name") == name or entry.get("repo_slug") == name)
        for entry in contexts
    )


def _registry_contexts(workspace_root: Path) -> list[dict[str, object]]:
    """Read the context registry's ``contexts`` list, fail-soft to ``[]``."""
    registry = workspace_root / ".dadaia" / "states" / "spec_contexts.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return []
    contexts = data.get("contexts", []) if isinstance(data, dict) else []
    return [e for e in contexts if isinstance(e, dict)] if isinstance(contexts, list) else []


def repo_slug_for_context(workspace_root: Path, name: str) -> str:
    """The ``repos/<slug>`` dir a context NAME lives in; falls back to *name* unchanged."""
    for entry in _registry_contexts(workspace_root):
        if entry.get("name") == name:
            slug = entry.get("repo_slug") or entry.get("repo")
            return slug if isinstance(slug, str) and slug else name
    return name


def context_name_for_repo_slug(workspace_root: Path, slug: str) -> str:
    """Inverse of :func:`repo_slug_for_context`: the NAME whose repo is *slug*."""
    for entry in _registry_contexts(workspace_root):
        entry_slug = entry.get("repo_slug") or entry.get("repo")
        if entry_slug == slug:
            name = entry.get("name")
            return name if isinstance(name, str) and name else slug
    return slug


def _repo_slug_under_repos(workspace_root: Path, path: Path) -> str | None:
    """First path component of *path* under ``<workspace_root>/repos/``, sanitized
    (CWE-22/CWE-59), or ``None``. *path* need not exist."""
    repos_dir = workspace_root / "repos"
    try:
        rel = path.resolve().relative_to(repos_dir.resolve())
    except (ValueError, OSError):
        return None
    parts = rel.parts
    if not parts:
        return None
    slug = parts[0]
    return slug if _CONTEXT_NAME_RE.fullmatch(slug) else None


def _live_session_context(workspace_root: Path) -> str | None:
    """Rung 2: this session's own LIVE record, keyed by the harness-native session id
    (never ``DADAIA_SESSION_ID`` — identity only). Fails soft on missing/stale/deleted."""
    harness_id = harness_session_id()
    if not harness_id:
        return None
    record = _read_session_record(workspace_root, harness_id)
    if record is None:
        return None
    hb, ttl = record.get(_SESSION_HEARTBEAT_FIELD), record.get(_SESSION_TTL_FIELD)
    if is_stale({"heartbeat": hb, "ttl": ttl}):
        return None
    context = record.get("context")
    context = str(context) if context else None
    if context and not _context_registered(workspace_root, context):
        return None
    return context


def resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve a specs/ dir: explicit input, else :func:`resolve_context` (no ``cwd/specs``
    fallback — ``DADAIA.md`` §3 grants no such rung); unresolved reaches the error below."""
    if specs_dir:
        return Path(specs_dir).resolve()

    cwd = Path.cwd()
    try:
        workspace_root = resolve_workspace_root(cwd)
    except WorkspaceNotInitializedError:
        workspace_root = None

    if workspace_root is not None:
        context = resolve_context()
        if context:
            slug = repo_slug_for_context(workspace_root, context)
            return (workspace_root / "repos" / slug / "specs").resolve()

    # Deferred import: hooks import this module on their hot path (F-01, v0.5.0 code
    # review) and must not pay typer's import cost for a CLI-only error type.
    import typer

    raise typer.BadParameter(
        "Could not resolve specs_dir. Pass --specs-dir or bind a context with "
        "`eval $(dadaia context bind <name> --mode read)`."
    )


def _authority_workspace_root() -> Path | None:
    """Workspace root rungs 0/3 evaluate against: ``WORKSPACE_ROOT`` env wins (hook
    transport, never a resolution rung), else the cwd-based walk; fails soft to ``None``."""
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    try:
        return resolve_workspace_root()
    except WorkspaceNotInitializedError:
        return None


def resolve_context(explicit: str | None = None, *, target_path: Path | None = None) -> str | None:
    """The single context-resolution authority — ``DADAIA.md`` §3, verbatim.

        rung 0  caller-supplied input — *explicit*, or the context derived from an
                explicit write TARGET (*target_path*) under ``<ws>/repos/<slug>/`` (a
                repo write IS explicit input — keeps ``repos/x/`` resolving ``x`` even
                while ``DADAIA_CONTEXT=y``).
        rung 1  ``DADAIA_CONTEXT``
        rung 2  this session's own LIVE record — see :func:`_live_session_context`.
        rung 3  the repo containing the current working directory.

    *target_path*/cwd resolve a repo slug first, then :func:`context_name_for_repo_slug`
    recovers the NAME. Every rung fails soft; ``None`` only when all four are exhausted."""
    if explicit:
        return explicit

    workspace_root = _authority_workspace_root()

    if workspace_root is not None and target_path is not None:
        slug = _repo_slug_under_repos(workspace_root, target_path)
        if slug:
            return context_name_for_repo_slug(workspace_root, slug)

    env_context = os.environ.get("DADAIA_CONTEXT")
    if env_context:
        return env_context

    if workspace_root is not None:
        session_context = _live_session_context(workspace_root)
        if session_context:
            return session_context

        slug = _repo_slug_under_repos(workspace_root, Path.cwd())
        if slug:
            return context_name_for_repo_slug(workspace_root, slug)

    return None
