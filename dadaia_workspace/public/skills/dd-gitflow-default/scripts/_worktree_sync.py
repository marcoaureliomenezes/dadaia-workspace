#!/usr/bin/env python3
"""`worktree.py sync <path>`: rebase a tree and every open tree below it, parents first, each
onto its base; a tree already holding its base is skipped. Local only: it never pushes."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from _worktree_end import _check_ancestor, _refuse_dirty, _target
from _worktree_git import cli_line, flow_for, git, git_line, ours, script
from _worktree_names import SCRIPT, Refusal, base_of, branch


def _cascade(root: Path, path: str) -> list[tuple[Path, str]]:
    """(tree, base) of the tree at *path* then of each open tree whose base chain leads to it."""
    repo, tree, name, onto = _target(root, path)
    if not tree.exists():
        raise Refusal(f"{tree} does not exist", f"{script(SCRIPT)} list")
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


def sync(root: Path, path: str) -> str:
    order = _cascade(root, path)
    for tree, _ in order:  # a dirty tree stops the cascade before any tree moves
        _refuse_dirty(tree)
    moved = 0
    for tree, base in order:
        if _holds(root, tree, base):
            continue
        try:
            git(tree, "rebase", base)
        except RuntimeError as error:
            git(tree, "rebase", "--abort", check=False)
            fix = (
                f"Agent action: resolve the conflict by hand (`{git_line(tree, 'rebase', base)}`), "
                f"then rerun `{cli_line(root, 'worktree', 'sync', path)}`"
            )
            raise Refusal(f"{tree} conflicts rebasing onto {base}", fix) from error
        moved += 1
    return f"{path} synced: {moved} tree(s) rebased"
