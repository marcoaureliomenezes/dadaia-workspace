"""`worktree.py preflight <tree>` is `merge` without the verdict — it runs
every check `merge` runs for the tree's kind, collects each refusal and prints
`PREFLIGHT PASS|FAIL <tree> <sha>`, each failing check with its message and its one `fix:` line.
Size: MEDIUM (real git, tmp workspace, a stub CLI).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import git_line
from tests.helpers.worktree_ws import JOB, TASK, approve, commit, fixes, git, make_workspace, run

BRANCH = "feature/0.5.0"
JOB_BRANCH = f"wt/{JOB}"
DEFINE = "0.5.0-rc1/define"
RED_VERIFY = "make `python scripts/ci.py job` exit 0 in {tree} and commit the fix in this worktree"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path := tmp_path / "ws").mkdir()
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", BRANCH)
    return tmp_path


def _tree(root: Path, name: str) -> Path:
    assert run(root, "new", "r", name).returncode == 0
    return root / "worktrees/r" / name


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
    job = _tree(root, JOB)
    task = _tree(root, TASK)
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
    job = _tree(root, JOB)
    commit(job, "src/a.py")
    _pass(root, job)
    task = _tree(root, TASK)
    head, error, fix = _report(root, job)
    assert head == f"PREFLIGHT FAIL {job} {_head(job)}"
    assert error == f"[error] task worktree {task} of {JOB_BRANCH} is open"
    assert fix.endswith(f" merge {task}")
    assert run(root, "clean", str(task)).returncode == 0
    commit(job, "RED-job", "")
    _fail(root, job, "verify: exited 1", f"Operator action: {RED_VERIFY.format(tree=job)}")


def test_a_define_tree_passes_without_a_verify_run_and_fails_a_red_ledger_check(root: Path) -> None:
    define = _tree(root, DEFINE)
    commit(define, "specs/notes", "")
    commit(define, "specs/RED-job", "")  # the job gate would fail on it: a define tree runs none
    done = run(root, "preflight", str(define))
    assert done.returncode == 0 and "ci job" not in done.stdout + done.stderr, done.stderr
    assert _report(root, define) == [f"PREFLIGHT PASS {define} {_head(define)}"]
    commit(define, "specs/bugs/BUGS.jsonl", '{"id": "half"}\n')
    _fail(
        root,
        define,
        f"bugs.py check failed on {define / 'specs'}",
        f"Operator action: fix the findings above in {define} and commit them",
    )


def test_a_backlog_tree_fails_a_path_outside_specs(root: Path) -> None:
    tree = _tree(root, "backlog/x")
    commit(tree, "src/a.py")
    _fail(
        root,
        tree,
        "src/a.py is code; a define or backlog tree lands specs/ only — code lands through a job",
        f"Operator action: revert src/a.py to {BRANCH} in one commit — "
        f"`{git_line(tree, 'restore', '-s', BRANCH, '-SW', '--', 'src/a.py')}` and `{git_line(tree, 'commit')}`",
    )


def test_a_reconcile_tree_fails_a_red_verify_as_a_job_tree_does(root: Path) -> None:
    tree = _tree(root, "0.5.0-rc1/reconcile")
    commit(tree, "RED-job", "")
    _fail(root, tree, "verify: exited 1", f"Operator action: {RED_VERIFY.format(tree=tree)}")


def test_a_plain_tree_passes_with_no_verify_line_and_fails_dirty(root: Path) -> None:
    repo = root / "repos/r"
    (repo / "AGENTS.md").write_text("no gate declared\n")
    git(repo, "commit", "-qam", "no verify")
    tree = _tree(root, "fix-a")
    commit(tree, "RED-job", "")  # a red gate would refuse: none is declared, none runs
    _pass(root, tree)
    (tree / "wip").write_text("x")
    add, commit_ = git_line(tree, "add", "-A"), git_line(tree, "commit")
    fix = (
        f"Operator action: commit them in their commit shape (`{add}` and `{commit_}`) or remove"
        f" them (`{git_line(tree, 'clean', '-fd')}` and `{git_line(tree, 'restore', '-SW', '.')}`)"
        " — never a stash every worktree shares"
    )
    _fail(root, tree, f"{tree} has uncommitted changes", fix)


def test_a_hotfix_tree_fails_a_red_verify(root: Path) -> None:
    repo = root / "repos/r"
    commit(repo, "specs/bugs/BUGS.jsonl", '{"id": "a-block-bug", "status": "open"}\n')
    tree = _tree(root, "hotfix/a-block-bug")
    commit(tree, "RED-job", "")
    _fail(root, tree, "verify: exited 1", f"Operator action: {RED_VERIFY.format(tree=tree)}")


def test_merge_on_a_passing_tree_without_a_verdict_refuses_only_with_the_verdict_message(
    root: Path,
) -> None:
    job = _tree(root, JOB)
    head = commit(job, "src/a.py")
    _pass(root, job)
    refused = run(root, "merge", str(job))
    assert refused.returncode == 1
    errors = [ln for ln in refused.stderr.splitlines() if ln.startswith("[error] ")]
    assert len(errors) == 1 and errors[0].startswith(f"[error] the newest dd-code-reviewer handoff naming HEAD {head}")  # fmt: skip
    assert len(fixes(refused)) == 1
    approve(root, head)
    assert run(root, "merge", str(job)).returncode == 0


def _kind(root: Path, kind: str) -> tuple[Path, Path]:
    """A committed, approved tree of *kind* and the checkout its merge lands in."""
    repo = root / "repos/r"
    if kind == "task":
        job = _tree(root, JOB)
        tree = _tree(root, TASK)
        commit(tree, "src/a.py")
        return tree, job
    if kind == "hotfix":
        commit(repo, "specs/bugs/BUGS.jsonl", '{"id": "a-block-bug", "status": "open"}\n')
    name = {
        "job": JOB,
        "plain": "fix-a",
        "define": DEFINE,
        "backlog": "backlog/x",
        "reconcile": "0.5.0-rc1/reconcile",
        "hotfix": "hotfix/a-block-bug",
    }[kind]
    tree = _tree(root, name)
    approve(root, commit(tree, "specs/notes" if kind in ("define", "backlog") else "src/a.py"))
    return tree, repo


def _same_refusal(root: Path, tree: Path, error: str) -> None:
    """`preflight` and `merge` print the same one `[error]` line and `fix:` line, both exit 1."""
    merged = run(root, "merge", str(tree))
    assert merged.returncode == 1, merged.stderr
    lines = _lines(merged)
    assert len(lines) == 2 and lines[0].startswith(f"[error] {error}"), lines
    checked = run(root, "preflight", str(tree))
    assert checked.returncode == 1
    assert _lines(checked)[1:] == lines


@pytest.mark.parametrize(
    "kind", ["task", "job", "plain", "define", "backlog", "reconcile", "hotfix"]
)
def test_preflight_refuses_an_ignored_file_neither_kept_nor_dropped_as_merge_does(
    root: Path, kind: str
) -> None:
    tree, _ = _kind(root, kind)
    (tree / "keep.scratch").write_text("x")
    _same_refusal(root, tree, "ignored files would be lost: keep.scratch")


@pytest.mark.parametrize(
    "kind", ["task", "job", "plain", "define", "backlog", "reconcile", "hotfix"]
)
def test_preflight_refuses_a_target_checkout_off_the_target_branch_as_merge_does(
    root: Path, kind: str
) -> None:
    tree, into = _kind(root, kind)
    git(into, "switch", "-q", "-c", "elsewhere")
    _same_refusal(root, tree, f"{into} is not on ")
