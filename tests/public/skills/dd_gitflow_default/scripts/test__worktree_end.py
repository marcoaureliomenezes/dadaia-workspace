"""`worktree.py merge` lands a task on its job's main tree after hygiene and test separation,
a job's main tree on its release tree and a hotfix on the work branch after an APPROVED verdict
and the job gate, a `backlog` tree after its verdict and the ledger checks alone — HEAD as it is,
by fast-forward in the parent's checkout, then removes and `branch -d`s the tree, re-runnable; an
open child tree blocks its parent; every refusal (dirty, a moved parent, no verdict, a red gate,
ignored files, wrong branch, a stray blocking the fast-forward, a git failure) carries one `fix:`
that clears it; `clean` removes only an empty worktree of ours.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from subprocess import run as real_run
from typing import Any

import pytest

from dadaia_workspace.core.cli_line import fix_line, git_line, shell_line
from dadaia_workspace.core.platform import quote
from dadaia_workspace.infrastructure.ledger_scripts import (
    _PACKAGE_SKILLS,
    LEDGER_SCRIPTS,
    load_owner,
)
from tests.fixtures.harness_env import run_bash, run_python, suite_env
from tests.helpers.oslib import cli_argv, command, inline, read_text, venv_dir, write_text
from tests.helpers.oslib import run as os_run
from tests.helpers.release_state import write_release_phase
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import (
    CI,
    NEW_JOB,
    NEW_TASK,
    SCRIPT,
    approve,
    associate,
    commit,
    fixes,
    git,
    make_workspace,
    open_tree,
    patch_cli,
    run,
)
from tests.helpers.worktree_ws import run_fix as _fix

RC, HOTFIX, BACKLOG = "0.5.0/rc-1/wt-rc", "0.5.0/wt-hotfix-some-bug", "0.5.0/wt-backlog-x"
WORK = f"wt/{RC}"  # the branch a job's main tree lands on
TREE, RC_TREE = f"worktrees/r/{NEW_JOB}", f"worktrees/r/{RC}"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path := tmp_path / "my ws").mkdir()  # every fix runs as printed: quoted
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    open_tree(tmp_path, RC)
    open_tree(tmp_path, NEW_JOB)
    return tmp_path


def land(root: Path, rel: str, text: str = "x = 1\n") -> str:
    """Commit *rel* in the job's first task tree and merge it into the job's main tree."""
    task = open_tree(root, NEW_TASK)
    sha = commit(task, rel, text)
    merged = run(root, "merge", str(task))
    assert merged.returncode == 0, merged.stderr
    return sha


def _sync_line(root: Path, tree: Path) -> str:
    """The one `worktree sync <tree>` fix line, the workspace launcher first."""
    return fix_line(root, "worktree", "sync", str(tree))


def _run_printed(
    root: Path, tree: Path, refused: subprocess.CompletedProcess[str]
) -> subprocess.CompletedProcess[str]:
    """Run the refusal's printed `<launcher> worktree sync <tree>` fix as the script's own verb."""
    assert _line(refused) == _sync_line(root, tree)
    return run(root, "sync", str(tree))


def _dispatch(tree: Path) -> str:
    """The one dispatch act a verdict refusal prints for *tree* at its HEAD."""
    head = git(tree, "rev-parse", "HEAD").strip()
    return f"Agent action: dispatch dd-code-reviewer on {tree} at HEAD {head}; its verdict.py run writes the verdict"  # fmt: skip


def _hotfix(root: Path) -> Path:
    """A hotfix tree of an open bug the work branch holds."""
    ledger = '{"id": "some-bug", "status": "open"}\n'
    commit(root / "repos/r", "specs/bugs/BUGS.jsonl", ledger)
    return open_tree(root, HOTFIX)


def _line(result: subprocess.CompletedProcess[str]) -> str:
    """The one fix line, spelled as printed: the kernel's `command` is the oracle."""
    (fix,) = fixes(result)
    return fix.removeprefix("fix: ")


def test_merge_fast_forwards_removes_and_reruns(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    sha = land(root, "src/a.py")
    rejected = approve(
        root, sha, verdict="REJECTED", at="T09:00:00Z"
    )  # the newer APPROVED overrules
    (other := root / ".dadaia/states/verdicts/z").mkdir()  # another context and a non-UTC name:
    rejected.rename(other / "a.handoff.json")  # produced_at orders, never the path
    approve(root, sha)
    result = run(root, "merge", TREE)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", WORK).strip() == sha  # HEAD as approved
    assert not tree.exists()
    assert git(repo, "branch", "--list", "wt/*", "--format=%(refname:short)").split() == [WORK]
    assert run(root, "merge", TREE).returncode == 1  # a finished merge's rerun is never success
    assert run(root, "new", "r", NEW_JOB).returncode == 0
    shutil.rmtree(tree)  # the dadaia:-locked tree deleted by hand: an orphan, its exit clears it
    rows = json.loads(run(root, "list", "--json").stdout)
    assert len(rows) == 2  # the release tree and the orphan
    (row,) = (r for r in rows if r["state"] == "orphan")
    assert (row["state"], row["path"]) == ("orphan", str(tree))
    assert row["exit"] == command(sys.executable, str(SCRIPT), "merge", str(tree))
    assert run(root, "merge", str(tree)).returncode == 0
    assert [r["path"] for r in json.loads(run(root, "list", "--json").stdout)] == [
        str(root / RC_TREE)
    ]
    git(repo, "worktree", "add", "-q", "-b", f"wt/{NEW_JOB}", str(tree), WORK)
    commit(tree, "src/b.py")
    git(repo, "worktree", "remove", str(tree))  # interrupted: tree gone, its commit unmerged
    assert _line(run(root, "merge", TREE)) == command(
        *("git", "-C", str(repo), "worktree", "add", "-f", "-f", "--lock"),
        *("--reason", f"dadaia:{NEW_JOB}", str(tree), f"wt/{NEW_JOB}"),
    )
    assert git(repo, "branch", "--list", f"wt/{NEW_JOB}").strip()  # never -D


def test_a_task_whose_job_tree_is_gone_refuses_with_the_fix_that_restores_it(
    root: Path,
) -> None:
    task = open_tree(root, NEW_TASK)
    commit(task, "src/a.py")
    shutil.rmtree(root / TREE)  # removed by hand: git's registry still holds it, locked
    refused = run(root, "merge", str(task))
    assert refused.returncode == 1 and "Traceback" not in refused.stderr
    assert "[error]" in refused.stderr
    _fix(root, refused)
    assert (root / TREE).is_dir()
    porcelain = git(root / "repos/r", "worktree", "list", "--porcelain").splitlines()
    assert f"locked dadaia:{NEW_JOB}" in porcelain
    assert run(root, "merge", str(task)).returncode == 0


def test_a_gone_task_with_its_job_tree_gone_refuses_with_the_fix_that_restores_the_job_tree(
    root: Path,
) -> None:
    task = open_tree(root, NEW_TASK)
    commit(task, "src/a.py")
    shutil.rmtree(task)  # the branch survives
    shutil.rmtree(root / TREE)
    refused = run(root, "merge", str(task))
    assert refused.returncode == 1 and "[error]" in refused.stderr
    assert _line(refused) == command(
        *("git", "-C", str(root / "repos/r"), "worktree", "add", "-f", "-f", "--lock"),
        *("--reason", f"dadaia:{NEW_JOB}", str(root / TREE), f"wt/{NEW_JOB}"),
    )
    _fix(root, refused)
    assert (root / TREE).is_dir()
    assert _line(
        run(root, "merge", str(task))
    ) == command(  # the job tree is back: the task's own refusal
        *("git", "-C", str(root / "repos/r"), "worktree", "add", "-f", "-f", "--lock"),
        *("--reason", f"dadaia:{NEW_TASK}", str(task), f"wt/{NEW_TASK}"),
    )


def test_a_finished_task_merge_rerun_refuses_with_the_new_that_opens_it(root: Path) -> None:
    task = open_tree(root, NEW_TASK)
    commit(task, "src/a.py")
    assert run(root, "merge", str(task)).returncode == 0
    git(root / "repos/r", "worktree", "remove", "-f", "-f", str(root / TREE))
    git(
        root / "repos/r", "branch", "-D", f"wt/{NEW_JOB}"
    )  # the job landed: parent tree and branch gone
    rerun = run(root, "merge", str(task))
    assert rerun.returncode == 1 and "merged" not in rerun.stdout
    assert _line(rerun) == command(sys.executable, str(SCRIPT), "new", "r", NEW_TASK)


def test_merge_of_a_path_with_no_tree_and_no_branch_refuses_with_the_new_that_opens_it(
    root: Path,
) -> None:
    result = run(root, "merge", str(root / f"worktrees/r/{NEW_TASK}"))
    assert result.returncode == 1 and "merged" not in result.stdout
    assert _line(result) == command(sys.executable, str(SCRIPT), "new", "r", NEW_TASK)


def test_clean_of_a_task_with_its_job_tree_gone_refuses_with_the_fix_that_restores_it(
    root: Path,
) -> None:
    task = open_tree(root, NEW_TASK)
    shutil.rmtree(root / TREE)
    refused = run(root, "clean", str(task))
    assert refused.returncode == 1 and "[error]" in refused.stderr
    assert _line(refused) == command(
        *("git", "-C", str(root / "repos/r"), "worktree", "add", "-f", "-f", "--lock"),
        *("--reason", f"dadaia:{NEW_JOB}", str(root / TREE), f"wt/{NEW_JOB}"),
    )
    _fix(root, refused)
    assert run(root, "clean", str(task)).returncode == 0 and not task.exists()


@pytest.mark.parametrize("verb", ["merge", "clean"])
def test_a_git_failure_no_check_named_ends_as_one_refusal(root: Path, verb: str) -> None:
    (root / TREE / ".git").unlink()  # a tree git no longer recognizes
    refused = run(root, verb, TREE)
    assert refused.returncode == 1 and "Traceback" not in refused.stderr
    assert "[error]" in refused.stderr
    [fix] = fixes(refused)
    assert fix.startswith(
        f"fix: Agent action: clear what `{inline('git', '-C', str(root / TREE))} "
    )
    assert " reports above, then rerun " in fix
    assert fix.endswith(f"worktree.py {verb} {quote(str(root / TREE))}")  # absolute, never `list`


def test_a_dirty_tree_refuses_with_one_fix_that_commits_or_removes(root: Path) -> None:
    tree = root / TREE
    (tree / "wip").mkdir()  # an untracked directory, and a tracked edit staged:
    write_text(tree / "wip/x.py", "")
    write_text(tree / "specs/releases/0.5.0/rc-1/SPEC.md", "dirty")
    git(tree, "add", "specs/releases/0.5.0/rc-1/SPEC.md")
    git(tree, "rm", "-q", "specs/releases/0.5.0/rc-1/PLAN.md")  # a staged deletion
    dirty = run(root, "merge", TREE)
    assert "uncommitted" in dirty.stderr
    [dirty_fix] = fixes(dirty)  # Agent action: commit or remove
    listing, then, *remove = dirty_fix.split("`")[1::2]
    assert [listing, then] == [  # the commit takes its own message
        git_line(tree, "status", "--short"),
        git_line(tree, "commit"),
    ]
    assert run_bash(listing).returncode == 0
    for step in remove:
        run_bash(step, check=True)
    assert git(tree, "status", "--porcelain") == ""  # removed, clean,
    assert not (tree / "wip").exists()
    assert git(tree, "stash", "list") == ""  # never in the stack every worktree shares


def test_a_backlog_tree_lands_specs_only_through_the_ledger_checks(root: Path) -> None:
    """A `backlog` merge runs the ledger, trio and release checks alone — an
    invalid ledger refuses, a valid one lands with no test run; code refuses with its undo."""
    repo, tree = root / "repos/r", open_tree(root, BACKLOG)
    commit(tree, "specs/bugs/BUGS.jsonl", '{"id": "half"}\n')
    approve(root, git(tree, "rev-parse", "HEAD").strip())
    invalid = run(root, "merge", str(tree))
    assert invalid.returncode == 1 and "bugs.py check failed" in invalid.stderr
    git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    commit(tree, "RED-job", "")  # a file the job gate would fail on: never run here
    code = run(root, "merge", str(tree))
    assert "RED-job is code" in code.stderr
    [code_fix] = fixes(code)  # Agent action: restore, commit
    restore, then = code_fix.split("`")[1::2]
    run_bash(restore, check=True)  # runs as printed
    assert then == git_line(tree, "commit")
    git(tree, "commit", "-qm", "revert: RED-job")
    plan = tree / "specs/releases/0.5.0/rc-1/PLAN.md"
    draft = read_text(plan).replace("**Status:** Approved", "**Status:** Draft", 1)
    approve(root, sha := commit(tree, "specs/releases/0.5.0/rc-1/PLAN.md", draft))
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == sha
    assert "ci " not in landed.stdout and not tree.exists()


@pytest.mark.parametrize("name", [RC, BACKLOG])
def test_an_associated_repo_tree_lands_with_no_ledger_check_of_its_own(
    tmp_path: Path, name: str
) -> None:
    """`a` holds no `specs/`: its rc and backlog trees land on the verdict and gate alone."""
    make_workspace(root := tmp_path)
    associate(root, "Approved")
    repo = root / "repos/a"
    (repo / "scripts").mkdir()
    write_text(repo / "AGENTS.md", "verify: python scripts/ci.py job\n")
    write_text(repo / "scripts/ci.py", CI)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "gate")
    git(repo, "branch", "-f", "feature/0.5.0")
    git(repo, "switch", "-q", "feature/0.5.0")
    assert run(root, "new", "a", name).returncode == 0
    tree = root / "worktrees/a" / name
    sha = commit(tree, "AGENTS.md", "verify: python scripts/ci.py job\n# gate\n")
    approve(root, sha, name=name, repo="a")
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == sha and not tree.exists()


def test_work_branch_refusals_fix_runs_verbatim(tmp_path: Path) -> None:
    (ws := tmp_path / "my ws").mkdir()
    make_workspace(ws)
    repo = ws / "repos/r"
    git(repo, "branch", "feature/0.4.9", "feature/0.5.0")  # two work branches: the older goes
    two = run(ws, "new", "r", RC)
    assert "2 work branches" in two.stderr
    [fix] = fixes(two)
    for step in fix.split("`")[1::2]:  # Agent action: the backticked steps, in order
        run_bash(step, check=True)
    assert not git(repo, "branch", "--list", "feature/0.4.9").strip()
    git(repo, "branch", "-m", "feature/0.5.0", "dev")  # none: the fix cuts one from dev
    _fix(ws, none := run(ws, "new", "r", RC))
    assert "no work branch" in none.stderr
    assert git(repo, "branch", "--list", "feature/0.5.0").strip()  # the live release's, not a tag's


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
    copy = os_run(
        ["git", "-C", str(root / TREE), "commit-tree", f"{head}^{{tree}}", "-p", f"{head}~"],
        input="src/b.py\n",
        env=suite_env(os.environ, Path.home()) | {"GIT_COMMITTER_DATE": "2001-01-01T00:00:00"},
        check=True,
    ).stdout.strip()
    if older:  # the newest produced_at decides, never a name sorting last
        approve(root, head, verdict=older, at="T09:00:00Z").rename(
            root / ".dadaia/states/verdicts/c/v.handoff.json"
        )
    target = (
        approve(root, head, verdict=verdict, valid=valid, at=at)
        if named
        else (approve(root, copy), "--all")[1]
    )
    commit(root / RC_TREE, "src/z.py")  # moved: only an identical series in the reflog counts
    git(root / TREE, "rebase", "-q", WORK)
    result = run(root, "merge", TREE)
    head = git(root / TREE, "rev-parse", "HEAD").strip()
    assert result.returncode == 1 and head in result.stderr
    tree = root / TREE
    if not named:
        assert _line(result) == _dispatch(tree)
    elif valid and verdict == "REJECTED" and at.endswith("Z"):  # a naive instant is unparsed
        assert _line(result) == (
            f"Agent action: fix the findings of {target}, then dispatch"
            f" dd-code-reviewer on {tree} at its new HEAD; its verdict.py run writes the verdict"
        )
    else:
        expected = [*cli_argv(venv_dir(root)), "reports", "validate", str(target)]
        assert _line(result) == command(*expected, "--reviewed-root", str(tree))
    assert git(root / "repos/r", "rev-parse", WORK).strip() != head


def test_failed_fast_forward_tells_a_stray_from_a_moved_work_branch(root: Path) -> None:
    rc, tree = root / RC_TREE, root / TREE
    sha = land(root, "src/a.py")
    approve(root, sha)
    (rc / "src").mkdir()
    write_text(
        rc / "src/a.py", "stray"
    )  # untracked in the release tree: the fast-forward would clobber it
    stray = run(root, "merge", TREE)
    assert "src/a.py" in stray.stderr and fixes(stray) == [
        f"fix: Agent action: commit or remove the paths `{inline('git', '-C', str(rc), 'status', '--short')}` lists in {rc}"
    ]
    (rc / "src/a.py").unlink()
    # a sibling lands while the verdict is read
    move = f"sp.run(['git', '-C', {str(rc)!r}, 'commit', '-qm', 'm', '--allow-empty'])"
    verdict = 'elif args[:2] == ["reports", "validate"]:\n'
    patch_cli(root, verdict, f"{verdict}    import subprocess as sp; {move}\n")
    moved = run(root, "merge", TREE)
    assert _line(moved) == _sync_line(root, tree) and tree.exists()


def test_merge_lists_ignored_files_and_keeps_them_by_its_fix(root: Path) -> None:
    rc, tree = root / RC_TREE, root / TREE
    approve(root, land(root, "src/a.py"))
    write_text(tree / "my notes.scratch", "keep me")
    (tree / "__pycache__").mkdir()
    (tree / "__pycache__/a.pyc").write_bytes(b"")
    git(rc, "switch", "-q", "-c", "side")
    refused = run(root, "merge", TREE)
    assert "my notes.scratch" in refused.stderr and "__pycache__" not in refused.stderr
    wrong_branch = run(root, "merge", TREE, "--keep", "my notes.scratch")
    assert _line(wrong_branch) == command("git", "-C", str(rc), "switch", WORK)
    _fix(root, wrong_branch)
    [keep] = [c for c in refused.stderr.split("`") if "--keep" in c]
    _fix(root, subprocess.CompletedProcess([], 1, "", f"fix: {keep}\n"))
    assert read_text(rc / "my notes.scratch") == "keep me" and not tree.exists()


JOB2 = "0.5.0/rc-1/job-2/wt-main"


def _kind(root: Path, kind: str) -> tuple[Path, Path]:
    """A committed, approved tree of *kind* and the checkout its merge lands in."""
    repo, rc = root / "repos/r", root / RC_TREE
    if kind == "task":
        tree, into = open_tree(root, NEW_TASK), root / TREE
    elif kind == "job":
        tree, into = root / TREE, rc
    else:
        if kind == "hotfix":
            commit(repo, "specs/bugs/BUGS.jsonl", '{"id": "some-bug", "status": "open"}\n')
        names = {"job-b": JOB2, "backlog": BACKLOG, "hotfix": HOTFIX}
        if kind == "rc":  # the release tree lands on the repo, with no open job under it
            git(repo, "worktree", "remove", "-f", "-f", str(root / TREE))
        tree = rc if kind == "rc" else open_tree(root, names[kind])
        into = rc if kind == "job-b" else repo
    sha = commit(tree, "specs/notes" if kind in ("rc", "backlog") else "src/a.py")
    approve(
        root,
        sha,
        name=NEW_JOB
        if kind == "job"
        else {"job-b": JOB2, "rc": RC, "backlog": BACKLOG, "hotfix": HOTFIX}.get(kind),
    )
    return tree, into


def _error_lines(done: subprocess.CompletedProcess[str]) -> list[str]:
    return [ln for ln in done.stderr.splitlines() if ln.startswith("[error] ")]


@pytest.mark.parametrize("kind", ["task", "job", "job-b", "rc", "backlog", "hotfix"])
def test_merge_refuses_an_ignored_file_neither_kept_nor_dropped(root: Path, kind: str) -> None:
    tree, _ = _kind(root, kind)
    write_text(tree / "keep.scratch", "x")
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1
    [error] = _error_lines(refused)
    assert error.startswith("[error] ignored files would be lost: keep.scratch")
    [fix] = fixes(refused)
    assert "--keep" in fix and "--drop" in fix


@pytest.mark.parametrize("kind", ["task", "job", "job-b", "rc", "backlog", "hotfix"])
def test_merge_refuses_a_target_checkout_off_the_target_branch(root: Path, kind: str) -> None:
    tree, into = _kind(root, kind)
    git(into, "switch", "-q", "-c", "elsewhere")
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1
    [error] = _error_lines(refused)
    assert error.startswith(f"[error] {into} is not on ")
    assert len(fixes(refused)) == 1


def test_merge_without_a_verdict_refuses_with_only_the_verdict_message(root: Path) -> None:
    job = root / TREE
    head = commit(job, "src/a.py")
    refused = run(root, "merge", str(job))
    assert refused.returncode == 1
    [error] = _error_lines(refused)
    assert error.startswith(f"[error] the newest dd-code-reviewer handoff naming HEAD {head}")
    assert len(fixes(refused)) == 1
    approve(root, head, name=NEW_JOB)
    assert run(root, "merge", str(job)).returncode == 0


def test_clean_removes_only_an_empty_worktree_of_ours(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    commit(tree, "src/a.py")
    [fix] = fixes(run(root, "clean", TREE))
    assert fix == (
        f"fix: Agent action: dispatch dd-code-reviewer on {tree} at its HEAD; its verdict.py run"
        f" writes the verdict, then run `{inline(sys.executable, str(SCRIPT), 'merge', str(tree))}`"
    )
    git(tree, "reset", "-q", "--hard", WORK)
    assert run(root, "clean", TREE).returncode == 0 and not tree.exists()
    # ours is the canonical wt/ branch, locked or not; a tree on another is not
    other = "worktrees/r/0.5.0/rc-1/job-2/wt-main"
    git(repo, "worktree", "add", "-q", "-b", "side", str(root / other))
    foreign = run(root, "clean", other)
    assert foreign.returncode == 1 and (root / other).exists()


def test_release_closure_waits_for_every_other_wt(tmp_path: Path) -> None:
    """Closure runs in the release tree, whose own wt/* is spared; any other wt/* refuses it,
    naming repos/<r> and the owner's exit — `clean` for an empty tree, which clears it."""
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    open_tree(root, RC)
    specs = root / RC_TREE / "specs"
    write_release_phase(specs, "0.5.0", "IMPLEMENTATION")
    (specs / "releases/_archive").mkdir()
    write_text(specs / "releases/_archive/releases_histo.jsonl", "")
    open_tree(root, NEW_JOB)  # empty
    for skill in (
        "dd-spec-navigator",
        "dd-gitflow-default",
        "dd-release-implementation",
        "dd-bug-resolution",
    ):
        stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")
    script = tmp_path / "skills/dd-release-implementation/scripts/release.py"
    closure = [str(script), "phase", "CLOSURE", "--specs", str(specs)]

    refused = run_python(*closure, cwd=root)
    fix = refused.stderr.rsplit("fix: ", 1)[1].strip()
    assert "repos/r " in refused.stderr and fix.endswith(shell_line("clean", str(root / TREE)))
    run_bash(fix, cwd=root, check=True)
    assert run_python(*closure, cwd=root).returncode == 0


def test_a_verdict_carries_over_only_an_identical_patch_and_message_series(root: Path) -> None:
    """Once the work branch moved, a reword, a dropped or added empty
    commit, a reorder, code amended under the same message (a colored config included), a gitlink
    amended under the same message (diff.ignoreSubmodules=all), or a hand-resolved conflict each change the approved series and refuse for review."""
    repo, tree = root / "repos/r", root / TREE
    land(root, "src/a.py")
    git(tree, "commit", "-q", "--allow-empty", "-m", "empty")
    approve(root, approved := git(tree, "rev-parse", "HEAD").strip())
    commit(root / RC_TREE, "src/z.py")
    git(repo, "config", "color.ui", "always")
    work = git(repo, "rev-parse", WORK)
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
        git(tree, "rebase", "-q", WORK)
        assert _line(run(root, "merge", TREE)) == _dispatch(tree), change
        assert git(repo, "rev-parse", WORK) == work
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
    git(tree, "rebase", "-q", WORK)
    assert _line(run(root, "merge", TREE)) == _dispatch(tree)
    assert git(repo, "rev-parse", WORK) == work
    git(tree, "reset", "-q", "--hard", approved)
    work = commit(root / RC_TREE, "src/a.py", "theirs\n") + "\n"
    assert run(root, "merge", TREE).returncode == 1  # moved; the agent's rebase conflicts
    os_run(["git", "-C", str(tree), "rebase", WORK])
    write_text(tree / "src/a.py", "resolved\n")
    git(tree, "add", "src/a.py")
    git(tree, "-c", "core.editor=true", "rebase", "--continue")
    assert _line(run(root, "merge", TREE)) == _dispatch(tree)
    assert git(repo, "rev-parse", WORK) == work


@pytest.mark.parametrize("change", ["same-patch", "new-patch"])
def test_a_moved_work_branch_refuses_and_its_fix_rebase_keeps_only_an_identical_patch(
    root: Path, change: str
) -> None:
    """A moved work branch refuses with the `sync` fix line, both branches
    unchanged; after it, a patch-identical rebase lands under the old verdict,
    a changed patch refuses for review."""
    repo, tree = root / "repos/r", root / TREE
    approve(root, mine := land(root, "src/a.py"))
    work = commit(root / RC_TREE, "src/z.py")
    moved = run(root, "merge", TREE)
    assert _line(moved) == _sync_line(root, tree)
    assert [
        git(repo, "rev-parse", WORK).strip(),
        git(tree, "rev-parse", "HEAD").strip(),
    ] == [work, mine]
    assert _run_printed(root, tree, moved).returncode == 0
    if change == "new-patch":
        write_text(tree / "src/a.py", "x = 2\n")
        git(tree, "commit", "-q", "--amend", "-C", "HEAD", "-a")
    result = run(root, "merge", TREE)
    landed = git(repo, "rev-parse", WORK).strip()
    if change == "same-patch":
        assert result.returncode == 0, result.stderr
        assert git(repo, "rev-parse", f"{WORK}~").strip() == work != landed
    else:
        assert _line(result) == _dispatch(tree)
        assert landed == work


@pytest.mark.parametrize("how", ["amend-after-sync", "forged-synced-config"])
def test_a_tree_whose_patch_context_changed_is_refused_on_its_old_verdict(
    root: Path, how: str
) -> None:
    """The parent edits a line inside the reviewed hunk's context: a real `sync` then an amend
    that moves the reviewed line, or a hand rebase with a `synced` config line forged for the
    reviewed sha, each land code no verdict covers, so each refuses for review."""
    repo, tree = root / "repos/r", root / TREE
    lines = [f"l{i}\n" for i in range(30)]
    commit(root / RC_TREE, "src/a.py", "".join(lines))
    assert run(root, "sync", TREE).returncode == 0
    reviewed = commit(tree, "src/a.py", "".join(lines[:6] + ["guard()\n"] + lines[6:]))
    approve(root, reviewed, name=NEW_JOB)
    edited = [*lines[:8], "edited\n", *lines[9:]]
    work = commit(root / RC_TREE, "src/a.py", "".join(edited))
    if how == "amend-after-sync":
        assert run(root, "sync", TREE).returncode == 0
        moved = [*edited[:26], "guard()\n", *edited[26:]]
        write_text(tree / "src/a.py", "".join(moved))
        git(tree, "commit", "-q", "--amend", "-C", "HEAD", "-a")
    else:
        git(tree, "rebase", "-q", WORK)
        git(tree, "config", "--add", f"branch.wt/{NEW_JOB}.synced", reviewed)
    refused = run(root, "merge", TREE)
    assert refused.returncode == 1, refused.stdout
    assert _line(refused) == _dispatch(tree)
    assert git(repo, "rev-parse", WORK).strip() == work


@pytest.mark.parametrize("resolved", [False, True], ids=["empty-ledger", "resolved-record"])
def test_an_rc_merge_reads_the_gitflow_once(tmp_path: Path, resolved: bool) -> None:
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(repo := root / "repos/r", "checkout", "-q", "feature/0.5.0")
    if resolved:  # its fix commit is in the repo itself: no sibling repo is asked about
        git(repo, "commit", "-q", "--allow-empty", "-m", "fix(bugs): a-bug \u2014 the cause")
        record = {"id": "a-bug", "ts": "2026-10-19T10:00:00Z", "reported_by": "t", "title": "t",
                  "severity": "LOW", "component": "c", "context": "c", "symptom": "s",
                  "repro": "r", "expected": "e", "status": "resolved", "cause": "the cause",
                  "caused_by": "none", "closed_at": "2026-10-19T11:00:00Z", "solution": "s",
                  "fix_sha": git(repo, "rev-parse", "HEAD").strip()}  # fmt: skip
        commit(repo, "specs/bugs/BUGS.jsonl", json.dumps(record) + "\n")
    reads = tmp_path / "reads.log"
    patch_cli(
        root,
        'if args[:2] == ["context", "list"]:\n',
        f'if args[:2] == ["context", "list"]:\n    open({str(reads)!r}, "a").write("x")\n',
    )
    tree = open_tree(root, RC)
    approve(root, commit(tree, "src/z.py"), name=RC)
    reads.unlink(missing_ok=True)
    merged = run(root, "merge", str(tree))
    assert merged.returncode == 0, merged.stderr
    assert reads.read_text() == "x"


@pytest.mark.parametrize("red", [True, False], ids=["red-gate", "green-gate"])
def test_the_job_gate_runs_scripts_ci_job_as_argv_on_the_head_it_lands(
    root: Path, red: bool
) -> None:
    """A job merge runs the work branch's `verify:` on HEAD, one argv list with
    stdin closed, its output on stdout; a red gate lands nothing."""
    repo, tree = root / "repos/r", root / TREE
    head = land(root, "RED-job" if red else "src/a.py", "")
    approve(root, head)
    work = git(repo, "rev-parse", WORK).strip()
    result = run(root, "merge", TREE, input="stdin leak\n")
    assert result.stdout.splitlines().count("ci job") == 1
    assert "stdin leak" not in result.stdout
    assert git(repo, "rev-parse", WORK).strip() == (work if red else head)
    assert (result.returncode, tree.exists()) == ((1, True) if red else (0, False))
    if red:
        [result_fix] = fixes(result)
        act, line, where = result_fix.split("`")
        assert act == "fix: Agent action: make "
        assert line == "python scripts/ci.py job"
        assert where == f" exit 0 in {tree} and commit the fix in a task of this job"


def test_a_job_merge_needs_an_approved_verdict(root: Path) -> None:
    """No verdict refuses with the dispatch fix; an APPROVED verdict lands the
    job, and the merge re-run after it refuses: nothing is left to land."""
    repo = root / "repos/r"
    head = land(root, "src/a.py")
    assert _line(run(root, "merge", TREE)) == _dispatch(root / TREE)
    approve(root, head)
    landed = run(root, "merge", TREE)
    assert landed.returncode == 0, landed.stderr
    approve(root, head, at="T11:00:00Z")
    assert run(root, "merge", TREE).returncode == 1
    assert git(repo, "rev-parse", WORK).strip() == head


def test_memory_is_not_a_doctor_ledger() -> None:
    assert [script.filename for script in LEDGER_SCRIPTS] == [
        "bugs.py",
        "backlog.py",
        "release.py",
        "audit.py",
    ]


def test_a_declared_verify_line_runs_as_argv_never_through_a_shell(root: Path) -> None:
    """The `verify:` line is split by the one declared-line reader and run as argv: `;` and `$(...)`
    are words."""
    line = "verify: python scripts/ci.py job ; touch PWNED $(touch PWNED2)\n"
    commit(root / RC_TREE, "AGENTS.md", line)
    git(root / TREE, "merge", "-q", "--ff-only", WORK)
    head = land(root, "src/a.py")
    approve(root, head, name=NEW_JOB)
    result = run(root, "merge", TREE)
    assert result.returncode == 0, result.stderr
    assert "ci job ; touch PWNED $(touch PWNED2)" in result.stdout.splitlines()
    assert not list(root.rglob("PWNED*"))


def test_a_code_commit_made_on_the_job_branch_lands_once_reviewed(root: Path) -> None:
    """A job merge does not judge how code reached the branch; the one review
    and the job gate judge the whole diff — a commit made directly on it lands like a task's."""
    approve(root, commit(root / TREE, "src/stray.py"))
    landed = run(root, "merge", TREE)
    assert landed.returncode == 0, landed.stderr
    assert (root / RC_TREE / "src/stray.py").is_file()


@pytest.mark.parametrize(
    ("kind", "declared"),
    [("hotfix", ""), ("job", ""), ("job", "FOO=1 python scripts/ci.py job")],
    ids=["hotfix-absent", "job-absent", "job-env-assignment"],
)
def test_a_verify_line_refusal_clears_by_its_printed_act(
    root: Path, kind: str, declared: str
) -> None:
    """The work branch's `verify:` line judges a merge: when it is absent or unstartable, the printed
    act (a backlog lane lands the repo's `AGENTS.md`, then the printed sync of the tree owning the
    merge base) is performed verbatim, and the same merge then lands."""
    repo, good = root / "repos/r", read_text(root / "repos/r/AGENTS.md")
    commit(repo, "AGENTS.md", f"verify: {declared}\n" if declared else "")
    if kind == "hotfix":
        flags = ("--bug-id", "some-bug", "--reported-by", "t", "--title", "t", "--severity", "LOW",
                 "--component", "AGENTS.md", "--context", "c", "--symptom", "s",
                 "--repro", "r", "--expected", "e", "--correlates", "none")  # fmt: skip
        run_python(str(_PACKAGE_SKILLS / "dd-bug-resolution/scripts/bugs.py"), "append",
                   "--specs", str(repo / "specs"), *flags, check=True)  # fmt: skip
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "bug")
        tree, name, onto = open_tree(root, HOTFIX), HOTFIX, "feature/0.5.0"
        owner = tree
    else:
        assert run(root, "sync", str(root / RC_TREE)).returncode == 0  # rc and job carry the line
        tree, name, onto, owner = root / TREE, NEW_JOB, WORK, root / RC_TREE
        land(root, "AGENTS.md", good)  # the job's own good line never judges it
        land(root, "src/a.py")
    head = lambda: git(tree, "rev-parse", "HEAD").strip()  # noqa: E731
    approve(root, commit(tree, "src/b.py") if kind == "hotfix" else head(), name=name)
    refused = run(root, "merge", str(tree))
    act = ("add this repo's job gate as a verify: line of AGENTS.md on " + onto if not declared else
           f"make the verify: line of AGENTS.md on {onto} one argv list that starts"
           " (no shell: no VAR=value prefix, no sh -c)")  # fmt: skip
    assert refused.returncode == 1 and "Traceback" not in refused.stderr
    sync = inline(*cli_argv(venv_dir(root)), "worktree", "sync", str(owner))
    assert fixes(refused) == [f"fix: Agent action: {act} through a wt-backlog lane, then `{sync}`"]  # fmt: skip
    lane = open_tree(root, BACKLOG)
    approve(root, commit(lane, "AGENTS.md", good), name=BACKLOG)
    assert run(root, "merge", str(lane)).returncode == 0
    assert run(root, "sync", str(owner)).returncode == 0
    approve(root, head(), at="T11:00:00Z", name=name)
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr


def test_an_rc_gate_red_from_the_work_branch_clears_through_a_hotfix_then_the_printed_sync(
    tmp_path: Path,
) -> None:
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    repo = root / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    commit(repo, "RED-job", "")
    flags = ("--bug-id", "some-bug", "--reported-by", "t", "--title", "t", "--severity", "LOW",
             "--component", "AGENTS.md", "--context", "c", "--symptom", "s",
             "--repro", "r", "--expected", "e", "--correlates", "none")  # fmt: skip
    run_python(str(_PACKAGE_SKILLS / "dd-bug-resolution/scripts/bugs.py"), "append",
               "--specs", str(repo / "specs"), *flags, check=True)  # fmt: skip
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "bug")
    assert run(root, "new", "r", RC).returncode == 0
    tree = root / "worktrees/r" / RC
    approve(root, commit(tree, "src/z.py"), name=RC)
    refused = run(root, "merge", str(tree))
    sync = inline(*cli_argv(venv_dir(root)), "worktree", "sync", str(tree))
    [refused_fix] = fixes(refused)
    assert refused.returncode == 1 and refused_fix.endswith(f"then `{sync}`")
    hotfix = root / "worktrees/r/0.5.0/wt-hotfix-some-bug"
    assert run(root, "new", "r", "0.5.0/wt-hotfix-some-bug").returncode == 0
    git(hotfix, "rm", "-q", "RED-job")
    git(hotfix, "commit", "-qm", "fix code")
    approve(root, git(hotfix, "rev-parse", "HEAD").strip(), name="0.5.0/wt-hotfix-some-bug")
    assert run(root, "merge", str(hotfix)).returncode == 0
    assert run(root, "sync", str(tree)).returncode == 0
    approve(root, git(tree, "rev-parse", "HEAD").strip(), name=RC, at="T11:00:00Z")
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr


def test_a_tests_line_after_a_utf8_bom_is_declared(tmp_path: Path) -> None:
    """A BOM before the first line does not hide `tests:`."""
    sys.path.insert(0, str(_PACKAGE_SKILLS / "dd-gitflow-default" / "scripts"))
    end = load_owner("dd-gitflow-default", "_worktree_end")
    git(tmp_path, "init", "-q", "-b", "work")
    (tmp_path / "AGENTS.md").write_bytes(b"\xef\xbb\xbftests: x/**\n")
    git(tmp_path, "add", "AGENTS.md")
    git(tmp_path, "commit", "-q", "-m", "law")

    assert end._declared(tmp_path, "work", "tests:") == "x/**"


def _law_end(tmp_path: Path, law: bytes) -> Any:
    sys.path.insert(0, str(_PACKAGE_SKILLS / "dd-gitflow-default" / "scripts"))
    end = load_owner("dd-gitflow-default", "_worktree_end")
    git(tmp_path, "init", "-q", "-b", "work")
    (tmp_path / "AGENTS.md").write_bytes(law)
    git(tmp_path, "add", "AGENTS.md")
    git(tmp_path, "commit", "-q", "-m", "law")
    return end


@pytest.mark.parametrize("codepage", ["cp1251", "cp932"])
def test_a_tests_line_after_a_bom_is_declared_whatever_codepage_text_decoding_defaults_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, codepage: str
) -> None:
    """Real git; only the process boundary is wrapped: a `text=True` call naming no encoding
    decodes with the forced codepage, as on a machine whose locale is that codepage."""
    end = _law_end(tmp_path, b"\xef\xbb\xbftests: x/**\n")

    def run_in_locale(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("text") and not kwargs.get("encoding"):
            kwargs = {**kwargs, "encoding": codepage}
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", run_in_locale)
    try:
        declared: object = end._declared(tmp_path, "work", "tests:")
    except UnicodeDecodeError as exc:
        declared = type(exc).__name__

    assert declared == "x/**"


def test_git_output_decoded_with_replacement_keeps_a_latin1_laws_tests_line_declared(
    tmp_path: Path,
) -> None:
    """A latin-1 byte on another line does not hide `tests:`."""
    end = _law_end(tmp_path, b"# caf\xe9\ntests: tests/**\n")

    assert end._declared(tmp_path, "work", "tests:") == "tests/**"


def test_a_repo_declaring_only_verify_lines_lands_a_task_and_its_job(root: Path) -> None:
    """The three verify lines are the whole law a
    task and a job merge read; a repo declaring nothing else lands both."""
    law = "".join(f"verify{k}: python scripts/ci.py {lv}\n"
                  for k, lv in (("", "job"), ("-stage", "stage"), ("-task", "task")))  # fmt: skip
    commit(root / RC_TREE, "AGENTS.md", law)
    git(root / TREE, "merge", "-q", "--ff-only", WORK)
    approve(root, sha := land(root, "src/a.py"), name=NEW_JOB)
    landed = run(root, "merge", TREE)
    assert landed.returncode == 0, landed.stderr
    assert git(root / "repos/r", "rev-parse", WORK).strip() == sha


@pytest.mark.parametrize(
    ("law", "test_path"),
    [
        ("tests: checks/**\n", "checks/check_feature.py"),
        ("", "pkg/feature_test.go"),
    ],
    ids=["declared-test-path", "fallback-test-path"],
)
def test_an_implementation_commit_cannot_carry_a_test(root: Path, law: str, test_path: str) -> None:
    job = root / TREE
    commit(
        root / RC_TREE,
        "AGENTS.md",
        "verify: python scripts/ci.py job\n" + law,
    )
    git(job, "merge", "-q", "--ff-only", WORK)
    task = open_tree(root, NEW_TASK)
    for rel in ("src/feature.py", test_path):
        (task / rel).parent.mkdir(parents=True, exist_ok=True)
        write_text(task / rel, "value = 1\n")
        git(task, "add", rel)
    git(task, "commit", "-qm", "feat(J1.T2): implementation")

    refused = run(root, "merge", str(task))

    assert refused.returncode == 1
    assert test_path in refused.stderr
    assert git(job, "rev-parse", "HEAD").strip() != git(task, "rev-parse", "HEAD").strip()


@pytest.mark.parametrize(
    ("paths", "lands"),
    [
        (("tests/test_a.py",), True),
        (("tests/my test.py",), True),
        (("tests/test_a.py", "src/prod.py"), False),
    ],
    ids=["tests-only", "blank-in-name", "carries-source"],
)
def test_a_test_commit_lands_only_when_every_path_is_a_test(
    root: Path, paths: tuple[str, ...], lands: bool
) -> None:
    commit(root / RC_TREE, "AGENTS.md", "verify: python scripts/ci.py job\n")
    git(root / TREE, "merge", "-q", "--ff-only", WORK)
    task = open_tree(root, NEW_TASK)
    for rel in paths:
        (task / rel).parent.mkdir(parents=True, exist_ok=True)
        write_text(task / rel, "value = 1\n")
        git(task, "add", rel)
    git(task, "commit", "-qm", "test(J1.T1): red")

    done = run(root, "merge", str(task))

    if lands:
        assert done.returncode == 0, done.stderr
    else:
        assert done.returncode == 1
        assert "src/prod.py" in done.stderr
        [fix] = fixes(done)
        assert "implementation task" in fix and "implementation commit" not in fix


def test_a_repo_without_a_tests_declaration_lands_a_source_only_task(root: Path) -> None:
    job = root / TREE
    commit(root / RC_TREE, "AGENTS.md", "verify: python scripts/ci.py job\n")
    git(job, "merge", "-q", "--ff-only", WORK)
    task = open_tree(root, NEW_TASK)
    commit(task, "src/feature.py")

    landed = run(root, "merge", str(task))

    assert landed.returncode == 0, landed.stderr


def _task_tree(root: Path, rel: str = "src/a.py") -> tuple[Path, str]:
    """An open task tree of the job holding one commit: (tree, its sha)."""
    task = open_tree(root, NEW_TASK)
    return task, commit(task, rel)


def test_a_task_lands_on_its_main_tree_with_no_verdict_and_no_gate(root: Path) -> None:
    task, sha = _task_tree(root, "RED-job")  # a file the job gate would fail on: never run here

    landed = run(root, "merge", str(task))

    assert landed.returncode == 0, landed.stderr
    assert "ci " not in landed.stdout and not task.exists()
    assert git(root / TREE, "rev-parse", "HEAD").strip() == sha
    assert git(root / "repos/r", "rev-parse", WORK).strip() != sha


_TERM = "zorblaxquux"  # an operator term no baseline pattern matches


def _real_denylist_gate(root: Path) -> None:
    """The stub's one real verb: `ci push-gate-check`, the matcher and its remedy, from this checkout's source."""
    patch_cli(
        root,
        "else:\n    sys.stdin.read()",
        'elif args[:2] == ["ci", "push-gate-check"]:\n    import os, subprocess\n'
        f'    sys.exit(subprocess.call([{sys.executable!r}, "-m", "dadaia_workspace", *args],'
        f" env=dict(os.environ, PYTHONPATH={str(Path(__file__).parents[5])!r})))\n"
        "else:\n    sys.stdin.read()",
    )
    write_text(
        root / ".dadaia/states/spec_contexts.json", '{"contexts": []}'
    )  # the real verb reads it
    # the workspace's own operator term: the loader never falls through to the live instance's file
    write_text(root / ".dadaia/states/privacy_denylist.json", f'{{"{_TERM}": "test"}}')


def test_a_task_carrying_a_denylisted_literal_is_refused_then_lands_by_its_printed_fix(
    root: Path,
) -> None:
    address = ".".join(["8"] * 4)  # a public IPv4 literal, spelled so this file holds none
    _real_denylist_gate(root)
    task = open_tree(root, NEW_TASK)
    (task / "tests").mkdir()
    for name, text in (("a", f'HOST = "{address}"\n'), ("b", "B = 1\n")):
        write_text(task / f"tests/test_{name}.py", text)
        git(task, "add", f"tests/test_{name}.py")
        git(task, "commit", "-qm", f"test(J1.T1): red {name}")
    onto = git(root / TREE, "rev-parse", "HEAD").strip()

    refused = run(root, "merge", str(task))

    assert refused.returncode == 1
    shown = refused.stdout + refused.stderr  # the scan's findings, then the refusal
    assert "tests/test_a.py" in shown and address not in shown
    assert git(root / TREE, "rev-parse", "HEAD").strip() == onto
    reworded = _hand_rewrite(task, onto, [_edit_tree("tests/test_a.py", "HOST = None\n"), None])
    assert reworded.returncode == 0, reworded.stderr
    landed = run(root, "merge", str(task))
    assert landed.returncode == 0, landed.stderr
    assert address not in git(root / TREE, "log", "-p", f"{onto}..HEAD")
    messages = git(root / TREE, "log", "--format=%B", f"{onto}..HEAD")
    assert "test(J1.T1): red a" in messages and "test(J1.T1): red b" in messages


def test_a_task_carrying_an_operator_term_is_refused_under_the_merge_fence(root: Path) -> None:
    _real_denylist_gate(root)
    task = open_tree(root, NEW_TASK)
    commit(task, "src/a.py", f"NOTE = '{_TERM}'\n")
    git(task, "commit", "-q", "--amend", "-m", "fix(J1.T1): green")

    refused = run(root, "merge", str(task))

    assert refused.returncode == 1
    shown = refused.stdout + refused.stderr
    assert "src/a.py" in shown and _TERM not in shown
    assert "operator denylist + baseline" in shown


def test_a_red_then_green_task_lands_after_its_printed_fix_with_both_kinds_apart(
    root: Path,
) -> None:
    address = ".".join(["8"] * 4)  # a public IPv4 literal, spelled so this file holds none
    _real_denylist_gate(root)
    task = open_tree(root, NEW_TASK)
    (task / "tests").mkdir()
    write_text(task / "tests/test_a.py", f'HOST = "{address}"\n')
    git(task, "add", "tests/test_a.py")
    git(task, "commit", "-qm", "test(J1.T1): red")
    write_text(task / "src.py", "B = 1\n")
    git(task, "add", "src.py")
    git(task, "commit", "-qm", "fix(J1.T1): green")
    onto = git(root / TREE, "rev-parse", "HEAD").strip()

    refused = run(root, "merge", str(task))

    assert refused.returncode == 1
    reworded = _hand_rewrite(task, onto, [_edit_tree("tests/test_a.py", "HOST = None\n"), None])
    assert reworded.returncode == 0, reworded.stderr
    landed = run(root, "merge", str(task))
    assert landed.returncode == 0, landed.stderr
    subjects = git(root / TREE, "log", "--reverse", "--format=%s", f"{onto}..HEAD").splitlines()
    assert subjects == ["test(J1.T1): red", "fix(J1.T1): green"]
    assert git(root / TREE, "show", "--format=", "--name-only", "HEAD").split() == ["src.py"]


def _git_proc(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """`git` as the helper runs it, with the exit code left to the caller."""
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={"HOME": str(repo), "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1"},
    )
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    return real_run(["git", *ident, "-C", str(repo), *args], env=env, capture_output=True, text=True, check=False)  # fmt: skip


def _edit_tree(rel: str, text: str) -> Callable[[Path], None]:
    """A hand edit of the commit a rebase stopped at: the file rewritten, amended into it."""

    def step(task: Path) -> None:
        write_text(task / rel, text)
        git(task, "add", rel)
        git(task, "commit", "-q", "--amend", "--no-edit")

    return step


def _reword_subject(subject: str) -> Callable[[Path], None]:
    """A hand reword of the commit a rebase stopped at: its message replaced by *subject*."""

    def step(task: Path) -> None:
        git(task, "commit", "-q", "--amend", "-m", subject)

    return step


def _hand_rewrite(
    task: Path, base: str, steps: list[Callable[[Path], None] | None]
) -> subprocess.CompletedProcess[str]:
    """The act a refusal's Agent action names, done by hand: an interactive rebase of
    `<base>..HEAD` stops at every commit, one step per commit edits it, and the rebase continues.
    Order and subjects stay unless a step names a new one."""
    stopped = _git_proc(task, "-c", "sequence.editor=sed -i s/^pick/edit/", "rebase", "-i", base)
    assert stopped.returncode == 0, stopped.stderr
    done = stopped
    for step in steps:
        if step is not None:
            step(task)
        done = _git_proc(task, "rebase", "--continue")
    return done


def _red_then(root: Path, address: str, green: str, *flags: str) -> Path:
    """A task of a `test(` commit carrying *address*, then a `feat(` implementation commit."""
    task = open_tree(root, NEW_TASK)
    (task / "tests").mkdir()
    write_text(task / "tests/test_a.py", f'HOST = "{address}"\n')
    git(task, "add", "tests/test_a.py")
    git(task, "commit", "-qm", "test(J1.T1): red")
    write_text(task / "src.py", "B = 1\n")
    git(task, "add", "src.py")
    git(task, "commit", "-q", *flags, "-m", green)
    return task


def test_a_message_hit_on_the_implementation_lands_after_its_printed_fix_and_message(
    root: Path,
) -> None:
    address = ".".join(["8"] * 4)  # a public IPv4 literal, spelled so this file holds none
    _real_denylist_gate(root)
    task = _red_then(root, address, f"feat(J1.T1): host {address}")
    onto = git(root / TREE, "rev-parse", "HEAD").strip()

    refused = run(root, "merge", str(task))
    assert refused.returncode == 1
    reworded = _hand_rewrite(
        task,
        onto,
        [_edit_tree("tests/test_a.py", "HOST = None\n"), _reword_subject("feat(J1.T1): host")],
    )
    assert reworded.returncode == 0, reworded.stderr
    landed = run(root, "merge", str(task))
    assert landed.returncode == 0, landed.stderr
    log = git(root / TREE, "log", "--reverse", "--format=%s", f"{onto}..HEAD").splitlines()
    assert log == ["test(J1.T1): red", "feat(J1.T1): host"]
    assert address not in git(root / TREE, "log", "-p", f"{onto}..HEAD")


def test_an_uncommitted_edit_clears_nothing_and_the_refusal_prints_one_fix(root: Path) -> None:
    address = ".".join(["8"] * 4)
    _real_denylist_gate(root)
    task = _red_then(root, address, "feat(J1.T1): host")
    head = git(task, "rev-parse", "HEAD")

    refused = run(root, "merge", str(task))
    assert refused.returncode == 1
    write_text(task / "tests/test_a.py", "HOST = None\n")  # edited, never committed
    stuck = run(root, "merge", str(task))

    assert stuck.returncode != 0
    assert len([ln for ln in stuck.stderr.splitlines() if ln.startswith("fix: ")]) == 1
    assert git(task, "rev-parse", "HEAD") == head
    assert git(task, "status", "--porcelain").split() == ["M", "tests/test_a.py"]


@pytest.mark.parametrize("kind", ["job", "rc"])
def test_main_and_rc_merges_run_no_denylist_scan(root: Path, kind: str) -> None:
    address = ".".join(["8"] * 4)
    _real_denylist_gate(root)
    if kind == "rc":  # the release tree lands on the repo, with no open job under it
        git(root / "repos/r", "worktree", "remove", "-f", "-f", str(root / TREE))
    tree, name = (root / TREE, NEW_JOB) if kind == "job" else (root / RC_TREE, RC)
    approve(root, commit(tree, "src/a.py", f"HOST = '{address}'\n"), name=name)

    landed = run(root, "merge", str(tree))

    assert landed.returncode == 0, landed.stderr


@pytest.mark.parametrize("kind", ["hotfix", "backlog"])
def test_every_tree_kind_is_refused_for_a_denylisted_literal(root: Path, kind: str) -> None:
    address = ".".join(["8"] * 4)
    _real_denylist_gate(root)
    tree = {
        "hotfix": lambda: _hotfix(root),
        "backlog": lambda: open_tree(root, BACKLOG),
    }[kind]()
    rel = "specs/a.md" if kind == "backlog" else "src/a.py"
    commit(tree, rel, f"HOST {address}\n")

    refused = run(root, "merge", str(tree))

    assert refused.returncode == 1
    shown = refused.stdout + refused.stderr
    assert rel in shown and address not in shown
    assert len(fixes(refused)) == 1


def test_a_dirty_main_tree_refuses_its_tasks_merge(root: Path) -> None:
    task, sha = _task_tree(root)
    write_text(root / TREE / "wip.py", "")  # untracked in the tree the task lands on

    refused = run(root, "merge", str(task))

    assert refused.returncode == 1 and str(root / TREE) in refused.stderr
    assert "uncommitted" in refused.stderr
    assert git(root / TREE, "rev-parse", "HEAD").strip() != sha


@pytest.mark.parametrize("kind", ["task", "main", "hotfix"])
def test_merge_fast_forwards_in_the_parents_checkout(root: Path, kind: str) -> None:
    repo, rc, job = root / "repos/r", root / RC_TREE, root / TREE
    if kind == "task":
        tree, sha = _task_tree(root)
        parent = job
    elif kind == "main":
        sha = land(root, "src/a.py")
        approve(root, sha)
        tree, parent = job, rc
    else:
        tree = _hotfix(root)
        approve(root, sha := commit(tree, "src/a.py"))
        parent = repo

    landed = run(root, "merge", str(tree))

    assert landed.returncode == 0, landed.stderr
    assert git(parent, "rev-parse", "HEAD").strip() == sha
    assert {p for p in (repo, rc, job) if (p / "src/a.py").exists()} == {parent}
    assert not tree.exists()


def test_a_hotfix_lands_on_the_work_branch_only_through_a_verdict_and_the_job_gate(
    root: Path,
) -> None:
    repo, tree = root / "repos/r", _hotfix(root)
    head = commit(tree, "RED-job", "")
    work = git(repo, "rev-parse", "feature/0.5.0").strip()

    assert _line(run(root, "merge", str(tree))) == _dispatch(tree)
    approve(root, head)
    red = run(root, "merge", str(tree))

    assert red.returncode == 1 and red.stdout.splitlines().count("ci job") == 1
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == work and tree.exists()
    assert fixes(red) == [
        f"fix: Agent action: make `python scripts/ci.py job` exit 0 in {tree} and commit the fix in this worktree"
    ]


def test_an_open_task_blocks_its_main_tree_merge(root: Path) -> None:
    task, _ = _task_tree(root)
    approve(root, commit(root / TREE, "src/b.py"))
    work = git(root / "repos/r", "rev-parse", WORK).strip()

    refused = run(root, "merge", TREE)

    assert refused.returncode == 1
    assert _line(refused) == command(sys.executable, str(SCRIPT), "merge", str(task))
    assert git(root / "repos/r", "rev-parse", WORK).strip() == work


def test_an_open_main_tree_blocks_its_release_tree_merge(root: Path) -> None:
    refused = run(root, "merge", RC_TREE)

    assert refused.returncode == 1
    assert _line(refused) == command(sys.executable, str(SCRIPT), "merge", str(root / TREE))


def test_a_workflow_file_named_test_is_not_a_test_when_no_tests_line_is_declared(
    tmp_path: Path,
) -> None:
    end = _law_end(tmp_path, b"verify: python scripts/ci.py job\n")

    assert end._is_test_path(".github/workflows/test_on_push.yml", []) is False


def _plain_tree(root: Path, name: str) -> Path:
    """A tree of any name made with raw git, as an old-layout workspace may still hold."""
    repo = root / "repos/r"
    tree = root / "worktrees/r" / name
    git(repo, "worktree", "add", "-q", "-b", f"wt/{name}", str(tree), "feature/0.5.0")
    return tree


@pytest.mark.parametrize("name", ["maintenance", "0.5.0-rc1/j1", "0.5.0-rc1/define"])
def test_a_plain_tree_is_refused_by_merge(tmp_path: Path, name: str) -> None:
    root = make_workspace(tmp_path)
    repo = root / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    commit(repo, "AGENTS.md", "verify: python scripts/ci.py job\n")
    tree = _plain_tree(root, name)
    head = commit(tree, "src/a.py")
    approve(root, head)

    refused = run(root, "merge", str(tree))

    assert refused.returncode == 1
    assert "not a worktree name" in refused.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() != head


def test_no_dadaia_base_key_is_ever_written_for_a_branch(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    repo = root / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")

    assert run(root, "new", "r", "early").returncode == 1
    git(repo, "branch", "-m", "feature/0.5.0", "feature/0.6.0")
    run(root, "new", "r", "early")

    assert "dadaia-base" not in git(repo, "config", "--list")


def test_a_verdict_citing_a_file_only_the_reviewed_tree_holds_is_accepted(root: Path) -> None:
    """The stub CLI resolves a
    `self_pull` ref as the real `reports validate` does, against `--reviewed-root` only (the repo
    checkout never holds the ref), so the gate must pass the tree it judged."""
    patch_cli(
        root,
        'sys.exit(0 if "schema_version" in json.load(open(args[2])) else 1)',
        "import os; h = json.load(open(args[2])); r = args[args.index('--reviewed-root') + 1:][:1]\n"
        "    sys.exit(0 if 'schema_version' in h and r and all(os.path.isfile(os.path.join(r[0], f))"
        " for f in h.get('self_pull', {}).get('refs', [])) else 1)",
    )
    head = land(root, "src/only_in_tree.py")
    handoff = approve(root, head)
    body = json.loads(read_text(handoff))
    write_text(handoff, json.dumps({**body, "self_pull": {"refs": ["src/only_in_tree.py"]}}))
    landed = run(root, "merge", TREE)
    assert landed.returncode == 0, landed.stderr
    assert git(root / "repos/r", "rev-parse", WORK).strip() == head


@pytest.mark.parametrize(
    ("law", "key", "argv"),
    [
        (b"verify: python scripts\\ci.py job\n", "verify:", ["python", "scripts\\ci.py", "job"]),
        (b"tests: checks\\** x/**\n", "tests:", ["checks\\**", "x/**"]),
        (b"verify: a ; b $(c)\n", "verify:", ["a", ";", "b", "$(c)"]),
        (b"", "verify:", []),
    ],
    ids=["windows-path", "tests-glob-line", "shell-words", "absent"],
)
def test_a_declared_line_splits_on_whitespace_alone(
    tmp_path: Path, law: bytes, key: str, argv: list[str]
) -> None:
    """One reader splits `verify:` and `tests:` lines, keeping backslashes."""
    end = _law_end(tmp_path, law)

    assert end._declared_argv(tmp_path, "work", key) == argv


def test_the_repo_job_gate_is_the_job_level_of_ci_py(tmp_path: Path) -> None:
    """This repo's own `AGENTS.md` declares `python scripts/ci.py job` as its `verify:` line."""
    law = (Path(__file__).resolve().parents[5] / "AGENTS.md").read_bytes()

    assert _law_end(tmp_path, law)._declared_argv(tmp_path, "work", "verify:") == ["python", "scripts/ci.py", "job"]  # fmt: skip


@pytest.mark.parametrize(
    ("law", "argv"),
    [
        (
            b'verify: pytest -m "not e2e and not quarantine" tests\n',
            ["pytest", "-m", "not e2e and not quarantine", "tests"],
        ),
        (b'verify: python "C:\\work x\\ci.py" job\n', ["python", "C:\\work x\\ci.py", "job"]),
        (
            b"verify: sh -c 'export A=1; python ci.py job' x\n",
            ["sh", "-c", "export A=1; python ci.py job", "x"],
        ),
        (b'verify: python -c "" x\n', ["python", "-c", "", "x"]),
        (b'verify: a"b c"d e\n', ["ab cd", "e"]),
    ],
    ids=[
        "quoted-word",
        "quoted-windows-path-with-space",
        "sh-c-argument",
        "empty-quotes",
        "mid-word-quotes",
    ],
)
def test_a_quote_groups_one_word_of_a_declared_line(
    tmp_path: Path, law: bytes, argv: list[str]
) -> None:
    """Words split on whitespace, a quote groups a word, a backslash stays literal."""
    end = _law_end(tmp_path, law)

    assert end._declared_argv(tmp_path, "work", "verify:") == argv


def test_an_unbalanced_quote_in_a_declared_line_is_one_refusal_with_one_fix(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    tree = root / "repos" / "law"
    tree.mkdir()
    end = _law_end(tree, b'verify: pytest -m "not e2e tests\n')

    with pytest.raises(end.Refusal) as refused:
        end._declared_argv(tree, "work", "verify:")

    assert refused.value.args[0] == "the verify: line of work has an unclosed quote"
    assert refused.value.fix.startswith(
        "Agent action: close the quote in the verify: line of AGENTS.md on work through a "
        "wt-backlog lane, then `"
    )
    assert refused.value.fix.endswith(f"then `{_sync_line(root, tree)}`")
    assert "\n" not in refused.value.fix


def test_a_task_merge_reads_the_gitflow_once(root: Path, tmp_path: Path) -> None:
    reads = tmp_path / "reads.log"
    patch_cli(
        root,
        'if args[:2] == ["context", "list"]:\n',
        f'if args[:2] == ["context", "list"]:\n    open({str(reads)!r}, "a").write("x")\n',
    )
    land(root, "src/a.py")
    assert reads.read_text() == "x"
