"""Intent: CONTRACT — AC1.8 / ADR 0110 (T-050-96): `worktree.py merge` refuses unless a valid
APPROVED dd-code-reviewer handoff names the worktree's HEAD sha; the fix names the validator.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.worktree_ws import approve, commit, fixes, git, make_workspace, run

pytestmark = pytest.mark.integration

TREE = "worktrees/r/0.5.0a-impl"


@pytest.mark.parametrize("verdict", ["missing", "other-sha", "REJECTED", "invalid"])
def test_merge_without_a_valid_approval_of_head_is_refused(tmp_path: Path, verdict: str) -> None:
    root = make_workspace(tmp_path)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "--kind", "impl").returncode == 0
    old = commit(root / TREE, "src/a.py")
    head = commit(root / TREE, "src/b.py")
    handoff = {
        "missing": None,
        "other-sha": lambda: approve(root, old),
        "REJECTED": lambda: approve(root, head, verdict="REJECTED"),
        "invalid": lambda: approve(root, head, valid=False),
    }[verdict]
    named = handoff() if handoff else None
    result = run(root, "merge", TREE)
    assert result.returncode == 1 and head in result.stderr
    validator = f"{root / '.dadaia/.venv/bin/dadaia'} reports validate"
    target = named if verdict in ("REJECTED", "invalid") else "--all"
    assert fixes(result) == [f"fix: {validator} {target}"]
    assert (root / TREE).is_dir() and git(root / "repos/r", "rev-parse", "feature/0.5.0") != head
