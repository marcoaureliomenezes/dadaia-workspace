"""A ledger record changed in place in a backlog-lane or rc worktree, while the work branch appended another: merge
refuses with the sync fix line, and that rebase stops on the ledger conflicted like any file
(no union merge) — the record never lands twice.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import fix_line, shell_line
from tests.helpers.worktree_ws import cli_path, commit, fixes, git, make_workspace, run


@pytest.mark.parametrize("name", ["0.5.0/wt-backlog-x", "0.5.0/rc-1/wt-rc"])
def test_in_place_ledger_change_refuses_at_rebase(tmp_path: Path, name: str) -> None:
    root, ledger = make_workspace(tmp_path), "specs/ADRs/decisions.jsonl"
    repo, tree = root / "repos/r", root / "worktrees/r" / name
    git(repo, "checkout", "-q", "feature/0.5.0")
    one, two = '{"id": "1", "status": "accepted"}\n', '{"id": "2", "status": "proposed"}\n'
    commit(repo, ledger, one + two)
    assert run(root, "new", "r", name).returncode == 0
    commit(tree, ledger, one + two.replace("proposed", "accepted"))
    commit(repo, ledger, one + two + '{"id": "3", "status": "proposed"}\n')
    (fix,) = fixes(run(root, "merge", str(tree.relative_to(root))))
    assert fix == f"fix: {fix_line(root, 'worktree', 'sync', str(tree))}"
    launcher, worktree, *verb = shlex.split(fix.removeprefix("fix: "))
    assert [launcher, worktree] == shlex.split(shell_line(str(cli_path(root)), "worktree"))
    assert run(root, *verb).returncode == 1  # sync stops on the conflicted ledger
    env = {"HOME": str(root), "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"}
    rebase = subprocess.run(
        ["git", "-C", str(tree), "rebase", "feature/0.5.0"], env=env, capture_output=True
    )
    assert rebase.returncode == 1
    assert git(tree, "diff", "--name-only", "--diff-filter=U").split() == [ledger]
    assert git(tree, "show", f"HEAD:{ledger}").count('"id": "2"') == 1
