"""A ledger record changed in place in a backlog-lane or rc worktree, while the work branch appended another: merge
refuses with the sync fix line, and that rebase stops on the ledger conflicted like any file
(no union merge) — the record never lands twice.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.platform import cli_argv
from tests.fixtures.harness_env import run_bash
from tests.helpers.oslib import command, venv_dir
from tests.helpers.oslib import run as os_run
from tests.helpers.worktree_ws import commit, fixes, git, make_workspace, run


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
    printed = command(*cli_argv(venv_dir(root)), "worktree", "sync", str(tree))
    assert fix == f"fix: {printed}"
    assert run_bash(printed, cwd=root).returncode == 0  # the printed line starts the launcher
    assert run(root, "sync", str(tree)).returncode == 1  # sync stops on the conflicted ledger
    env = {"HOME": str(root), "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"}
    rebase = os_run(["git", "-C", str(tree), "rebase", "feature/0.5.0"], env=env)
    assert rebase.returncode == 1
    assert git(tree, "diff", "--name-only", "--diff-filter=U").split() == [ledger]
    assert git(tree, "show", f"HEAD:{ledger}").count('"id": "2"') == 1
