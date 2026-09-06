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
        raise WorkspaceNotInitializedError(
            f"'{root}' is not an initialized workspace (no .dadaia/). "
            f"Run 'dadaia init --workspace {root}' first."
        )
    return root


def _is_nested_inside_dotdadaia(start: Path) -> bool:
    """``True`` when *start* sits inside some ancestor's own ``.dadaia/`` tree.

    A directory literally nested under a path component named ``.dadaia``
    (e.g. ``<root>/.dadaia/tmp/<agent>/<date>/<nested-ws>/`` — the R7-sanctioned
    throwaway-workspace pattern, `DADAIA.md` §4) is workspace-INTERNAL scratch
    space, never a sub-repo. This is a different shape than a sub-repo directory
    that merely happens to carry its own sibling ``.dadaia/`` (e.g.
    ``repos/<slug>/.dadaia/`` next to ``repos/<slug>/src/``) — that case is
    unaffected and keeps ancestor-walking normally.
    """
    return any(parent.name == ".dadaia" for parent in start.resolve().parents)


def resolve_workspace_root_for_init(cwd: Path | None = None) -> Path:
    """Resolve the workspace root for a bare ``dadaia init`` (no ``--workspace``).

    Walk up from *cwd* looking for ``.dadaia/states/spec_contexts.json`` and fall
    back to *cwd* when nothing is found, so a bare invocation anywhere inside an
    existing workspace's tree re-projects that workspace's assets.

    **One boundary the walk never crosses (bug
    ``ancestor-walk-workspace-root-silent-mistarget``):** when *cwd* is itself
    nested inside an ANCESTOR workspace's own ``.dadaia/`` directory (the
    R7-sanctioned throwaway workspace under ``.dadaia/tmp/<agent>/<date>/``), the
    walk is skipped and *cwd* is returned — exactly like "no sentinel anywhere".

    An explicit ``--workspace`` never reaches here: it is authoritative at its own
    call site (``dadaia init`` creates it) and, for every verb requiring an already
    initialized target, in :func:`resolve_cli_workspace_root`.

    Returns
    -------
    Path
        Absolute path to the intended workspace root.  Never raises.
    """
    start = cwd if cwd is not None else Path.cwd()

    if _is_nested_inside_dotdadaia(start):
        return start.resolve()

    try:
        return resolve_workspace_root(start)
    except WorkspaceNotInitializedError:
        return start.resolve()
