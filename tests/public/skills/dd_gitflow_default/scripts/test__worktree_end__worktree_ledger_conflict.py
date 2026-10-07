"""worktree-merge-union-duplicates-ledger-records-on-in-place-mutation:
a ledger record changed in place in a worktree, while the work branch appended another: merge
refuses with the rebase fix line, and that rebase stops on the ledger conflicted like any file
(no union merge, ADR 0180) — the record never lands twice.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from dadaia_workspace.core.cli_line import git_line
from tests.helpers.worktree_ws import commit, fixes, git, make_workspace, run


def test_in_place_ledger_change_refuses_at_rebase(tmp_path: Path) -> None:
    root, ledger = make_workspace(tmp_path), "specs/ADRs/decisions.jsonl"
    repo, tree = root / "repos/r", root / "worktrees/r/backlog/x"
    git(repo, "checkout", "-q", "feature/0.5.0")
    one, two = '{"id": "1", "status": "accepted"}\n', '{"id": "2", "status": "proposed"}\n'
    commit(repo, ledger, one + two)
    assert run(root, "new", "r", "backlog/x").returncode == 0
    commit(tree, ledger, one + two.replace("proposed", "accepted"))
    commit(repo, ledger, one + two + '{"id": "3", "status": "proposed"}\n')
    (fix,) = fixes(run(root, "merge", str(tree.relative_to(root))))
    assert fix == f"fix: {git_line(tree, 'rebase', 'feature/0.5.0')}"
    env = {"HOME": str(root), "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"}
    rebase = subprocess.run(shlex.split(fix.removeprefix("fix: ")), env=env, capture_output=True)
    assert rebase.returncode == 1
    assert git(tree, "diff", "--name-only", "--diff-filter=U").split() == [ledger]
    assert git(tree, "show", f"HEAD:{ledger}").count('"id": "2"') == 1
