"""`worktree.py merge` of a release tree checks its ledgers with the instance's ledger scripts,
never one the tree carries. Size: MEDIUM (real git, a tmp workspace, a stub CLI).
"""

from __future__ import annotations

from pathlib import Path

from tests.helpers.worktree_ws import approve, commit, git, make_workspace, open_tree, run

RC = "0.5.0/rc-1/wt-rc"


def test_a_tree_with_no_library_keeps_the_instance_scripts(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    tree = open_tree(tmp_path, RC)
    sha = commit(tree, "specs/bugs/BUGS.jsonl", '{"id": "half"}\n')
    approve(tmp_path, sha, name=RC)
    refused = run(tmp_path, "merge", str(tree))
    assert refused.returncode == 1 and "bugs.py check failed" in refused.stderr


def test_a_backlog_lane_never_runs_a_ledger_script_it_committed(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    lane = open_tree(tmp_path, "0.5.0/wt-backlog-x")
    marker = tmp_path / "ran"
    commit(
        lane,
        "specs/x/dd-bug-resolution/scripts/bugs.py",
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
    )
    approve(tmp_path, git(lane, "rev-parse", "HEAD").strip(), name="0.5.0/wt-backlog-x")
    run(tmp_path, "merge", str(lane))
    assert not marker.exists()
