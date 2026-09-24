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

import sys
from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError

#: The sentinel file whose presence marks a properly initialized workspace.
_SENTINEL = Path(".dadaia") / "states" / "spec_contexts.json"


def resolve_workspace_root(cwd: Path | None = None) -> Path:
    """Walk up from *cwd* to find the first directory containing ``.dadaia/states/spec_contexts.json``.

    Parameters
    ----------
    cwd:
        Starting directory. Defaults to ``Path.cwd()`` when *None*.

    Returns
    -------
    Path
        Absolute path to the workspace root.

    Raises
    ------
    WorkspaceNotInitializedError
        If no qualifying directory is found before reaching the filesystem
        root. The error message names the starting *cwd* that was inspected
        and every directory that was skipped because it contained ``.dadaia/``
        without ``states/spec_contexts.json``.

    Notes
    -----
    **Backward-compat guarantee:** for any workspace where ``.dadaia/states/
    spec_contexts.json`` exists at the true workspace root, the function
    returns exactly the same path as the old ``_resolve_workspace()``
    helper — because the old helper also walked up looking for ``.dadaia/``
    and the real root is the first (and only) directory satisfying both
    criteria.

    **Sub-repo behaviour:** sub-repos that ship ``.dadaia/`` for public
    asset projections are deliberately ignored. Only a directory that also
    has ``states/spec_contexts.json`` is accepted as a workspace root.
    """
    start: Path = (cwd or Path.cwd()).resolve()

    skipped: list[Path] = []

    for candidate in [start, *start.parents]:
        dadaia_dir = candidate / ".dadaia"
        if dadaia_dir.exists():
            sentinel = candidate / _SENTINEL
            if sentinel.exists():
                return candidate.resolve()
            # Has .dadaia/ but not the sentinel — sub-repo or partial init.
            skipped.append(candidate)

    raise not_initialized(start, skipped)


def not_initialized(
    searched: Path, skipped: list[Path] | None = None
) -> WorkspaceNotInitializedError:
    """THE workspace-not-found error: the searched directory, any skipped partial
    ``.dadaia/``, and one runnable ``fix:`` — ``cd`` to the running CLI's own workspace
    (its venv lives at ``<root>/.dadaia/.venv``) when that root is initialized, else
    the uvx bootstrap."""
    own = Path(sys.prefix).resolve().parent.parent
    fix = f"cd {own}" if (own / _SENTINEL).is_file() else "uvx dadaia-workspace init <dir>"
    partial = (
        f" Skipped (partial .dadaia/, no states/): {', '.join(map(str, skipped))}."
        if skipped
        else ""
    )
    return WorkspaceNotInitializedError(
        f"No initialized workspace found from '{searched}'.{partial}\nfix: {fix}"
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
        When *workspace* is given but holds no ``.dadaia/``, or when the walk
        finds no initialized workspace.
    """
    if workspace is None:
        return resolve_workspace_root(cwd)
    root = workspace.resolve()
    if not (root / ".dadaia").is_dir():
        raise not_initialized(root)
    return root
