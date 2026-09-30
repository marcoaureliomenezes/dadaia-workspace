"""Intent: CONTRACT — AC1.8 (T-050-96, T-050-108, T-050-98): `worktree.py merge` fast-forwards,
removes and `branch -d`s a reviewed worktree, re-runnable; every refusal (dirty, outside the
kind's allowed set, conflicting rebase, no APPROVED verdict for HEAD, ignored files, wrong
branch, failed fast-forward: a stray or a moved work branch) carries one `fix:` that clears it; `clean`
removes only an empty `dadaia:` worktree. AC1.9 (T-050-98): ledgers union, TASKS markers replay.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.release_state import write_release_phase
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import SCRIPT, approve, commit, fixes, git, make_workspace, run
from tests.helpers.worktree_ws import run_fix as _fix

pytestmark = pytest.mark.integration

TREE = "worktrees/r/0.5.0a-impl"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(tmp_path, "new", "r", "--kind", "impl").returncode == 0
    return tmp_path


def test_merge_fast_forwards_removes_and_reruns(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    sha = commit(tree, "src/a.py")
    approve(root, sha)
    result = run(root, "merge", TREE)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == sha
    assert not tree.exists() and not git(repo, "branch", "--list", "wt/*").strip()
    assert run(root, "merge", TREE).returncode == 0  # a finished merge re-runs clean
    assert run(root, "new", "r", "--kind", "impl").returncode == 0
    shutil.rmtree(tree)  # the dadaia:-locked tree deleted by hand: an orphan, its exit clears it
    (row,) = json.loads(run(root, "list", "--json").stdout)
    assert (row["state"], row["path"]) == ("orphan", str(tree))
    assert run(root, *shlex.split(row["exit"])[2:]).returncode == 0
    assert json.loads(run(root, "list", "--json").stdout) == []
    git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0a-impl", str(tree))
    commit(tree, "src/b.py")
    git(repo, "worktree", "remove", str(tree))  # interrupted: tree gone, its commit unmerged
    assert fixes(run(root, "merge", TREE)) == [
        f"fix: git -C {repo} worktree add {tree} wt/0.5.0a-impl"
    ]
    assert git(repo, "branch", "--list", "wt/0.5.0a-impl").strip()  # never -D


def test_dirty_outside_set_and_conflict_each_refuse_with_one_fix(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    (tree / "wip.py").write_text("")
    _fix(root, dirty := run(root, "merge", TREE))
    assert "uncommitted" in dirty.stderr
    commit(tree, "specs/backlog/BACKLOG.json", "{}")  # new: the undo removes it
    commit(tree, "specs/releases/0.5.0/rc-1/SPEC.md", "edited")  # on the work branch: restored
    for rel, owner in (("specs/backlog/BACKLOG.json", "backlog"), ("SPEC.md", "release")):
        outside = run(root, "merge", TREE)
        assert rel in outside.stderr and f"{owner} worktree" in outside.stderr
        _fix(root, outside)
    commit(repo, "README.md", "- [ ] a\n")  # markers alone, but not TASKS: never replayed
    git(tree, "rebase", "-q", "feature/0.5.0")
    commit(repo, "README.md", "- [-] a\n")
    commit(tree, "README.md", "- [x] a\n")
    conflict = run(root, "merge", TREE)
    assert not (Path(git(tree, "rev-parse", "--git-dir").strip()) / "rebase-merge").exists()
    assert fixes(conflict) == [f"fix: git -C {tree} rebase feature/0.5.0"]


@pytest.mark.parametrize(
    ("named", "verdict", "valid"),
    [(False, "APPROVED", True), (True, "REJECTED", True), (True, "APPROVED", False)],
    ids=["other-sha", "rejected", "invalid"],
)
def test_merge_needs_a_valid_approval_of_the_exact_head(
    root: Path, named: bool, verdict: str, valid: bool
) -> None:
    old = commit(root / TREE, "src/a.py")
    head = commit(root / TREE, "src/b.py")
    target = (
        approve(root, head, verdict=verdict, valid=valid)
        if named
        else (approve(root, old), "--all")[1]
    )
    result = run(root, "merge", TREE)
    assert result.returncode == 1 and head in result.stderr
    assert fixes(result) == [f"fix: {root / '.dadaia/.venv/bin/dadaia'} reports validate {target}"]
    assert git(root / "repos/r", "rev-parse", "feature/0.5.0").strip() != head


def test_failed_fast_forward_tells_a_stray_from_a_moved_work_branch(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    sha = commit(tree, "src/a.py")
    approve(root, sha)
    (repo / "src").mkdir()
    (repo / "src/a.py").write_text(
        "stray"
    )  # untracked in repos/r: the fast-forward would clobber it
    stray = run(root, "merge", TREE)
    assert "src/a.py" in stray.stderr and fixes(stray) == [
        f"fix: Operator action: commit or remove the paths above in {repo}"
    ]
    (repo / "src/a.py").unlink()
    cli = root / ".dadaia/.venv/bin/dadaia"  # a sibling lands while the verdict is read
    move = f"subprocess.run(['git', '-C', {str(repo)!r}, 'commit', '-qm', 'm', '--allow-empty'])"
    verdict = 'elif args[:2] == ["reports", "validate"]:\n'
    cli.write_text(cli.read_text().replace(verdict, f"{verdict}    import subprocess; {move}\n"))
    moved = run(root, "merge", TREE)
    assert fixes(moved) == [f"fix: python3 {SCRIPT} merge {tree}"] and tree.exists()


def test_parallel_siblings_union_ledgers_and_replay_task_markers(root: Path) -> None:
    """AC1.9 (ADR 0111): the worktree's TASKS marker flips replay onto the sibling-advanced work
    side, most advanced state winning; any worktree change beyond markers, or a missing side,
    refuses; JSONL ledgers merge by union."""
    repo, tree, tasks = root / "repos/r", root / TREE, "specs/releases/0.5.0/rc-1/TASKS.md"
    s = "**Status:** Approved\n"  # the trio stays Approved for the next `new`
    commit(repo, tasks, s + "- [ ] **T-1**\n- [ ] **T-2**\n- [ ] **T-3**\n")
    git(tree, "rebase", "-q", "feature/0.5.0")
    commit(tree, tasks, s + "- [x] **T-1**\n- [-] **T-2**\n- [ ] **T-3**\n")
    commit(repo, tasks, s + "- [ ] **T-1**\n- [x] **T-2**\n- [ ] **T-3** amended\n")
    run(root, "merge", TREE)  # rebased with the markers replayed; HEAD awaits its verdict
    approve(root, git(tree, "rev-parse", "HEAD").strip())
    assert run(root, "merge", TREE).returncode == 0
    assert (repo / tasks).read_text() == s + "- [x] **T-1**\n- [x] **T-2**\n- [ ] **T-3** amended\n"
    refused = [f"fix: git -C {tree} rebase feature/0.5.0"]
    assert run(root, "new", "r", "--kind", "impl").returncode == 0
    t2, t3 = "- [x] **T-2**\n", "- [ ] **T-3** amended\n"
    for mine, theirs in (  # the worktree adds a line; the work side rewrote the flipped one
        ("- [-] **T-1**\n" + t2 + t3 + "- [ ] **T-4**\n", "- [ ] **T-1**\n" + t2 + t3),
        ("- [-] **T-1**\n" + t2 + t3, "- [x] **T-1** moved\n" + t2 + t3),
    ):
        commit(tree, tasks, s + mine)
        commit(repo, tasks, s + theirs)
        assert fixes(run(root, "merge", TREE)) == refused
        git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    commit(tree, tasks, s + "- [x] **T-1**\n- [x] **T-2** amended\n")
    git(repo, "rm", "-q", tasks)
    git(repo, "commit", "-qm", "moved away")
    assert fixes(run(root, "merge", TREE)) == refused  # modify/delete: no side to replay onto
    git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    assert run(root, "clean", TREE).returncode == 0
    assert run(root, "new", "r", "--kind", "bug").returncode == 0
    bug, ledger = root / "worktrees/r/0.5.0a-bug", "specs/bugs/BUGS.jsonl"
    commit(repo, ledger, '{"id": "a"}\n')
    git(bug, "rebase", "-q", "feature/0.5.0")
    commit(bug, ledger, '{"id": "a"}\n{"id": "b"}\n')
    commit(repo, ledger, '{"id": "a"}\n{"id": "c"}\n')
    run(root, "merge", "worktrees/r/0.5.0a-bug")
    assert (bug / ledger).read_text() == '{"id": "a"}\n{"id": "c"}\n{"id": "b"}\n'


def test_merge_lists_ignored_files_and_keeps_them_by_its_fix(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    approve(root, commit(tree, "src/a.py"))
    (tree / "notes.scratch").write_text("keep me")
    (tree / "__pycache__").mkdir()
    (tree / "__pycache__/a.pyc").write_bytes(b"")
    git(repo, "checkout", "-q", "main")
    refused = run(root, "merge", TREE)
    assert "notes.scratch" in refused.stderr and "__pycache__" not in refused.stderr
    wrong_branch = run(root, "merge", TREE, "--keep", "notes.scratch")
    assert fixes(wrong_branch) == [f"fix: git -C {repo} switch feature/0.5.0"]
    _fix(root, wrong_branch)
    _fix(root, refused)
    assert (repo / "notes.scratch").read_text() == "keep me" and not tree.exists()


def test_clean_removes_only_an_empty_worktree_of_ours(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    commit(tree, "src/a.py")
    assert fixes(run(root, "clean", TREE)) == [f"fix: python3 {SCRIPT} merge {tree}"]
    git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    assert run(root, "clean", TREE).returncode == 0 and not tree.exists()
    # ours is the canonical wt/ branch, locked or not (T-050-99 N2); a tree on another is not
    git(repo, "worktree", "add", "-q", "-b", "side", str(root / "worktrees/r/0.5.0b-bug"))
    foreign = run(root, "clean", "worktrees/r/0.5.0b-bug")
    assert foreign.returncode == 1 and (root / "worktrees/r/0.5.0b-bug").exists()


def test_each_kind_allows_its_own_set_only() -> None:
    """ADRs 0106, 0124, 0148 (7), 0153: the allowed sets `merge` enforces, one row per kind boundary."""
    spec = importlib.util.spec_from_file_location("kinds", SCRIPT.parent / "_worktree_kinds.py")
    assert spec and spec.loader
    kinds = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kinds)
    rows = {
        ("impl", "src/a.py"): True,
        ("impl", "specs/releases/0.5.0/rc-5/TASKS.md"): True,
        ("impl", "specs/releases/0.5.0/TASKS.md"): False,
        ("impl", "specs/backlog/BACKLOG.json"): False,
        ("bug", "specs/bugs/BUGS.jsonl"): True,
        ("bug", "specs/bugs/_archive/bugs_histo.jsonl"): True,
        ("bug", "specs/releases/0.5.0/rc-5/SPEC.md"): False,
        ("backlog", "specs/backlog/_archive/backlog_histo.jsonl"): True,
        ("backlog", "src/a.py"): False,
        ("release", "specs/memory/ARCHITECTURE.md"): True,
        ("release", "specs/constitution.md"): True,
        ("release", "specs/bugs/AGENTS.md"): True,
        ("release", "specs/audits/x/FINDINGS.jsonl"): False,
    }
    assert {row: kinds.allows(*row) for row in rows} == rows


def test_release_closure_waits_for_every_other_wt(tmp_path: Path) -> None:
    """AC1.10 (F4): closure runs in its release worktree, whose own wt/* is spared; any
    other wt/* refuses it, naming repos/<r> and the owner's exit — `clean` for an empty
    tree (N1), which clears it."""
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "--kind", "release").returncode == 0
    specs = root / "worktrees/r/0.5.0a-release/specs"
    write_release_phase(specs, "0.5.0", "IMPLEMENTATION")
    (specs / "releases/_archive").mkdir()
    (specs / "releases/_archive/releases_histo.jsonl").write_text("")
    assert run(root, "new", "r", "--kind", "impl").returncode == 0  # empty
    for skill in ("dd-spec-navigator", "dd-gitflow-default", "dd-release-implementation"):
        stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")
    script = tmp_path / "skills/dd-release-implementation/scripts/release.py"
    closure = [sys.executable, str(script), "phase", "CLOSURE", "--sha", "beef123"]
    closure += ["--specs", str(specs)]

    refused = subprocess.run(closure, cwd=root, capture_output=True, text=True)
    fix = refused.stderr.rsplit("fix: ", 1)[1].strip()
    assert "repos/r " in refused.stderr and fix.endswith(f"clean {root}/worktrees/r/0.5.0b-impl")
    subprocess.run(fix.replace("python3", sys.executable, 1), shell=True, cwd=root, check=True)  # noqa: S602
    assert subprocess.run(closure, cwd=root, capture_output=True).returncode == 0
