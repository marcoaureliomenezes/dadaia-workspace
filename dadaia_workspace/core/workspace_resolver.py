"""Centralized workspace root resolver for dadaia-workspace.

Single source of truth for walking up the directory tree to find the
workspace root. A valid workspace root is a directory that contains
``.dadaia/states/spec_contexts.json`` — NOT merely ``.dadaia/``.

Sub-repos (e.g. ``repos/dadaia-bots``, ``repos/tauan-games``) may have
their own ``.dadaia/`` for lib projection purposes, but they do NOT have
a ``states/`` subdirectory. Those are skipped so that CLI commands run
from within any sub-repo resolve to the workspace root correctly.
"""

from __future__ import annotations

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

    # Nothing found.
    skipped_msg = ""
    if skipped:
        skipped_list = ", ".join(str(p) for p in skipped)
        skipped_msg = f" Skipped (partial .dadaia/, no states/): {skipped_list}."

    raise WorkspaceNotInitializedError(
        f"No initialized workspace found from '{start}'."
        f"{skipped_msg}"
        f" Run 'dadaia init' at your workspace root."
    )


def resolve_workspace_root_for_init(cwd: Path | None = None) -> Path:
    """Walk up from *cwd* to find workspace root via sentinel.

    Falls back to *cwd* when no sentinel is found — safe for first-time init.

    Parameters
    ----------
    cwd:
        Starting directory. Defaults to ``Path.cwd()`` when *None*.

    Returns
    -------
    Path
        Workspace root when the sentinel is found, otherwise *cwd* (or
        ``Path.cwd()`` when *cwd* is *None*).  Never raises.
    """
    try:
        return resolve_workspace_root(cwd)
    except WorkspaceNotInitializedError:
        return cwd or Path.cwd()
