#!/usr/bin/env python3
"""`worktree.py pause`: park one clean lane or `wt-rc` tree as a bundle of the commits origin lacks
at `.dadaia/dist/<repo>/<name>.bundle`, then drop the tree and its local branch; `resume` brings both
back from the bundle and deletes it. Nothing is committed or pushed."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from _platform import act, command
from _worktree_end import _open_children, _refuse_dirty, _target
from _worktree_git import git, ours
from _worktree_names import (
    LAUNCH,
    LEVEL_FILE,
    LOCK,
    Refusal,
    branch,
    kind_of,
    level_folders,
    tree_path,
)
from _worktree_new import _LEVELS


def write_bundle(repo: Path, ref: str, dest: Path) -> None:
    """Runs `git bundle create` for the commits of branch *ref* that no `origin` ref holds, verifies
    them, and only then moves the file to *dest*. Raises `GitError` on any failure, leaving
    nothing at *dest*."""
    home = next(p for p in dest.parents if p.is_dir())  # same filesystem, so the move is a rename
    with tempfile.TemporaryDirectory(dir=home) as scratch:
        made = Path(scratch) / "made.bundle"
        git(repo, "bundle", "create", str(made), ref, "--not", "--remotes=origin")
        git(repo, "bundle", "verify", str(made))
        dest.parent.mkdir(parents=True, exist_ok=True)
        made.replace(dest)


def pause(root: Path, path: str) -> str:
    """Bundles the tree at *path*, removes it and its local `wt/` branch; refuses first, touching
    nothing, a job or task tree, a dirty one, one holding ignored files, a `wt-rc` with a tree
    open below it, and a branch origin already holds."""
    repo, tree, name, _ = _target(root, path)
    land = command(*LAUNCH, "merge", str(tree))
    if kind_of(name) in ("main", "task"):
        raise Refusal(f"{tree} is a {kind_of(name)} tree: only a lane or a wt-rc pauses", land)
    if not any(Path(row["path"]).resolve() == tree for row in ours(repo)):
        raise Refusal(f"{tree} is not a worktree of ours", command(*LAUNCH, "list"))
    _refuse_dirty(tree)
    if any(line.startswith("!! ") for line in git(tree, "status", "--porcelain", "--ignored").splitlines()):  # fmt: skip
        raise Refusal(
            f"{tree} holds ignored files",
            act(
                "agent",
                f"delete the ignored files {tree} holds or commit them, then rerun the pause",
            ),  # fmt: skip
        )
    if kind_of(name) == "rc":
        _open_children(repo, name)
    ref = branch(name)
    if git(repo, "rev-list", "--count", ref, "--not", "--remotes=origin").strip() == "0":
        raise Refusal(f"{ref} holds no commit origin lacks", land)
    dest = root.joinpath(".dadaia", "dist", repo.name, f"{name}.bundle")
    write_bundle(repo, ref, dest)
    git(repo, "worktree", "unlock", str(tree), check=False)
    git(repo, "worktree", "remove", str(tree))
    git(repo, "update-ref", "-d", f"refs/heads/{ref}")
    return f"paused {ref} at {dest}"


def resume(root: Path, path: str) -> str:
    """Recreates the local `wt/` branch and the tree at *path* from its pause bundle, then deletes
    the bundle and the `dist/<repo>/` folders it leaves empty; refuses, touching nothing, a branch
    that exists or a missing bundle."""
    repo, tree, name, _ = _target(root, path)
    ref, dist = branch(name), root / ".dadaia" / "dist" / repo.name
    bundle = dist / f"{name}.bundle"
    if git(repo, "branch", "--list", ref).strip():
        raise Refusal(f"{ref} exists", command(*LAUNCH, "list"))
    if not bundle.is_file():
        raise Refusal(f"no bundle at {bundle}", command(*LAUNCH, "list"))
    made = [(f, lv) for f, lv in level_folders(tree_path(root, repo.name), name) if not f.exists()]
    git(repo, "fetch", "-q", str(bundle), f"{ref}:{ref}")
    git(repo, "worktree", "add", "-q", "--lock", "--reason", f"{LOCK}{name}", str(tree), ref)
    for folder, level in made:
        shutil.copyfile(_LEVELS / f"{level}.md", folder / LEVEL_FILE)
    bundle.unlink()
    for folder in bundle.parents:
        if folder == dist.parent or any(folder.iterdir()):
            break
        folder.rmdir()
    return f"resumed {ref} at {tree}"
