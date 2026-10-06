"""trio-status-canon-judged-outside-the-define-merge-gate: a `define` merge runs the workspace
doctor on its own `specs/` — the check the work branch's CI runs — fenced to the tree, so a tree
the doctor refuses never lands. Size: MEDIUM (real git, tmp workspace, a stub CLI).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import approve, commit, git, make_workspace, run

pytestmark = pytest.mark.integration


def test_a_define_merge_runs_the_doctor_fenced_to_its_tree(tmp_path: Path) -> None:
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "0.5.0-rc1/define").returncode == 0
    tree = root / "worktrees/r/0.5.0-rc1/define"
    approve(root, commit(tree, "specs/RED-doctor", ""))
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1 and "dadaia doctor check failed" in refused.stderr
    out = refused.stdout.splitlines()
    assert out[0] == f"doctor --specs-dir {tree}/specs" and out[2] == f"cwd {tree}"
    assert str(root) in out[1].removeprefix("fenced ").split(os.pathsep)  # no workspace acted on
    git(tree, "rm", "-q", "specs/RED-doctor")
    git(tree, "commit", "-qm", "doctor-clean")
    approve(root, git(tree, "rev-parse", "HEAD").strip(), at="T11:00:00Z")
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
