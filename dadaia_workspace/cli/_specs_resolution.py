"""The single CLI bind-resolution seam (v0.1.50 FR4; generalized v0.1.77 FR1).

Every resolver-driven ``dadaia`` command resolves through this module — its specs
directory via :func:`resolve_specs_dir_for_cli`, or (v0.1.77) the bound CONTEXT NAME
itself via :func:`resolve_context_for_cli`. A thin call onto the single resolution
authority (release K1, the "One Invocation" deepening, 2026-08-28 audit):
:mod:`dadaia_workspace.core.invocation`. This module's OWN job is the CLI-specific
allowlist validation FR3 documents below — resolution itself has exactly one home now.

An *explicit* context name is gated by :data:`~dadaia_workspace.core.invocation.CONTEXT_NAME_RE`
before any ``repos/<name>/specs`` join; an ambient ``DADAIA_CONTEXT`` is judged by the
authority's bind rule (a name the registry does not hold is no bind).
"""

from __future__ import annotations

import os
from pathlib import Path

from dadaia_workspace.core.invocation import CONTEXT_NAME_RE as _CONTEXT_NAME_RE
from dadaia_workspace.core.invocation import (
    HARNESS_SESSION_ID_ENV_VARS as _HARNESS_SESSION_ID_ENV_VARS,
)
from dadaia_workspace.core.invocation import alive_context_trees as _alive_context_trees
from dadaia_workspace.core.invocation import repo_owner as _repo_owner
from dadaia_workspace.core.invocation import repo_slug_for_context as _core_repo_slug
from dadaia_workspace.core.invocation import resolve as _resolve_invocation
from dadaia_workspace.core.invocation import (
    resolve_context_specs_dir as _core_resolve_context_specs_dir,
)
from dadaia_workspace.core.invocation import resolve_session_id as _resolve_session_id
from dadaia_workspace.core.invocation import resolve_specs_dir as _core_resolve_specs_dir

#: Re-exports so a verb never reaches ``core.invocation`` directly (FR3,
#: ``bind-resolution-seam-is-a-single-home``). The contract takes ZERO ignore_imports,
#: so every consumer of the harness-session-id env-var list, the session-id rule, or the
#: name->repo-slug mapping routes through this seam.
HARNESS_SESSION_ID_ENV_VARS = _HARNESS_SESSION_ID_ENV_VARS
resolve_session_id = _resolve_session_id
alive_context_trees = _alive_context_trees
repo_owner = _repo_owner


def repo_slug_for_context(workspace_root: Path, name: str) -> str:
    """The on-disk ``repos/<slug>`` directory for a context NAME (registry-backed).

    A context's NAME and its repo SLUG are two identities; deriving the directory from
    the name is the defect class fixed in the 0.4.2 arc. Verbs call this seam so the one
    registry-backed resolution stays the single source of truth.
    """
    return _core_repo_slug(workspace_root, name)


def resolve_context_for_cli(explicit: str | None) -> str:
    """Resolve the target Spec Context NAME: *explicit*, else the single authority
    (:func:`dadaia_workspace.core.invocation.resolve`) — the session's bind, else the repo
    containing the cwd. Never borrows the first ALIVE context. A traversal-shaped
    *explicit* raises :class:`ValueError` (defense-in-depth before the path join).
    """
    if explicit:
        if not _CONTEXT_NAME_RE.fullmatch(explicit):
            raise ValueError(
                f"Invalid context name {explicit!r}: context names must match "
                f"{_CONTEXT_NAME_RE.pattern!r} (letters, digits, '_', '-' only). "
                "Pass a valid Spec Context Project name."
            )
        return explicit
    resolved = _resolve_invocation(env=os.environ, cwd=Path.cwd()).context_name
    if resolved and _CONTEXT_NAME_RE.fullmatch(resolved):
        return resolved
    raise ValueError(
        "No caller-owned Spec Context is selected. Run "
        "'dadaia context bind <name>' in this session or pass "
        "'--context <name>' explicitly. Use 'dadaia context list --json' to discover "
        "available contexts."
    )


def own_bind_for_cli() -> tuple[str | None, str | None]:
    """THIS caller's ``(bound context, session id)`` — the one Bind every reader shares."""
    inv = _resolve_invocation(env=os.environ, cwd=Path.cwd())
    return inv.bind.context_name, inv.session_id


def resolve_context_specs_dir_for_cli(workspace_root: Path, context: str) -> Path:
    """Seam wrapper over the ONE context->specs resolver (T-053-01/F003): registry
    ``repo_slug`` mapping, no fallback tree (0.4.8 R4). CLI verbs import THIS, never
    ``core.invocation`` directly (bind-resolution-seam-is-a-single-home)."""
    return _core_resolve_context_specs_dir(workspace_root, context)


def resolve_specs_dir_for_cli(specs_dir: str | None) -> Path:
    """Resolve the target specs/ dir (explicit flag, else the resolution authority)."""
    return _core_resolve_specs_dir(specs_dir)


def resolve_workspace_root_for_cli(target_path: Path) -> Path:
    """The workspace root above *target_path* — the single root walk
    (:func:`dadaia_workspace.core.invocation.resolve`'s ``target_path``-first rung,
    then the CLI's own workspace, else the cwd walk). Falls back to *target_path* itself
    when nothing is found (an uninitialized/consumer tree). The seam a git-hook-spawned
    ``dadaia ci`` verb (a harness-FREE child, no session, no ``DADAIA_CONTEXT``) uses to
    resolve its workspace without importing ``core.invocation`` directly
    (``bind-resolution-seam-is-a-single-home``)."""
    return (
        _resolve_invocation(target_path=target_path, env=os.environ, cwd=Path.cwd()).workspace_root
        or target_path
    )
