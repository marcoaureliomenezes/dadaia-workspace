"""Intent: CONTRACT — worktree-merge-union-duplicates-ledger-records-on-in-place-mutation:
a ledger record changed in place in a worktree, while the work branch appended another, refuses
at rebase like any file — never lands the record twice.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import commit, fixes, git, make_workspace, run

pytestmark = pytest.mark.integration


def test_in_place_ledger_change_refuses_at_rebase(tmp_path: Path) -> None:
    root, ledger = make_workspace(tmp_path), "specs/ADRs/decisions.jsonl"
    repo, tree = root / "repos/r", root / "worktrees/r/0.5.0a-backlog"
    git(repo, "checkout", "-q", "feature/0.5.0")
    one, two = '{"id": "1", "status": "accepted"}\n', '{"id": "2", "status": "proposed"}\n'
    commit(repo, ledger, one + two)
    assert run(root, "new", "r", "--kind", "backlog").returncode == 0
    commit(tree, ledger, one + two.replace("proposed", "accepted"))
    commit(repo, ledger, one + two + '{"id": "3", "status": "proposed"}\n')
    (fix,) = fixes(run(root, "merge", str(tree.relative_to(root))))
    assert shlex.split(fix.removeprefix("fix: ")) == [
        *("git", "-C", str(tree), "rebase", "feature/0.5.0")
    ]
