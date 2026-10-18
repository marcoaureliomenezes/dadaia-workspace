#!/usr/bin/env python3
"""`worktree.py sync <path>`: rebase a tree and every open tree below it, parents first, each
onto its base; a tree already holding its base is skipped. Local only: it never pushes."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from _platform import act, command, git_inline, inline
from _worktree_end import _check_ancestor, _refuse_dirty, _target
from _worktree_git import cli_words, flow_for, git, ours
from _worktree_names import LAUNCH, Refusal, base_of, branch


def _cascade(root: Path, path: str) -> list[tuple[Path, str]]:
    """(tree, base) of the tree at *path* then of each open tree whose base chain leads to it."""
    repo, tree, name, onto = _target(root, path)
    if not tree.exists():
        raise Refusal(f"{tree} does not exist", command(*LAUNCH, "list"))
    work = flow_for(root, repo)["work"]
    below = [(row["name"], Path(row["path"])) for row in ours(repo)]
    order: list[tuple[Path, str]] = []
    queue: deque[tuple[str, Path, str]] = deque([(name, tree, onto)])
    while queue:
        current, here, base = queue.popleft()
        order.append((here, base))
        queue.extend(
            (child, child_tree, branch(current))
            for child, child_tree in below
            if base_of(child, work) == branch(current)
        )
    return order


def _holds(root: Path, tree: Path, base: str) -> bool:
    try:
        _check_ancestor(root, tree, base)
    except Refusal:
        return False
    return True


def _fork(tree: Path, key: str, base: str) -> str:
    """The commit *tree* was cut from: the one a conflicted run saved while it still holds, else the merge-base."""
    saved = git(tree, "config", "--get", f"{key}.syncfork", check=False).strip()
    if saved:
        try:
            git(tree, "merge-base", "--is-ancestor", saved, "HEAD")
            return saved
        except RuntimeError:
            pass
    return git(tree, "merge-base", "HEAD", base).strip()


def sync(root: Path, path: str) -> str:
    order = _cascade(root, path)
    for tree, _ in order:  # a dirty tree stops the cascade before any tree moves
        _refuse_dirty(tree)
    keys = {
        tree: "branch." + git(tree, "symbolic-ref", "--short", "HEAD").strip() for tree, _ in order
    }
    forks = {tree: _fork(tree, keys[tree], base) for tree, base in order}  # before any parent moves
    for tree, fork in forks.items():  # a conflict stops the run: the rerun reads these
        git(tree, "config", f"{keys[tree]}.syncfork", fork)
    moved = 0
    for tree, base in order:
        if _holds(root, tree, base):
            git(tree, "config", "--unset", f"{keys[tree]}.syncfork", check=False)
            continue
        try:
            git(tree, "rebase", "--onto", base, forks[tree])
            git(tree, "config", "--unset", f"{keys[tree]}.syncfork", check=False)
        except RuntimeError as error:
            git(tree, "rebase", "--abort", check=False)
            fix = act(
                "agent",
                f"resolve the conflict by hand (`{git_inline(tree, 'rebase', '--onto', base, forks[tree])}`), "
                f"then rerun `{inline(*cli_words(root, 'worktree', 'sync', path))}`",
            )
            raise Refusal(f"{tree} conflicts rebasing onto {base}", fix) from error
        moved += 1
    return f"{path} synced: {moved} tree(s) rebased"
