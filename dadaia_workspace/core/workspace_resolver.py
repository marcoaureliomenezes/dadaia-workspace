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


def resolve_workspace_root_for_init(
    cwd: Path | None = None,
    *,
    explicit: bool = False,
) -> Path:
    """Resolve the workspace root for ``dadaia init``.

    When *explicit* is ``True`` the supplied *cwd* is treated as the
    authoritative target: it is returned directly (resolved to an absolute
    path) without any ancestor-walk.  This is the correct behavior for
    ``dadaia init --workspace <dir>`` — the caller has told us exactly where
    to initialize, so we must not silently write into an ancestor workspace.

    When *explicit* is ``False`` (the default) the old semantics are mostly
    preserved: walk up from *cwd* looking for ``.dadaia/states/
    spec_contexts.json``, and fall back to *cwd* when nothing is found. This
    supports the no-argument invocation (``dadaia init`` with no
    ``--workspace`` flag) re-projecting assets from anywhere inside an
    existing workspace's own tree (including a sub-repo directory that has
    not yet been sentinel-initialized).

    **One boundary the walk never crosses (bug
    ``ancestor-walk-workspace-root-silent-mistarget``):** when *cwd* is itself
    nested inside an ANCESTOR workspace's own ``.dadaia/`` directory (the
    R7-sanctioned pattern for a throwaway/nested workspace created under
    ``.dadaia/tmp/<agent>/<date>/``), the ancestor-walk is skipped entirely and
    *cwd* is returned directly — exactly like "no sentinel found anywhere".
    Walking past that boundary is precisely how a naive nested-throwaway
    invocation used to silently re-project an unrelated ancestor workspace's
    harness assets instead of creating a new workspace at *cwd*.

    Parameters
    ----------
    cwd:
        Starting directory (or explicit target when *explicit=True*).
        Defaults to ``Path.cwd()`` when *None*.
    explicit:
        When ``True``, treat *cwd* as the authoritative workspace root and
        return it immediately.  When ``False``, perform the ancestor-walk
        with sentinel detection (subject to the ``.dadaia/``-nesting boundary
        above).

    Returns
    -------
    Path
        Absolute path to the intended workspace root.  Never raises.
    """
    if explicit:
        # Authoritative path: resolve to absolute but do NOT walk up.
        # The directory may not exist yet (init is allowed to create it).
        target = cwd if cwd is not None else Path.cwd()
        return target.resolve()

    start = cwd if cwd is not None else Path.cwd()

    if _is_nested_inside_dotdadaia(start):
        # Workspace-internal scratch space of an ancestor workspace — never
        # silently walk past this boundary to re-project the ancestor's assets.
        return start.resolve()

    # Legacy / default behavior: ancestor-walk with safe fallback.
    try:
        return resolve_workspace_root(start)
    except WorkspaceNotInitializedError:
        return cwd or Path.cwd()
