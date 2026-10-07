"""AC1.8 (T-050-96, T-050-108); rc-9 AC1.2–AC1.5 (ADRs 0190, 0191): `worktree.py merge` lands a
job on the work branch after its APPROVED verdict naming its CI-matrix run and the job gate,
a `define` tree after its verdict and the ledger checks alone — HEAD as it is, by
fast-forward, then removes and `branch -d`s the tree, re-runnable; every refusal (dirty, a
moved work branch, no verdict, a red gate, ignored files, wrong branch, a stray blocking the
fast-forward) carries one `fix:` that clears it; `clean` removes only an empty `dadaia:`
worktree.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import suite_env
from tests.helpers.release_state import write_release_phase
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import (
    JOB,
    SCRIPT,
    TASK,
    approve,
    commit,
    fixes,
    git,
    land,
    make_workspace,
    run,
)
from tests.helpers.worktree_ws import run_fix as _fix

TREE = f"worktrees/r/{JOB}"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path := tmp_path / "my ws").mkdir()  # every fix runs as printed: quoted
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(tmp_path, "new", "r", JOB).returncode == 0
    return tmp_path


def _argv(result: subprocess.CompletedProcess[str]) -> list[str]:
    """The one fix line, split as the shell will: the expected argv is the oracle."""
    (fix,) = fixes(result)
    return shlex.split(fix.removeprefix("fix: "))


def test_merge_fast_forwards_removes_and_reruns(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    sha = land(root, "src/a.py")
    rejected = approve(
        root, sha, verdict="REJECTED", at="T09:00:00Z"
    )  # the newer APPROVED overrules
    (other := root / ".dadaia/handoff/z").mkdir()  # another context and a non-UTC name:
    rejected.rename(other / "a.handoff.json")  # produced_at orders, never the path
    approve(root, sha)
    result = run(root, "merge", TREE)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == sha  # HEAD as approved
    assert not tree.exists() and not git(repo, "branch", "--list", "wt/*").strip()
    assert run(root, "merge", TREE).returncode == 0  # a finished merge re-runs clean
    assert run(root, "new", "r", JOB).returncode == 0
    shutil.rmtree(tree)  # the dadaia:-locked tree deleted by hand: an orphan, its exit clears it
    (row,) = json.loads(run(root, "list", "--json").stdout)
    assert (row["state"], row["path"]) == ("orphan", str(tree))
    assert run(root, *shlex.split(row["exit"])[2:]).returncode == 0
    assert json.loads(run(root, "list", "--json").stdout) == []
    git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0-rc1/j1", str(tree))
    commit(tree, "src/b.py")
    git(repo, "worktree", "remove", str(tree))  # interrupted: tree gone, its commit unmerged
    assert _argv(run(root, "merge", TREE)) == [
        *("git", "-C", str(repo), "worktree", "add", str(tree), "wt/0.5.0-rc1/j1")
    ]
    assert git(repo, "branch", "--list", "wt/0.5.0-rc1/j1").strip()  # never -D


def test_a_dirty_tree_refuses_with_one_fix_that_commits_or_removes(root: Path) -> None:
    tree = root / TREE
    (tree / "wip").mkdir()  # an untracked directory, and a tracked edit staged:
    (tree / "wip/x.py").write_text("")
    (tree / "specs/releases/0.5.0/rc-1/SPEC.md").write_text("dirty")
    git(tree, "add", "specs/releases/0.5.0/rc-1/SPEC.md")
    dirty = run(root, "merge", TREE)
    assert "uncommitted" in dirty.stderr
    add, then, *remove = fixes(dirty)[0].split("`")[1::2]  # Operator action: commit or remove
    assert [shlex.split(add), shlex.split(then)] == [  # the commit takes its own message
        ["git", "-C", str(tree), "add", "-A"],
        ["git", "-C", str(tree), "commit"],
    ]
    for step in remove:
        subprocess.run(step, shell=True, check=True, capture_output=True)  # noqa: S602
    assert git(tree, "status", "--porcelain") == ""  # removed, clean,
    assert not (tree / "wip").exists()
    assert git(tree, "stash", "list") == ""  # never in the stack every worktree shares


def test_a_define_tree_lands_specs_only_through_the_ledger_checks(root: Path) -> None:
    """AC1.2 (ADR 0190): a `define` merge runs the ledger, trio and release checks alone — an
    invalid ledger refuses, a valid one lands with no test run; code refuses with its undo."""
    repo, tree = root / "repos/r", root / "worktrees/r/0.5.0-rc1/define"
    assert run(root, "new", "r", "0.5.0-rc1/define").returncode == 0
    commit(tree, "specs/bugs/BUGS.jsonl", '{"id": "half"}\n')
    approve(root, git(tree, "rev-parse", "HEAD").strip(), ci_run=False)
    invalid = run(root, "merge", str(tree))
    assert invalid.returncode == 1 and "bugs.py check failed" in invalid.stderr
    git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    commit(tree, "RED-job", "")  # a file the job gate would fail on: never run here
    code = run(root, "merge", str(tree))
    assert "RED-job is code" in code.stderr
    restore, then = fixes(code)[0].split("`")[1::2]  # Operator action: restore, commit
    subprocess.run(restore, shell=True, check=True)  # noqa: S602 — runs as printed
    assert shlex.split(then) == ["git", "-C", str(tree), "commit"]
    git(tree, "commit", "-qm", "revert: RED-job")
    approve(root, sha := commit(tree, "specs/releases/0.5.0/rc-1/PLAN.md", "**Status:** Draft\n"),
            ci_run=False)  # fmt: skip
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == sha
    assert "ci " not in landed.stdout and not tree.exists()


def test_work_branch_refusals_fix_runs_verbatim(tmp_path: Path) -> None:
    (ws := tmp_path / "my ws").mkdir()
    make_workspace(ws)
    repo = ws / "repos/r"
    git(repo, "branch", "feature/0.4.9", "feature/0.5.0")  # two work branches: the older goes
    _fix(ws, two := run(ws, "new", "r", JOB))
    assert "2 work branches" in two.stderr
    assert not git(repo, "branch", "--list", "feature/0.4.9").strip()
    git(repo, "branch", "-m", "feature/0.5.0", "dev")  # none: the fix cuts one from dev
    _fix(ws, none := run(ws, "new", "r", JOB))
    assert "no work branch" in none.stderr
    assert git(repo, "branch", "--list", "feature/*").strip()


@pytest.mark.parametrize(
    ("named", "verdict", "valid", "older", "at"),
    [
        (False, "APPROVED", True, None, "T10:00:00Z"),
        (True, "REJECTED", True, None, "T10:00:00Z"),
        (True, "APPROVED", False, "APPROVED", "T10:00:00Z"),
        (True, "REJECTED", True, "APPROVED", "T10:00:00Z"),
        (True, "APPROVED", True, "APPROVED", "Tx"),
        (True, "REJECTED", True, "APPROVED", "T11:00:00"),  # 02:00Z if read in Asia/Tokyo
        (True, "REJECTED", True, "APPROVED", "T09:00:00Z"),  # tied with the older APPROVED
    ],
    ids=[
        *("outside-reflog", "rejected", "invalid", "rejected-after-approved"),
        *("no-produced-at", "naive-produced-at", "tied-produced-at"),
    ],
)
def test_merge_needs_a_valid_approval_of_the_exact_head(
    root: Path, named: bool, verdict: str, valid: bool, older: str | None, at: str
) -> None:
    land(root, "src/a.py")
    head = land(root, "src/b.py")
    copy = subprocess.run(  # head's tree, parent and message, outside wt/<name>'s reflog
        ["git", "-C", str(root / TREE), "commit-tree", f"{head}^{{tree}}", "-p", f"{head}~"],
        input="src/b.py\n",
        env=suite_env(os.environ, Path.home()) | {"GIT_COMMITTER_DATE": "2001-01-01T00:00:00"},
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if older:  # the newest produced_at decides (ADR 0110), never a name sorting last
        approve(root, head, verdict=older, at="T09:00:00Z").rename(
            root / ".dadaia/handoff/c/v.handoff.json"
        )
    target = (
        approve(root, head, verdict=verdict, valid=valid, at=at)
        if named
        else (approve(root, copy), "--all")[1]
    )
    commit(root / "repos/r", "src/z.py")  # moved: only an identical series in the reflog counts
    git(root / TREE, "rebase", "-q", "feature/0.5.0")
    result = run(root, "merge", TREE)
    head = git(root / TREE, "rev-parse", "HEAD").strip()
    assert result.returncode == 1 and head in result.stderr
    cli = str(root / ".dadaia/.venv/bin/dadaia")
    assert _argv(result) == [cli, "reports", "validate", str(target)]
    assert git(root / "repos/r", "rev-parse", "feature/0.5.0").strip() != head


def test_failed_fast_forward_tells_a_stray_from_a_moved_work_branch(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    sha = land(root, "src/a.py")
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
    assert _argv(moved) == ["git", "-C", str(tree), "rebase", "feature/0.5.0"] and tree.exists()


def test_merge_lists_ignored_files_and_keeps_them_by_its_fix(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    approve(root, land(root, "src/a.py"))
    (tree / "my notes.scratch").write_text("keep me")
    (tree / "__pycache__").mkdir()
    (tree / "__pycache__/a.pyc").write_bytes(b"")
    git(repo, "checkout", "-q", "main")
    refused = run(root, "merge", TREE)
    assert "my notes.scratch" in refused.stderr and "__pycache__" not in refused.stderr
    wrong_branch = run(root, "merge", TREE, "--keep", "my notes.scratch")
    assert _argv(wrong_branch) == ["git", "-C", str(repo), "switch", "feature/0.5.0"]
    _fix(root, wrong_branch)
    _fix(root, refused)
    assert (repo / "my notes.scratch").read_text() == "keep me" and not tree.exists()


def test_clean_removes_only_an_empty_worktree_of_ours(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    commit(tree, "src/a.py")
    assert _argv(run(root, "clean", TREE)) == [sys.executable, str(SCRIPT), "merge", str(tree)]
    git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    assert run(root, "clean", TREE).returncode == 0 and not tree.exists()
    # ours is the canonical wt/ branch, locked or not (T-050-99 N2); a tree on another is not
    git(repo, "worktree", "add", "-q", "-b", "side", str(root / "worktrees/r/0.5.0-rc1/j2"))
    foreign = run(root, "clean", "worktrees/r/0.5.0-rc1/j2")
    assert foreign.returncode == 1 and (root / "worktrees/r/0.5.0-rc1/j2").exists()


@pytest.mark.windows
@pytest.mark.quarantine(bug="worktree-script-run-fails-winerror-193-on-windows")
def test_release_closure_waits_for_every_other_wt(tmp_path: Path) -> None:
    """AC1.10 (F4); rc-9 AC1.5: closure runs in the Reconciliation job's tree, whose own wt/* is
    spared; any other wt/* refuses it, naming repos/<r> and the owner's exit — `clean` for an
    empty tree (N1), which clears it."""
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "0.5.0-rc1/reconcile").returncode == 0
    specs = root / "worktrees/r/0.5.0-rc1/reconcile/specs"
    write_release_phase(specs, "0.5.0", "IMPLEMENTATION")
    (specs / "releases/_archive").mkdir()
    (specs / "releases/_archive/releases_histo.jsonl").write_text("")
    assert run(root, "new", "r", JOB).returncode == 0  # empty
    for skill in (
        "dd-spec-navigator",
        "dd-gitflow-default",
        "dd-release-implementation",
        "dd-bug-resolution",
    ):
        stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")
    script = tmp_path / "skills/dd-release-implementation/scripts/release.py"
    closure = [sys.executable, str(script), "phase", "CLOSURE", "--sha", "beef123"]
    closure += ["--specs", str(specs)]

    refused = subprocess.run(closure, cwd=root, capture_output=True, text=True)
    fix = refused.stderr.rsplit("fix: ", 1)[1].strip()
    assert "repos/r " in refused.stderr and fix.endswith(f"clean {root}/{TREE}")
    subprocess.run(fix, shell=True, cwd=root, check=True)  # noqa: S602
    assert subprocess.run(closure, cwd=root, capture_output=True).returncode == 0


def test_a_verdict_carries_over_only_an_identical_patch_and_message_series(root: Path) -> None:
    """AC3.19 (ADR 0168): once the work branch moved, a reword, a dropped or added empty
    commit, a reorder, code amended under the same message (a colored config included), a gitlink
    amended under the same message (diff.ignoreSubmodules=all), or a hand-resolved conflict each change the approved series and refuse for review."""
    repo, tree = root / "repos/r", root / TREE
    land(root, "src/a.py")
    git(tree, "commit", "-q", "--allow-empty", "-m", "empty")
    approve(root, approved := git(tree, "rev-parse", "HEAD").strip())
    commit(repo, "src/z.py")
    git(repo, "config", "color.ui", "always")
    refusal = [str(root / ".dadaia/.venv/bin/dadaia"), "reports", "validate", "--all"]
    work = git(repo, "rev-parse", "feature/0.5.0")
    for change in (
        [("rm", "-q", "src/a.py"), ("commit", "-q", "--amend", "-C", "HEAD")],  # same message
        [("commit", "-q", "--amend", "--allow-empty", "-m", "reworded")],  # same patch-ids
        [("reset", "-q", "--hard", "HEAD~")],  # the empty commit dropped
        [("commit", "-q", "--allow-empty", "-m", "empty 2")],  # one more empty commit
        [  # the same two commits, reordered
            ("reset", "-q", "--hard", "HEAD~2"),
            ("cherry-pick", "--allow-empty", approved, f"{approved}~"),
        ],
    ):
        git(tree, "reset", "-q", "--hard", approved)
        for step in change:
            git(tree, *step)
        git(tree, "rebase", "-q", "feature/0.5.0")
        assert _argv(run(root, "merge", TREE)) == refusal, change
        assert git(repo, "rev-parse", "feature/0.5.0") == work
    git(repo, "config", "diff.ignoreSubmodules", "all")  # a gitlink change shows no diff
    git(tree, "reset", "-q", "--hard", approved)
    for sha in (approved, f"{approved}~"):  # the same message, another gitlink: fail closed
        git(
            tree,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{git(tree, 'rev-parse', sha).strip()},sub",
        )
        git(
            tree, "commit", "-q", *(("--amend", "-C", "HEAD") if sha != approved else ("-m", "sub"))
        )
        if sha == approved:
            approve(root, git(tree, "rev-parse", "HEAD").strip())
    git(tree, "rebase", "-q", "feature/0.5.0")
    assert _argv(run(root, "merge", TREE)) == refusal
    assert git(repo, "rev-parse", "feature/0.5.0") == work
    git(tree, "reset", "-q", "--hard", approved)
    work = commit(repo, "src/a.py", "theirs\n") + "\n"
    assert run(root, "merge", TREE).returncode == 1  # moved; the agent's rebase conflicts
    subprocess.run(["git", "-C", str(tree), "rebase", "feature/0.5.0"], capture_output=True)
    (tree / "src/a.py").write_text("resolved\n")
    git(tree, "add", "src/a.py")
    git(tree, "-c", "core.editor=true", "rebase", "--continue")
    assert _argv(run(root, "merge", TREE)) == refusal
    assert git(repo, "rev-parse", "feature/0.5.0") == work


@pytest.mark.parametrize("change", ["same-patch", "new-patch"])
def test_a_moved_work_branch_refuses_and_its_fix_rebase_keeps_only_an_identical_patch(
    root: Path, change: str
) -> None:
    """AC12.7 (ADR 0185): a moved work branch refuses with the rebase fix line, both branches
    unchanged; after it, a patch-identical rebase lands under the old verdict (ADR 0168),
    a changed patch refuses for review."""
    repo, tree = root / "repos/r", root / TREE
    approve(root, mine := land(root, "src/a.py"))
    work = commit(repo, "src/z.py")
    moved = run(root, "merge", TREE)
    assert _argv(moved) == ["git", "-C", str(tree), "rebase", "feature/0.5.0"]
    assert [
        git(repo, "rev-parse", "feature/0.5.0").strip(),
        git(tree, "rev-parse", "HEAD").strip(),
    ] == [work, mine]
    _fix(root, moved)
    if change == "new-patch":
        (tree / "src/a.py").write_text("x = 2\n")
        git(tree, "commit", "-q", "--amend", "-C", "HEAD", "-a")
    result = run(root, "merge", TREE)
    landed = git(repo, "rev-parse", "feature/0.5.0").strip()
    if change == "same-patch":
        assert result.returncode == 0, result.stderr
        assert git(repo, "rev-parse", "feature/0.5.0~").strip() == work != landed
    else:
        assert _argv(result)[1:] == ["reports", "validate", "--all"] and landed == work


@pytest.mark.parametrize("red", [True, False], ids=["red-gate", "green-gate"])
def test_the_job_gate_runs_scripts_ci_job_as_argv_on_the_head_it_lands(
    root: Path, red: bool
) -> None:
    """AC1.2 (ADRs 0190, 0207): a job merge runs the work branch's `verify:` on HEAD, one argv list with
    stdin closed, its output on stdout; a red gate lands nothing."""
    repo, tree = root / "repos/r", root / TREE
    head = land(root, "RED-job" if red else "src/a.py", "")
    approve(root, head)
    work = git(repo, "rev-parse", "feature/0.5.0").strip()
    result = run(root, "merge", TREE, input="stdin leak\n")
    assert "ci job" in result.stdout.splitlines() and "stdin leak" not in result.stdout
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == (work if red else head)
    assert (result.returncode, tree.exists()) == ((1, True) if red else (0, False))
    if red:
        act, line, where = fixes(result)[0].split("`")
        assert act == "fix: Operator action: make "
        assert shlex.split(line) == [
            "python",
            "scripts/ci.py",
            "job",
        ]
        assert where == f" exit 0 in {tree} and commit the fix in this worktree"


def test_a_job_merge_needs_a_verdict_naming_its_ci_matrix_run(root: Path) -> None:
    """AC1.2, AC1.4: no verdict refuses; an APPROVED naming no CI-matrix run refuses with the
    operator's act; one naming the run lands."""
    repo = root / "repos/r"
    head = land(root, "src/a.py")
    assert _argv(run(root, "merge", TREE))[1:] == ["reports", "validate", "--all"]
    approve(root, head, ci_run=False)
    unrun = run(root, "merge", TREE)
    assert fixes(unrun) == [
        "fix: Operator action: push wt/0.5.0-rc1/j1, wait for its CI run to pass, and have "
        "dd-code-reviewer's verdict carry that run's URL as ci_run"
    ]
    approve(root, head, at="T11:00:00Z")
    assert run(root, "merge", TREE).returncode == 0
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == head


def test_one_job_lands_code_an_atom_and_its_derived_section_together(root: Path) -> None:
    """AC1.3, AC1.5 (ADRs 0191, 0192): no allowed set splits one change — code, an atom and its
    derived section land in one job merge."""
    repo = root / "repos/r"
    land(root, "src/a.py")
    land(root, "specs/memory/product/x/atom.md", "# atom\n")
    approve(root, land(root, "README.md", "## A\n<!-- derived-from: atom sha256:0 -->\n"))
    assert run(root, "merge", TREE).returncode == 0
    landed = git(repo, "diff", "--name-only", "HEAD~3", "HEAD").split()
    assert landed == ["README.md", "specs/memory/product/x/atom.md", "src/a.py"]


def test_a_declared_verify_line_runs_as_argv_never_through_a_shell(root: Path) -> None:
    """AC1.2: the `verify:` line is split by shlex and run as argv: `;` and `$(...)` are words."""
    line = "verify: python scripts/ci.py job ; touch PWNED $(touch PWNED2)\n"
    commit(root / "repos/r", "AGENTS.md", line + "verify-task: python scripts/ci.py task\n")
    git(root / TREE, "merge", "-q", "--ff-only", "feature/0.5.0")
    head = land(root, "src/a.py")
    approve(root, head)
    result = run(root, "merge", TREE)
    assert result.returncode == 0, result.stderr
    assert "ci job ; touch PWNED $(touch PWNED2)" in result.stdout.splitlines()
    assert not list(root.rglob("PWNED*"))


def test_a_task_lands_on_its_job_branch_after_the_task_gate_with_no_verdict(root: Path) -> None:
    """AC1.1, AC1.4: a red task gate lands nothing; a green one fast-forwards the job branch
    in the job's tree, unreviewed; a stage with an open task cannot close, nor a job land."""
    job, task = root / TREE, root / "worktrees/r" / TASK
    assert run(root, "new", "r", TASK).returncode == 0
    held = run(root, "stage", TREE)
    assert held.returncode == 1 and _argv(held)[-2:] == ["merge", str(task)]
    assert _argv(run(root, "merge", TREE))[-2:] == ["merge", str(task)]
    red = commit(task, "RED-task", "")
    refused = run(root, "merge", str(task))
    assert refused.returncode == 1 and "ci task RED-task" in refused.stdout.splitlines()
    assert git(job, "rev-parse", "HEAD").strip() != red
    git(task, "rm", "-q", "RED-task")
    git(task, "commit", "-qm", "green")
    commit(task, "src/a.py")
    git(task, "commit", "-q", "--amend", "--no-edit", "--trailer", "Owner-tests: tests/test_r.py")
    sha = git(task, "rev-parse", "HEAD").strip()
    landed = run(root, "merge", str(task))
    assert landed.returncode == 0, landed.stderr
    assert git(job, "rev-parse", "HEAD").strip() == sha and not task.exists()
    assert not git(root / "repos/r", "branch", "--list", "wt/0.5.0-rc1/j1--J1.S1.T1").strip()
    staged = run(root, "stage", TREE)
    assert (staged.returncode, staged.stdout.splitlines()) == (
        0, ["ci stage", f"[ok] stage gate green on wt/0.5.0-rc1/j1@{sha}"]
    )  # fmt: skip


def _task_commit(root: Path, *trailers: str, rm: str = "", add: str = "src/b.py") -> Path:
    """Open `TASK`, delete *rm*, write *add*, commit with *trailers*; return the task tree."""
    task = root / "worktrees/r" / TASK
    assert run(root, "new", "r", TASK).returncode == 0
    if rm:
        git(task, "rm", "-q", rm)
    (task / add).parent.mkdir(parents=True, exist_ok=True)
    (task / add).write_text("y = 1\n")
    git(task, "add", add)
    git(task, "commit", "-qm", "J1.S1.T1 work", *(a for t in trailers for a in ("--trailer", t)))
    return task


def test_the_task_gate_skips_deleted_files_and_appends_owner_tests(root: Path) -> None:
    """J1.S3.T14: a deleted path never reaches `verify-task:`; `Owner-tests:` trailer paths do."""
    land(root, "src/a.py")
    land(root, "tests/test_a.py", "")
    _task_commit(root, "Owner-tests: tests/test_a.py src/b.py", rm="src/a.py")
    landed = run(root, "merge", f"worktrees/r/{TASK}")
    assert landed.returncode == 0, landed.stderr
    assert "ci task src/b.py tests/test_a.py" in landed.stdout.splitlines()


def test_a_missing_owner_test_refuses_with_one_fix_line(root: Path) -> None:
    """J1.S3.T14: an `Owner-tests:` path absent from the tree refuses, one fix line."""
    _task_commit(root, "Owner-tests: tests/test_gone.py")
    refused = run(root, "merge", f"worktrees/r/{TASK}")
    assert refused.returncode == 1 and "tests/test_gone.py" in refused.stderr
    lines = refused.stderr.splitlines()
    assert len([ln for ln in lines if ln.startswith(("fix: ", "Operator action: "))]) == 1


def test_a_task_cannot_rewrite_its_own_gate(root: Path) -> None:
    """J1.S3.T14 (ADR 0207): the task gate runs the work branch's `verify-task:`, not the task's."""
    line = "verify: python scripts/ci.py job\nverify-task: python scripts/ci.py stage\n"
    _task_commit(root, add="AGENTS.md")
    task = root / "worktrees/r" / TASK
    (task / "AGENTS.md").write_text(line)
    git(task, "commit", "-qam", "J1.S1.T1 gate")
    landed = run(root, "merge", f"worktrees/r/{TASK}")
    assert landed.returncode == 0, landed.stderr
    assert "ci task AGENTS.md" in landed.stdout.splitlines()


@pytest.mark.parametrize(
    ("add", "trailers", "code"),
    [("src/b.py", (), 1), ("tests/test_b.py", (), 0), ("docs/b.md", (), 0),
     ("src/b.py", ("Owner-tests: src/b.py",), 1),
     ("src/b.py", ("Owner-tests: tests/test_r.py",), 0)],
)  # fmt: skip
def test_a_code_task_without_owner_tests_refuses_with_one_fix_line(
    root: Path, add: str, trailers: tuple[str, ...], code: int
) -> None:
    """LOW 2: a task touching non-test `.py` with no `Owner-tests:` trailer runs no tests."""
    task = _task_commit(root, *trailers, add=add)
    result = run(root, "merge", f"worktrees/r/{TASK}")
    assert result.returncode == code, result.stderr
    if code:
        assert fixes(result) == [
            f"fix: Operator action: name the task's owner tests in an Owner-tests: trailer on its commits in {task}"
        ]


def test_a_code_task_whose_touched_test_feeds_its_gate_lands(root: Path) -> None:
    """LOW 4: a touched `test_` file is in the gate's argv, so no trailer is needed."""
    commit(_task_commit(root, add="tests/test_b.py"), "src/b.py")
    landed = run(root, "merge", f"worktrees/r/{TASK}")
    assert landed.returncode == 0, landed.stderr
    assert "ci task src/b.py tests/test_b.py" in landed.stdout.splitlines()


def test_the_stage_gate_runs_the_work_branch_verify_stage_line(root: Path) -> None:
    """LOW 3: a task that rewrote `verify-stage:` on the job branch does not choose its gate."""
    line = "verify: python scripts/ci.py job\nverify-stage: python scripts/ci.py task\n"
    land(root, "AGENTS.md", line)
    staged = run(root, "stage", TREE)
    assert staged.returncode == 0, staged.stderr
    assert staged.stdout.splitlines()[0] == "ci stage"


def test_a_stray_job_branch_commit_refuses(root: Path) -> None:
    """AC1.3: a job branch takes code only through a task merge; specs edits land directly."""
    tree = root / TREE
    commit(tree, "specs/releases/0.5.0/rc-1/PLAN.md", "**Status:** Approved\n")
    approve(root, stray := commit(tree, "src/stray.py"))
    refused = run(root, "merge", TREE)
    assert refused.returncode == 1 and stray in refused.stderr
    git(tree, "reset", "-q", "--hard", "HEAD~")
    approve(root, git(tree, "rev-parse", "HEAD").strip(), at="T11:00:00Z")
    assert run(root, "merge", TREE).returncode == 0


@pytest.mark.parametrize(
    ("declared", "act"),
    [("", "add this repo's task gate as a verify-task: line to"),
     ("FOO=1 python scripts/ci.py task", "make the verify-task: line of"),
     ("python 'scripts/ci.py task", "make the verify-task: line of")],
    ids=["absent", "env-assignment", "unbalanced-quote"],
)  # fmt: skip
def test_a_task_gate_line_absent_or_unstartable_refuses_with_a_fix_that_clears_it(
    root: Path, declared: str, act: str
) -> None:
    """Bug verify-line-absent-refusal-sends-to-a-tree-the-gate-never-reads: the task gate
    reads the work branch's `verify-task:`; an absent or unstartable line refuses with one
    operator act on that tracked line, never a traceback, and doing that act lands the task."""
    repo, agents = root / "repos/r", root / "repos/r/AGENTS.md"
    line = f"verify-task: {declared}\n" if declared else ""
    commit(repo, "AGENTS.md", "verify: python scripts/ci.py job\n" + line)
    task = _task_commit(root, "Owner-tests: tests/test_r.py")
    refused = run(root, "merge", str(task))
    assert refused.returncode == 1 and "Traceback" not in refused.stderr
    tail = (" and commit it on feature/0.5.0" if not declared else
            " on feature/0.5.0 one argv list that starts: it runs without a shell"
            " — no VAR=value prefix, no sh -c")  # fmt: skip
    assert fixes(refused) == [f"fix: Operator action: {act} {agents}{tail}"]
    commit(repo, "AGENTS.md", "verify-task: python scripts/ci.py task\n")
    landed = run(root, "merge", str(task))
    assert landed.returncode == 0, landed.stderr


@pytest.mark.parametrize(
    ("declared", "act"),
    [("", "add this repo's job gate as a verify: line to"),
     ("FOO=1 python scripts/ci.py job", "make the verify: line of")],
    ids=["absent", "env-assignment"],
)  # fmt: skip
def test_a_job_gate_reads_the_work_branch_verify_line_not_its_own(
    root: Path, declared: str, act: str
) -> None:
    """ADR 0207: a job whose task rewrote `verify:` is still judged by the work branch's
    line; its absent or unstartable refusal names the work branch, and doing that act lands."""
    repo, tree, agents = root / "repos/r", root / TREE, root / "repos/r/AGENTS.md"
    good = agents.read_text()
    rest = "".join(ln for ln in good.splitlines(keepends=True) if not ln.startswith("verify:"))
    commit(repo, "AGENTS.md", (f"verify: {declared}\n" if declared else "") + rest)
    git(tree, "merge", "-q", "--ff-only", "feature/0.5.0")
    land(root, "AGENTS.md", good)  # the job's own line never judges it
    approve(root, land(root, "src/a.py"))
    refused = run(root, "merge", TREE)
    assert refused.returncode == 1 and "Traceback" not in refused.stderr
    tail = (" and commit it on feature/0.5.0" if not declared else
            " on feature/0.5.0 one argv list that starts: it runs without a shell"
            " — no VAR=value prefix, no sh -c")  # fmt: skip
    assert fixes(refused) == [f"fix: Operator action: {act} {agents}{tail}"]
    commit(repo, "AGENTS.md", good)
    git(tree, "rebase", "-q", "feature/0.5.0")
    approve(root, git(tree, "rev-parse", "HEAD").strip(), at="T11:00:00Z")
    landed = run(root, "merge", TREE)
    assert landed.returncode == 0, landed.stderr
