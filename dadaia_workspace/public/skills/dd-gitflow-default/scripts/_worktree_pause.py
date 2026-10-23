#!/usr/bin/env python3
"""`worktree.py pause`: park one clean lane or `wt-rc` tree as a bundle of the commits origin lacks
at `.dadaia/dist/<repo>/<name>.bundle`, then drop the tree and its local branch; `resume` brings both
back from the bundle and deletes it. Nothing is committed or pushed."""

from __future__ import annotations

from pathlib import Path

from _git import GitError
from _platform import act, command, inline
from _worktree_end import open_children, precious, refuse_dirty, rmdir, target
from _worktree_git import _row, git, locked_add, ours
from _worktree_names import LAUNCH, Refusal, branch, kind_of, tree_path
from _worktree_new import absent_levels, write_level_files


def write_bundle(repo: Path, ref: str, dest: Path) -> None:
    """Runs `git bundle create` for the commits of branch *ref* that no `origin` ref holds, into
    *dest*, and verifies it. Raises `GitError` on any failure, leaving nothing at *dest*."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    git(
        repo, "bundle", "create", str(dest), ref, "--not", "--remotes=origin"
    )  # git's lockfile leaves nothing on failure
    try:
        git(repo, "bundle", "verify", str(dest))
    except GitError:
        dest.unlink()
        raise


#: The kinds of tree that pause and an export take: the lanes and the `wt-rc`.
CARRIED = ("backlog", "hotfix", "rc")


def member(repo: str, name: str) -> str:
    """`<repo>/<name>.bundle`: where a tree's bundle sits under `.dadaia/dist/` and in an export."""
    return f"{repo}/{name}.bundle"


def carry(repo: Path, tree: Path, name: str, into: Path) -> str | None:
    """Writes the commits of the lane or `wt-rc` tree *name* at *tree* that no `origin` ref holds
    to `<into>/<repo>/<name>.bundle` and returns that member; `None`, writing nothing, when origin
    holds them all or *name* is no lane or `wt-rc`. Refuses a dirty tree first, whatever it is
    ahead."""
    if kind_of(name) not in CARRIED:
        return None
    refuse_dirty(tree)
    ref = branch(name)
    if git(repo, "rev-list", "--count", ref, "--not", "--remotes=origin").strip() == "0":
        return None
    write_bundle(repo, ref, into / (found := member(repo.name, name)))
    return found


def pause(root: Path, path: str) -> str:
    """Bundles the tree at *path*, removes it and its local `wt/` branch; refuses first, touching
    nothing, a job or task tree, a dirty one, one holding ignored files, a `wt-rc` with a tree
    open below it, and a branch origin already holds."""
    repo, tree, name, _ = target(root, path)
    land = command(*LAUNCH, "merge", str(tree))
    if kind_of(name) not in CARRIED:
        raise Refusal(f"{tree} is a {kind_of(name)} tree: only a lane or a wt-rc pauses", land)
    if not any(Path(row["path"]).resolve() == tree for row in ours(repo)):
        raise Refusal(f"{tree} is not a worktree of ours", act("agent", f"rerun with a tree path `{inline(*LAUNCH, 'list')}` prints"))  # fmt: skip
    if held := precious(tree):
        raise Refusal(
            f"{tree} holds ignored files: {', '.join(held)}",
            act("agent", f"delete or commit {', '.join(held)}, then rerun the pause"),
        )
    if kind_of(name) == "rc":
        open_children(repo, name)
    ref, dist = branch(name), root / ".dadaia" / "dist"
    if (found := carry(repo, tree, name, dist)) is None:
        raise Refusal(f"{ref} holds no commit origin lacks", land)
    git(repo, "worktree", "unlock", str(tree), check=False)
    git(repo, "worktree", "remove", str(tree))
    rmdir(tree, name)
    git(repo, "update-ref", "-d", f"refs/heads/{ref}")
    return f"paused {ref} at {dist / found}"


def resume(root: Path, path: str) -> str:
    """Recreates the local `wt/` branch and the tree at *path* from its pause bundle, then deletes
    the bundle and the `dist/<repo>/` folders it leaves empty; refuses, touching nothing, a branch
    that exists or a missing bundle."""
    repo, tree, name, _ = target(root, path)
    ref, dist = branch(name), root / ".dadaia" / "dist" / repo.name
    bundle = dist / f"{name}.bundle"
    if git(repo, "branch", "--list", ref).strip():
        raise Refusal(f"{ref} exists", command(*LAUNCH, "clean", str(tree)))  # fmt: skip
    if not bundle.is_file():
        raise Refusal(f"no bundle at {bundle}", act("agent", f"rerun with the tree of a bundle under {dist}"))  # fmt: skip
    made = absent_levels(root, repo.name, name)
    git(repo, "fetch", "-q", str(bundle), f"{ref}:{ref}")
    try:
        git(repo, *locked_add(name, "-q"), str(tree), ref)
    except GitError:
        git(repo, "update-ref", "-d", f"refs/heads/{ref}")
        raise
    write_level_files(made)
    bundle.unlink()
    for folder in bundle.parents:
        if folder == dist.parent or any(folder.iterdir()):
            break
        folder.rmdir()
    return f"resumed {ref} at {tree}"


def paused_rows(root: Path) -> list[dict[str, object]]:
    """One `paused` row per `.dadaia/dist/<repo>/**/*.bundle`: `path` is the tree `resume` takes,
    `exit` the resume line."""
    out: list[dict[str, object]] = []
    for bundle in sorted((root / ".dadaia" / "dist").glob("*/**/*.bundle")):
        repo, *_ = bundle.relative_to(root / ".dadaia" / "dist").parts
        name = bundle.relative_to(root / ".dadaia" / "dist" / repo).with_suffix("").as_posix()
        path = str(tree_path(root, repo, name))
        out.append(_row(Path(repo), path, "paused", name=name, kind="paused"))
    return out
