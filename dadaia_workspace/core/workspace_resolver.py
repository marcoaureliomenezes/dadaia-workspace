"""Centralized workspace root resolver for dadaia-workspace.

Single source of truth for walking up the directory tree to find the
workspace root. A valid workspace root is a directory that contains
``.dadaia/states/spec_contexts.json`` — NOT merely ``.dadaia/``.

Sub-repos (e.g. ``repos/my-service``, ``repos/my-app``) may have
their own ``.dadaia/`` for lib projection purposes, but they do NOT have
a ``states/`` subdirectory. Those are skipped so that CLI commands run
from within any sub-repo resolve to the workspace root correctly.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.skill_owner import load_owner

_root = load_owner("dd-bug-resolution", "_root")
_workspace_of: Callable[..., Path | None] = _root.workspace_of
_fenced: Callable[[], frozenset[Path]] = _root.fenced_roots

#: The sentinel file whose presence marks a properly initialized workspace.
_SENTINEL = Path(".dadaia") / "states" / "spec_contexts.json"

#: ``os.pathsep``-separated roots never resolved — by the walk, the CLI's own venv or an
#: explicit ``--workspace`` — so no dadaia process nor child inheriting it acts on one
#: (ADR 0088): the suite and every mutating probe set it.
FENCE_ENV = "DADAIA_FENCED_ROOTS"


def fenced_env(sandbox: Path) -> dict[str, str]:
    """This environment with every root above *sandbox* fenced: a child started with it
    acts on *sandbox* only, never on the workspace owning its venv or enclosing it."""
    fence = [os.environ.get(FENCE_ENV, ""), *map(str, sandbox.resolve().parents)]
    return {**os.environ, FENCE_ENV: os.pathsep.join(p for p in fence if p)}


def resolve_workspace_root(cwd: Path | None = None) -> Path:
    """The workspace owning the running venv (only when *cwd* is None), else the first of
    *cwd* (default: the process cwd) and its ancestors holding ``.dadaia/states/
    spec_contexts.json`` — a sub-repo's bare ``.dadaia/`` is skipped. A fenced root is
    never returned; none found raises :class:`WorkspaceNotInitializedError`."""
    own = own_workspace_root() if cwd is None else None
    if own is not None:
        return own
    start = (cwd or Path.cwd()).resolve()
    root = _workspace_of(start)
    if root is None:
        fenced = _fenced()
        raise not_initialized(
            start,
            [d for d in (start, *start.parents) if (d / ".dadaia").exists() and d not in fenced],
        )
    return root


def acting_root(path: Path) -> Path | None:
    """The unfenced workspace holding *path* — where a process may act."""
    return _workspace_of(path)


def owning_root(path: Path) -> Path | None:
    """The workspace holding *path*, fenced or not — the gate's question "which root
    protects this target" alone: the fence stops a process ACTING on a root, never the
    protection of that root (bug fenced-roots-env-disables-the-gate)."""
    return _workspace_of(path, fenced=frozenset())


def own_workspace_root() -> Path | None:
    """The workspace owning the running CLI's venv (``<ws>/.dadaia/.venv``), else ``None``:
    the first rung, so a fix line runs from any cwd — outside any workspace or inside
    another one. A fenced root (:data:`FENCE_ENV`) is never its own."""
    venv = Path(sys.prefix).resolve()
    root = venv.parent.parent
    owned = venv.parent.name == ".dadaia" and (root / _SENTINEL).is_file()
    return root if owned and root not in _fenced() else None


def not_initialized(
    searched: Path, skipped: list[Path] | None = None
) -> WorkspaceNotInitializedError:
    """THE workspace-not-found error: the searched directory, any skipped partial
    ``.dadaia/``, and one ``fix:`` — the uvx bootstrap (a CLI owning a workspace never
    gets here: :func:`own_workspace_root` is the walk's first rung)."""
    partial = (
        f" Skipped (partial .dadaia/, no states/): {', '.join(map(str, skipped))}."
        if skipped
        else ""
    )
    return WorkspaceNotInitializedError(
        f"No initialized workspace found from '{searched}'.{partial}",
        fix="Operator action: run `uvx dadaia-workspace init` with the new workspace's directory",
    )


def resolve_cli_workspace_root(workspace: Path | None, cwd: Path | None = None) -> Path:
    """Resolve the workspace root for a CLI verb carrying ``--workspace``.

    One home for the flag's semantics, shared by every such verb: an explicitly
    given *workspace* is AUTHORITATIVE — it is used as given and must itself hold
    ``.dadaia/``; it is never re-resolved through the ancestor walk, which would
    silently target an enclosing workspace when the path is an uninitialized
    directory nested inside one (bug
    ``import-export-workspace-flag-re-resolves-through-ancestor-walk``).

    ``None`` keeps the cwd ancestor walk of :func:`resolve_workspace_root`.

    Raises
    ------
    WorkspaceNotInitializedError
        When *workspace* is given but holds no sentinel or is fenced, or when the walk
        finds no initialized workspace.
    """
    if workspace is None:
        return resolve_workspace_root(cwd)
    root = workspace.resolve()
    if not (root / _SENTINEL).is_file() or root in _fenced():
        raise not_initialized(root)
    return root
