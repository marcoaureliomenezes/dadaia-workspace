"""Characterization net for the public ``worktree.py hash`` seam owned by CP1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import commit, diff_hash, git, make_workspace, run

pytestmark = pytest.mark.slow(reason="runs the public script over a real Git worktree")


def test_hash_prints_the_exact_verdict_binding_without_writing(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    repo = root / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    name = "0.5.0-rc1/define"
    assert run(root, "new", "r", name).returncode == 0
    tree = root / "worktrees/r" / name
    head = commit(tree, "specs/note.md", "characterized\n")
    before = git(tree, "status", "--porcelain", "-uno")

    result = run(root, "hash", str(tree), "--sha", head)

    assert (result.returncode, result.stderr) == (0, "")
    assert json.loads(result.stdout) == {
        "root": str(root),
        "scope": f"wt/{name}@{head}",
        "reviewed_sha": head,
        "diff_sha256": diff_hash(root, head),
    }
    assert git(tree, "status", "--porcelain", "-uno") == before == ""
