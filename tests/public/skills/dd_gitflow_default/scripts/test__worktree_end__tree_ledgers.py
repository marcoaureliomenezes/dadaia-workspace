"""`worktree.py merge` of a release tree checks the tree's ledgers with the ledger scripts the tree
carries, so a self-hosted release that changes a ledger schema merges under its own schema.
Size: MEDIUM (real git, a tmp workspace, a stub CLI).
"""

from __future__ import annotations

from pathlib import Path

from tests.helpers.worktree_ws import (
    approve,
    commit,
    git,
    make_workspace,
    open_tree,
    run,
)

RC = "0.5.0/rc-1/wt-rc"
SKILLS = "dadaia_workspace/public/skills"
OWN = (
    ("dd-bug-resolution", "bugs.py"),
    ("dd-backlog-definition", "backlog.py"),
    ("dd-release-implementation", "release.py"),
)


def _release_tree(tmp_path: Path, verdict: int, *under: str) -> tuple[Path, Path]:
    """A release tree whose ledger the instance's `bugs.py` refuses and whose own ledger scripts
    (one copy under each of the *under* folders, the library path by default) exit *verdict* on
    `check`, approved and ready to merge."""
    make_workspace(tmp_path)
    repo = tmp_path / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    tree = open_tree(tmp_path, RC)
    for skill, name in OWN:
        for folder in under or (SKILLS,):
            commit(
                tree,
                f"{folder}/{skill}/scripts/{name}",
                f'import sys\nprint("tree-{name}")\nsys.exit({verdict})\n',
            )
    sha = commit(tree, "specs/bugs/BUGS.jsonl", '{"id": "half"}\n')
    approve(tmp_path, sha, name=RC)
    return tmp_path, tree


def test_a_tree_ledger_the_trees_own_scripts_accept_merges(tmp_path: Path) -> None:
    root, tree = _release_tree(tmp_path, 0)
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
    assert not tree.exists()


def test_a_tree_ledger_the_trees_own_scripts_refuse_does_not_merge(tmp_path: Path) -> None:
    root, tree = _release_tree(tmp_path, 1)
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1
    assert "tree-bugs.py" in refused.stdout + refused.stderr
    assert tree.exists()


def test_two_tracked_copies_of_a_ledger_script_both_run_and_judge_the_tree(tmp_path: Path) -> None:
    log = tmp_path / "ran"
    script = f"import sys\nwith open({str(log)!r}, 'a') as f:\n    f.write(__file__ + '\\n')\nsys.exit(0)\n"
    root, tree = _release_tree(tmp_path, 0, SKILLS, ".agents/skills")
    rel = "dd-bug-resolution/scripts/bugs.py"
    for folder in (SKILLS, ".agents/skills"):
        commit(tree, f"{folder}/{rel}", script)
    approve(root, git(tree, "rev-parse", "HEAD").strip(), name=RC)
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
    assert sorted(log.read_text().splitlines()) == sorted(str(tree / f / rel) for f in (SKILLS, ".agents/skills"))  # fmt: skip


def test_a_tracked_ledger_script_under_a_path_with_a_space_is_the_trees_own(tmp_path: Path) -> None:
    root, tree = _release_tree(tmp_path, 0, "my lib/skills")
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
    assert not tree.exists()


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
