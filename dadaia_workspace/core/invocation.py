"""One Invocation — the single session/context/root/mode resolution authority.

Rungs (`.dadaia/AGENTS.md` §2): 0 ``explicit`` or the context owning an explicit write target under
``repos/<slug>/``; 1 the session's bind; 2 the repo containing the cwd. The workspace root is
walked from the target first, so a cwd inside a nested sandbox never shadows the real root.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dadaia_workspace.core import context_registry, workspace_resolver
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.models.spec_context import CONTEXT_NAME_RE
from dadaia_workspace.core.session_store import live_session

__all__ = [
    "CONTEXT_NAME_RE",
    "HARNESS_SESSION_ID_ENV_VARS",
    "Bind",
    "Invocation",
    "Zone",
    "all_repos",
    "alive_context_trees",
    "context_name_for_repo_slug",
    "repo_owner",
    "repo_slug_for_context",
    "resolve",
    "resolve_bind",
    "resolve_root",
    "resolve_context_specs_dir",
    "resolve_specs_dir",
    "resolve_session_id",
    "sanitize_session_id",
    "scope",
]

#: Harness-native session-id env vars, in resolution order (a modern Codex subprocess
#: exposes ``CODEX_THREAD_ID`` instead of ``CODEX_SESSION_ID``).
HARNESS_SESSION_ID_ENV_VARS: tuple[str, ...] = (
    "CLAUDE_CODE_SESSION_ID",
    "CODEX_SESSION_ID",
    "CODEX_THREAD_ID",
)

_SESSION_ID_STRIP = re.compile(r"[^A-Za-z0-9_-]")


@dataclass(frozen=True)
class Bind:
    """The session's own binding: its context and every repo slug that context owns.
    Unbound (``None``, empty ``repos``) owns no repo."""

    context_name: str | None = None
    repos: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Invocation:
    """One resolved answer to "which session, which context, which root"; unresolvable fields
    are ``None``. ``bind`` is the session's own binding, which the gate compares with the
    target-decided ``context_name``; ``rung`` is diagnostic only."""

    workspace_root: Path | None
    session_id: str | None
    context_name: str | None
    repo_slug: str | None
    specs_dir: Path | None
    bind: Bind
    rung: str


def sanitize_session_id(raw: str | None) -> str:
    """Strip a session id to ``[A-Za-z0-9_-]`` (CWE-22 path-traversal defense)."""
    return _SESSION_ID_STRIP.sub("", raw or "")


def resolve_session_id(env: Mapping[str, str]) -> str:
    """The one session-id rule, sanitized: ``DADAIA_SESSION_ID``, then
    :data:`HARNESS_SESSION_ID_ENV_VARS`, else ``""``. Env only: ``context bind`` sees no
    hook payload, so a payload id would be an id no bind can ever record (ADR 0116)."""
    candidate = env.get("DADAIA_SESSION_ID") or next(
        filter(None, map(env.get, HARNESS_SESSION_ID_ENV_VARS)), ""
    )
    return sanitize_session_id(candidate)


def _alive(entry: dict[str, object]) -> bool:
    return str(entry.get("state")).lower() == "alive" and bool(entry.get("name"))


def _main_slug(entry: dict[str, object]) -> str | None:
    """A row's main repo slug; ``None`` for a hand-edited row without one."""
    slug = context_registry.entry_slugs(entry)[0]
    return slug if isinstance(slug, str) and slug else None


def _specs_tree(workspace_root: Path, slug: str) -> Path:
    return workspace_root / "repos" / slug / "specs"


def alive_context_names(workspace_root: Path) -> list[str]:
    """The name of every ALIVE context (what ``context bind`` accepts)."""
    return [str(e["name"]) for e in context_registry.entries(workspace_root) if _alive(e)]


def _context_registered(workspace_root: Path, name: str) -> bool:
    """True while *name* is registered."""
    return any(
        e.get("name") == name or e.get("repo_slug") == name
        for e in context_registry.entries(workspace_root)
    )


def repo_slug_for_context(workspace_root: Path, name: str) -> str | None:
    """The ``repos/<slug>`` dir a context NAME lives in, or ``None`` when unregistered."""
    rows = context_registry.entries(workspace_root)
    return next((s for e in rows if e.get("name") == name and (s := _main_slug(e))), None)


def context_name_for_repo_slug(workspace_root: Path, slug: str) -> str | None:
    """The context whose main or associated repo is *slug*, or ``None``."""
    owner = _owning_entry(workspace_root, slug)
    return owner[0] if owner else None


def repo_owner(workspace_root: Path, path: Path) -> tuple[str, str, str] | None:
    """``(context, repo slug, main repo slug)`` for any path :func:`scope` gives a repo, or
    ``None`` when no registered context owns it."""
    slug, _ = scope(workspace_root, path)
    owner = _owning_entry(workspace_root, slug) if slug else None
    return (owner[0], str(slug), owner[1]) if owner else None


def _owning_entry(workspace_root: Path, slug: str) -> tuple[str, str] | None:
    for entry in context_registry.entries(workspace_root):
        main, *_ = slugs = context_registry.entry_slugs(entry)
        name = entry.get("name")
        if slug in slugs and isinstance(name, str) and name and isinstance(main, str):
            return name, main
    return None


Zone = Literal["root", "repo", "audit", "worktree"]


def scope(workspace_root: Path, path: Path) -> tuple[str | None, Zone]:
    """The one path-to-repo decider: ``(repo, zone)``. ``worktrees/<r>/**`` belongs to ``r``
    (worktree), ``repos/<r>/specs/audits/**`` is audit, the rest of ``repos/<r>/`` repo,
    anything else root. *path* need not exist; a slug outside the name grammar is root
    (CWE-22/CWE-59)."""
    try:
        parts = path.resolve().relative_to(workspace_root.resolve()).parts
    except (ValueError, OSError):
        return None, "root"
    if len(parts) < 2 or parts[0] not in ("repos", "worktrees"):
        return None, "root"
    if not CONTEXT_NAME_RE.fullmatch(parts[1]):
        return None, "root"
    if parts[0] == "worktrees":
        return parts[1], "worktree"
    return parts[1], "audit" if parts[2:4] == ("specs", "audits") else "repo"


def resolve_root(*, cwd: Path, target_path: Path | None) -> Path | None:
    """The target's own root, then the running CLI's own workspace, then the cwd's — every
    rung fenced: an Invocation is where a process acts. Reads no registry; never raises."""
    owned = workspace_resolver.acting_root(target_path) if target_path is not None else None
    return owned or workspace_resolver.own_workspace_root() or workspace_resolver.acting_root(cwd)


def _live_session_context(workspace_root: Path, session_id: str | None) -> str | None:
    record = live_session(workspace_root, session_id) if session_id else None
    context = record.get("context") if record else None
    return str(context) if context else None


def all_repos(workspace_root: Path, context_name: str) -> frozenset[str]:
    """Every repo slug *context_name* owns (main plus associated); unknown owns nothing."""
    for entry in context_registry.entries(workspace_root):
        if entry.get("name") != context_name:
            continue
        main, *associated = context_registry.entry_slugs(entry)
        return frozenset(s for s in (main or context_name, *associated) if isinstance(s, str) and s)
    return frozenset()


def resolve_bind(
    workspace_root: Path | None, session_id: str | None, env: Mapping[str, str]
) -> Bind:
    """A session with an id is bound only by its own live record; without one,
    ``DADAIA_CONTEXT`` is the bind. An unregistered name is no bind; never cwd-derived."""
    if workspace_root is None:
        return Bind()
    name = (
        _live_session_context(workspace_root, session_id)
        if session_id
        else env.get("DADAIA_CONTEXT")
    )
    if not name or not _context_registered(workspace_root, name):
        return Bind()
    return Bind(context_name=name, repos=all_repos(workspace_root, name))


def resolve(
    *,
    explicit: str | None = None,
    target_path: Path | None = None,
    env: Mapping[str, str],
    cwd: Path,
) -> Invocation:
    """Resolve session, context, root and bind once. *explicit*/*target_path* are rung 0 (a
    write under ``repos/x/`` resolves ``x`` even while bound to ``y``)."""
    root = resolve_root(cwd=cwd, target_path=target_path)
    session_id = resolve_session_id(env) or None
    bind = resolve_bind(root, session_id, env)

    def owner(path: Path | None) -> str | None:
        slug = scope(root, path)[0] if root and path else None
        return context_name_for_repo_slug(root, slug) if root and slug else None

    rungs = (
        ("explicit", explicit),
        ("target_path", owner(target_path)),
        ("bind", bind.context_name),
        ("cwd", owner(cwd)),
    )
    rung, name = next(((r, n) for r, n in rungs if n), ("none", None))
    slug = repo_slug_for_context(root, name) if root and name else None
    specs_dir = _specs_tree(root, slug).resolve() if root and slug else None
    return Invocation(root, session_id, name, slug, specs_dir, bind, rung)


def resolve_specs_dir(specs_dir: str | None) -> Path:
    """Explicit input (a symlinked root refused, once, here), else :func:`resolve`; never
    a ``cwd/specs`` fallback."""
    if specs_dir:
        path = Path(specs_dir)
        if path.is_symlink():
            raise ValueError(
                f"Refusing a symlinked specs root: {path} is a symlink. Point "
                "--specs-dir at the real directory instead of a link to it."
            )
        return path.resolve()

    inv = resolve(env=os.environ, cwd=Path.cwd())
    if inv.specs_dir is not None:
        return inv.specs_dir

    raise ValueError(
        "Could not resolve specs_dir. Pass --specs-dir or bind a context with "
        f"`{fix_line(None, 'context', 'bind', '<name>')}`."
    )


def resolve_context_specs_dir(workspace_root: Path, context: str) -> Path | None:
    """A registered context's ``specs/`` tree, existing or not; ``None`` when unregistered."""
    slug = repo_slug_for_context(workspace_root, context)
    return _specs_tree(workspace_root, slug) if slug else None


def alive_context_trees(workspace_root: Path) -> dict[str, Path]:
    """Every ALIVE context name -> its ``specs/`` tree, in registry order: one registry read
    (a hook's cost never grows with the registry, ADR 0118). Names are unique: every store
    insert refuses a registered name (``SpecContextService._validate``)."""
    return {
        str(e["name"]): _specs_tree(workspace_root, slug)
        for e in context_registry.entries(workspace_root)
        if _alive(e) and (slug := _main_slug(e))
    }
