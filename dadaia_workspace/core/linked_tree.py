"""Linked-tree predicates: which ``.git`` files git wrote for a worktree of this workspace.

Side effects: reads files only; symlinks are never followed.
"""

from __future__ import annotations

from pathlib import Path, PurePath

from dadaia_workspace.core import platform


def gitdir(entry: Path) -> PurePath | None:
    """The gitdir a regular, non-link ``.git`` file names, else ``None``."""
    if not entry.is_file() or platform.is_link(entry):
        return None
    try:
        return PurePath(platform.read_text(entry).removeprefix("gitdir:").strip())
    except (OSError, platform.Undecodable):
        return None


def is_worktree_gitfile(entry: Path) -> bool:
    """A linked worktree's ``.git`` file: a regular file, not a link, whose gitdir sits in
    ``<common>/worktrees/``."""
    named = gitdir(entry)
    return named is not None and named.parent.name == "worktrees"


def _anchors(root: Path, entry: Path) -> bool:
    """A ``.git`` file whose gitdir sits in ``<root>/repos/<slug>/.git/worktrees/`` and whose
    ``gitdir`` back-pointer, written by git inside that repo, names this very file."""
    named = gitdir(entry)
    if not (
        named is not None
        and len(named.parents) > 3
        and (named.parent.name, named.parents[1].name) == ("worktrees", ".git")
        and named.parents[3] in (root / "repos", root.resolve() / "repos")
    ):
        return False
    try:
        back = platform.read_text(Path(named) / "gitdir").strip()
    except (OSError, platform.Undecodable):
        return False
    return Path(back).resolve() == entry.resolve()


def linked_tree_depths(root: Path, parts: list[str]) -> list[int]:
    """The depths (in *parts*, workspace-relative) of every ancestor below ``worktrees/<r>``
    holding a ``.git`` file that git linked from a repo of this workspace."""
    return [k for k in range(3, len(parts)) if _anchors(root, root.joinpath(*parts[:k], ".git"))]
