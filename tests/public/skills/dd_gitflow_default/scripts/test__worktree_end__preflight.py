"""`worktree.py preflight <tree>` is `merge` without the verdict — it runs
every check `merge` runs for the tree's kind, collects each refusal and prints
`PREFLIGHT PASS|FAIL <tree> <sha>`, each failing check with its message and its one `fix:` line.
Size: MEDIUM (real git, tmp workspace, a stub CLI).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import git_line, shell_line
from tests.helpers.worktree_ws import (
    NEW_JOB,
    NEW_TASK,
    SCRIPT,
    approve,
    commit,
    fixes,
    git,
    make_workspace,
    open_tree,
    run,
)

BRANCH = "feature/0.5.0"
RC = "0.5.0/rc-1/wt-rc"
JOB_BRANCH = f"wt/{NEW_JOB}"
JOB2 = "0.5.0/rc-1/job-2/wt-main"
BACKLOG = "0.5.0/wt-backlog-x"
HOTFIX = "0.5.0/wt-hotfix-a-block-bug"
RECONCILE = "0.5.0/rc-1/reconcile"
RED_VERIFY = "make `python scripts/ci.py job` exit 0 in {tree} and commit the fix in this worktree"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path := tmp_path / "ws").mkdir()
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", BRANCH)
    assert open_tree(tmp_path, RC).is_dir()
    return tmp_path


def _head(tree: Path) -> str:
    return git(tree, "rev-parse", "HEAD").strip()


def _lines(done: subprocess.CompletedProcess[str]) -> list[str]:
    """The verdict line, each failing check's `[error]` line and each `fix:` line, in print order."""
    return [
        ln
        for ln in (done.stdout + done.stderr).splitlines()
        if ln.startswith(("PREFLIGHT ", "[error] ", "fix: "))
    ]


def _report(root: Path, tree: Path) -> list[str]:
    return _lines(run(root, "preflight", str(tree)))


def _fail(root: Path, tree: Path, error: str, fix: str) -> None:
    """The preflight failed with the one check *error* and its one *fix* line, exit 1, no write."""
    before = git(tree, "status", "--porcelain")
    done = run(root, "preflight", str(tree))
    assert done.returncode == 1, done.stderr
    assert _report(root, tree) == [f"PREFLIGHT FAIL {tree} {_head(tree)}", f"[error] {error}", f"fix: {fix}"]  # fmt: skip
    assert git(tree, "status", "--porcelain") == before


def _pass(root: Path, tree: Path) -> None:
    done = run(root, "preflight", str(tree))
    assert done.returncode == 0, done.stderr
    assert _report(root, tree) == [f"PREFLIGHT PASS {tree} {_head(tree)}"]


def test_a_task_passes_clean_and_rebased_and_fails_behind_its_job_branch(root: Path) -> None:
    job = open_tree(root, NEW_JOB)
    task = open_tree(root, NEW_TASK)
    commit(task, "src/a.py")
    _pass(root, task)
    commit(job, "src/b.py")
    _fail(
        root,
        task,
        f"{JOB_BRANCH} moved past this branch's base",
        git_line(task, "rebase", JOB_BRANCH),
    )


def test_a_job_passes_and_fails_with_an_open_task_and_with_a_red_verify(root: Path) -> None:
    job = open_tree(root, NEW_JOB)
    commit(job, "src/a.py")
    _pass(root, job)
    task = open_tree(root, NEW_TASK)
    head, error, fix = _report(root, job)
    assert head == f"PREFLIGHT FAIL {job} {_head(job)}"
    assert error == f"[error] task worktree {task} of {JOB_BRANCH} is open"
    assert fix.endswith(f" merge {task}")
    assert run(root, "clean", str(task)).returncode == 0
    commit(job, "RED-job", "")
    _fail(root, job, "verify: exited 1", f"Agent action: {RED_VERIFY.format(tree=job)}")


def test_a_backlog_tree_passes_without_a_verify_run_and_fails_a_red_ledger_check(
    root: Path,
) -> None:
    backlog = open_tree(root, BACKLOG)
    commit(backlog, "specs/notes", "")
    commit(backlog, "specs/RED-job", "")  # the job gate would fail on it: a backlog tree runs none
    done = run(root, "preflight", str(backlog))
    assert done.returncode == 0 and "ci job" not in done.stdout + done.stderr, done.stderr
    assert _report(root, backlog) == [f"PREFLIGHT PASS {backlog} {_head(backlog)}"]
    commit(backlog, "specs/bugs/BUGS.jsonl", '{"id": "half"}\n')
    ledger = backlog / "specs/bugs/BUGS.jsonl"
    fix = (
        f"Agent action: line 1 of {ledger} was not written by `bugs.py append` or "
        "`bugs.py update` (specs/bugs/AGENTS.md: never hand-edit BUGS.jsonl) — "
        "revert the commit that introduced it "
        f"(`{git_line(ledger.parent, 'log', '-L', f'1,1:{ledger.name}')}` finds it), or delete the line "
        "if you wrote it and it is still uncommitted, then redo the change through "
        "`bugs.py append` or `bugs.py update`"
    )
    _fail(root, backlog, f"bugs.py check failed on {backlog / 'specs'}", fix)


def test_a_backlog_tree_fails_a_path_outside_specs(root: Path) -> None:
    tree = open_tree(root, BACKLOG)
    commit(tree, "src/a.py")
    _fail(
        root,
        tree,
        "src/a.py is code; a define or backlog tree lands specs/ only — code lands through a job",
        f"Agent action: revert src/a.py to {BRANCH} in one commit — "
        f"`{git_line(tree, 'restore', '-s', BRANCH, '-SW', '--', 'src/a.py')}` and `{git_line(tree, 'commit')}`",
    )


def test_a_reconcile_tree_fails_a_red_verify_as_a_job_tree_does(root: Path) -> None:
    tree = (
        root / "worktrees/r" / RECONCILE
    )  # no such kind now: a raw tree, the refusal is what runs
    git(root / "repos/r", "worktree", "add", "-q", "-b", f"wt/{RECONCILE}", str(tree), BRANCH)
    commit(tree, "RED-job", "")
    _fail(root, tree, "verify: exited 1", f"Agent action: {RED_VERIFY.format(tree=tree)}")


def test_a_plain_name_is_refused_as_not_a_worktree_name_with_the_list_fix(root: Path) -> None:
    refused = run(root, "new", "r", "fix-a")
    assert refused.returncode == 1
    assert "[error] not a worktree name" in refused.stderr
    assert fixes(refused) == [f"fix: {shell_line(sys.executable, str(SCRIPT))} list"]
    assert not (root / "worktrees/r/fix-a").exists()


def test_a_hotfix_tree_fails_a_red_verify(root: Path) -> None:
    repo = root / "repos/r"
    commit(repo, "specs/bugs/BUGS.jsonl", '{"id": "a-block-bug", "status": "open"}\n')
    tree = open_tree(root, HOTFIX)
    commit(tree, "RED-job", "")
    _fail(root, tree, "verify: exited 1", f"Agent action: {RED_VERIFY.format(tree=tree)}")


def test_merge_on_a_passing_tree_without_a_verdict_refuses_only_with_the_verdict_message(
    root: Path,
) -> None:
    job = open_tree(root, NEW_JOB)
    head = commit(job, "src/a.py")
    _pass(root, job)
    refused = run(root, "merge", str(job))
    assert refused.returncode == 1
    errors = [ln for ln in refused.stderr.splitlines() if ln.startswith("[error] ")]
    assert len(errors) == 1 and errors[0].startswith(f"[error] the newest dd-code-reviewer handoff naming HEAD {head}")  # fmt: skip
    assert len(fixes(refused)) == 1
    approve(root, head, name=NEW_JOB)
    assert run(root, "merge", str(job)).returncode == 0


def _kind(root: Path, kind: str) -> tuple[Path, Path]:
    """A committed, approved tree of *kind* and the checkout its merge lands in."""
    repo, rc = root / "repos/r", root / "worktrees/r" / RC
    if kind == "task":
        job = open_tree(root, NEW_JOB)
        tree = open_tree(root, NEW_TASK)
        commit(tree, "src/a.py")
        return tree, job
    if kind == "hotfix":
        commit(repo, "specs/bugs/BUGS.jsonl", '{"id": "a-block-bug", "status": "open"}\n')
    names = {"job": NEW_JOB, "job-b": JOB2, "rc": RC, "backlog": BACKLOG, "hotfix": HOTFIX}
    if kind == "reconcile":
        tree = root / "worktrees/r" / RECONCILE
        git(repo, "worktree", "add", "-q", "-b", f"wt/{RECONCILE}", str(tree), BRANCH)
    else:
        tree = rc if kind == "rc" else open_tree(root, names[kind])
    sha = commit(tree, "specs/notes" if kind in ("rc", "backlog") else "src/a.py")
    approve(root, sha, name=names.get(kind))
    return tree, rc if kind in ("job", "job-b") else repo


def _same_refusal(root: Path, tree: Path, error: str) -> None:
    """`preflight` and `merge` print the same one `[error]` line and `fix:` line, both exit 1."""
    merged = run(root, "merge", str(tree))
    assert merged.returncode == 1, merged.stderr
    lines = _lines(merged)
    assert len(lines) == 2 and lines[0].startswith(f"[error] {error}"), lines
    checked = run(root, "preflight", str(tree))
    assert checked.returncode == 1
    assert _lines(checked)[1:] == lines


@pytest.mark.parametrize("kind", ["task", "job", "job-b", "rc", "backlog", "reconcile", "hotfix"])
def test_preflight_refuses_an_ignored_file_neither_kept_nor_dropped_as_merge_does(
    root: Path, kind: str
) -> None:
    tree, _ = _kind(root, kind)
    (tree / "keep.scratch").write_text("x")
    _same_refusal(root, tree, "ignored files would be lost: keep.scratch")


@pytest.mark.parametrize("kind", ["task", "job", "job-b", "rc", "backlog", "reconcile", "hotfix"])
def test_preflight_refuses_a_target_checkout_off_the_target_branch_as_merge_does(
    root: Path, kind: str
) -> None:
    tree, into = _kind(root, kind)
    git(into, "switch", "-q", "-c", "elsewhere")
    _same_refusal(root, tree, f"{into} is not on ")
