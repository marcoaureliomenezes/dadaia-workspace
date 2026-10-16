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
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.cli_line import fix_line, git_line, shell_line
from dadaia_workspace.infrastructure.ledger_scripts import (
    _PACKAGE_SKILLS,
    LEDGER_SCRIPTS,
    load_owner,
)
from tests.fixtures.harness_env import run_bash, run_python, suite_env
from tests.helpers.release_state import write_release_phase
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import (
    NEW_JOB,
    NEW_TASK,
    SCRIPT,
    approve,
    cli_path,
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


def _sync_argv(root: Path, tree: Path) -> list[str]:
    """The one `worktree sync <tree>` fix line as the shell splits it, the workspace launcher first."""
    return shlex.split(fix_line(root, "worktree", "sync", str(tree)))


def _run_printed(
    root: Path, refused: subprocess.CompletedProcess[str]
) -> subprocess.CompletedProcess[str]:
    """Run the refusal's printed `<launcher> worktree <verb> …` fix as the script's own verb."""
    launcher, worktree, *verb = _argv(refused)
    assert [launcher, worktree] == [str(cli_path(root)), "worktree"]
    return run(root, *verb)


def _hotfix(root: Path) -> Path:
    """A hotfix tree of an open bug the work branch holds."""
    ledger = '{"id": "some-bug", "status": "open"}\n'
    commit(root / "repos/r", "specs/bugs/BUGS.jsonl", ledger)
    return open_tree(root, HOTFIX)


def _argv(result: subprocess.CompletedProcess[str]) -> list[str]:
    """The one fix line, split as the shell will: the expected argv is the oracle."""
    (fix,) = fixes(result)
    return [
        str(Path(w)) if Path(w).is_absolute() else w for w in shlex.split(fix.removeprefix("fix: "))
    ]


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
    assert git(repo, "rev-parse", WORK).strip() == sha  # HEAD as approved
    assert not tree.exists()
    assert git(repo, "branch", "--list", "wt/*", "--format=%(refname:short)").split() == [WORK]
    assert run(root, "merge", TREE).returncode == 0  # a finished merge re-runs clean
    assert run(root, "new", "r", NEW_JOB).returncode == 0
    shutil.rmtree(tree)  # the dadaia:-locked tree deleted by hand: an orphan, its exit clears it
    rows = json.loads(run(root, "list", "--json").stdout)
    assert len(rows) == 2  # the release tree and the orphan
    (row,) = (r for r in rows if r["state"] == "orphan")
    assert (row["state"], row["path"]) == ("orphan", str(tree))
    assert run(root, *shlex.split(row["exit"])[2:]).returncode == 0
    assert [r["path"] for r in json.loads(run(root, "list", "--json").stdout)] == [
        str(root / RC_TREE)
    ]
    git(repo, "worktree", "add", "-q", "-b", f"wt/{NEW_JOB}", str(tree), WORK)
    commit(tree, "src/b.py")
    git(repo, "worktree", "remove", str(tree))  # interrupted: tree gone, its commit unmerged
    assert _argv(run(root, "merge", TREE)) == [
        *("git", "-C", str(repo), "worktree", "add", str(tree), f"wt/{NEW_JOB}")
    ]
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
    assert run(root, "merge", str(task)).returncode == 0


@pytest.mark.parametrize("verb", ["merge", "clean"])
def test_a_git_failure_no_check_named_ends_as_one_refusal(root: Path, verb: str) -> None:
    (root / TREE / ".git").unlink()  # a tree git no longer recognizes
    refused = run(root, verb, TREE)
    assert refused.returncode == 1 and "Traceback" not in refused.stderr
    assert "[error]" in refused.stderr
    [fix] = fixes(refused)
    assert fix.startswith("fix: Agent action: clear the git failure above, then rerun ")
    assert fix.endswith(f"worktree.py {verb} {TREE}")  # the rerun as given, never `list`


def test_a_dirty_tree_refuses_with_one_fix_that_commits_or_removes(root: Path) -> None:
    tree = root / TREE
    (tree / "wip").mkdir()  # an untracked directory, and a tracked edit staged:
    (tree / "wip/x.py").write_text("")
    (tree / "specs/releases/0.5.0/rc-1/SPEC.md").write_text("dirty")
    git(tree, "add", "specs/releases/0.5.0/rc-1/SPEC.md")
    dirty = run(root, "merge", TREE)
    assert "uncommitted" in dirty.stderr
    add, then, *remove = fixes(dirty)[0].split("`")[1::2]  # Agent action: commit or remove
    assert [add, then] == [  # the commit takes its own message
        git_line(tree, "add", "-A"),
        git_line(tree, "commit"),
    ]
    for step in remove:
        subprocess.run(step, shell=True, check=True, capture_output=True)  # noqa: S602
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
    restore, then = fixes(code)[0].split("`")[1::2]  # Agent action: restore, commit
    subprocess.run(restore, shell=True, check=True)  # noqa: S602 — runs as printed
    assert then == git_line(tree, "commit")
    git(tree, "commit", "-qm", "revert: RED-job")
    plan = tree / "specs/releases/0.5.0/rc-1/PLAN.md"
    draft = plan.read_text().replace("**Status:** Approved", "**Status:** Draft", 1)
    approve(root, sha := commit(tree, "specs/releases/0.5.0/rc-1/PLAN.md", draft))
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == sha
    assert "ci " not in landed.stdout and not tree.exists()


def test_work_branch_refusals_fix_runs_verbatim(tmp_path: Path) -> None:
    (ws := tmp_path / "my ws").mkdir()
    make_workspace(ws)
    repo = ws / "repos/r"
    git(repo, "branch", "feature/0.4.9", "feature/0.5.0")  # two work branches: the older goes
    two = run(ws, "new", "r", RC)
    assert "2 work branches" in two.stderr
    for step in fixes(two)[0].split("`")[1::2]:  # Agent action: the backticked steps, in order
        subprocess.run(step, shell=True, check=True, capture_output=True)  # noqa: S602
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
    copy = subprocess.run(  # head's tree, parent and message, outside wt/<name>'s reflog
        ["git", "-C", str(root / TREE), "commit-tree", f"{head}^{{tree}}", "-p", f"{head}~"],
        input="src/b.py\n",
        env=suite_env(os.environ, Path.home()) | {"GIT_COMMITTER_DATE": "2001-01-01T00:00:00"},
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if older:  # the newest produced_at decides, never a name sorting last
        approve(root, head, verdict=older, at="T09:00:00Z").rename(
            root / ".dadaia/handoff/c/v.handoff.json"
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
    cli = str(cli_path(root))
    expected = [cli, "reports", "validate", str(target)]
    assert _argv(result) == expected + (["--reviewed-root", str(root / TREE)] if named else [])
    assert git(root / "repos/r", "rev-parse", WORK).strip() != head


def test_failed_fast_forward_tells_a_stray_from_a_moved_work_branch(root: Path) -> None:
    rc, tree = root / RC_TREE, root / TREE
    sha = land(root, "src/a.py")
    approve(root, sha)
    (rc / "src").mkdir()
    (rc / "src/a.py").write_text(
        "stray"
    )  # untracked in the release tree: the fast-forward would clobber it
    stray = run(root, "merge", TREE)
    assert "src/a.py" in stray.stderr and fixes(stray) == [
        f"fix: Agent action: commit or remove the paths above in {rc}"
    ]
    (rc / "src/a.py").unlink()
    # a sibling lands while the verdict is read
    move = f"subprocess.run(['git', '-C', {str(rc)!r}, 'commit', '-qm', 'm', '--allow-empty'])"
    verdict = 'elif args[:2] == ["reports", "validate"]:\n'
    patch_cli(root, verdict, f"{verdict}    import subprocess; {move}\n")
    moved = run(root, "merge", TREE)
    assert _argv(moved) == _sync_argv(root, tree) and tree.exists()


def test_merge_lists_ignored_files_and_keeps_them_by_its_fix(root: Path) -> None:
    rc, tree = root / RC_TREE, root / TREE
    approve(root, land(root, "src/a.py"))
    (tree / "my notes.scratch").write_text("keep me")
    (tree / "__pycache__").mkdir()
    (tree / "__pycache__/a.pyc").write_bytes(b"")
    git(rc, "switch", "-q", "-c", "side")
    refused = run(root, "merge", TREE)
    assert "my notes.scratch" in refused.stderr and "__pycache__" not in refused.stderr
    wrong_branch = run(root, "merge", TREE, "--keep", "my notes.scratch")
    assert _argv(wrong_branch) == ["git", "-C", str(rc), "switch", WORK]
    _fix(root, wrong_branch)
    _fix(root, refused)
    assert (rc / "my notes.scratch").read_text() == "keep me" and not tree.exists()


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
    (tree / "keep.scratch").write_text("x")
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1
    [error] = _error_lines(refused)
    assert error.startswith("[error] ignored files would be lost: keep.scratch")
    assert len(fixes(refused)) == 1


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
    assert _argv(run(root, "clean", TREE)) == [sys.executable, str(SCRIPT), "merge", str(tree)]
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
    (specs / "releases/_archive/releases_histo.jsonl").write_text("")
    open_tree(root, NEW_JOB)  # empty
    for skill in (
        "dd-spec-navigator",
        "dd-gitflow-default",
        "dd-release-implementation",
        "dd-bug-resolution",
    ):
        stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")
    script = tmp_path / "skills/dd-release-implementation/scripts/release.py"
    closure = [str(script), "phase", "CLOSURE", "--sha", "beef123", "--specs", str(specs)]

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
    refusal = [str(cli_path(root)), "reports", "validate", "--all"]
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
        assert _argv(run(root, "merge", TREE)) == refusal, change
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
    assert _argv(run(root, "merge", TREE)) == refusal
    assert git(repo, "rev-parse", WORK) == work
    git(tree, "reset", "-q", "--hard", approved)
    work = commit(root / RC_TREE, "src/a.py", "theirs\n") + "\n"
    assert run(root, "merge", TREE).returncode == 1  # moved; the agent's rebase conflicts
    subprocess.run(["git", "-C", str(tree), "rebase", WORK], capture_output=True)
    (tree / "src/a.py").write_text("resolved\n")
    git(tree, "add", "src/a.py")
    git(tree, "-c", "core.editor=true", "rebase", "--continue")
    assert _argv(run(root, "merge", TREE)) == refusal
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
    assert _argv(moved) == _sync_argv(root, tree)
    assert [
        git(repo, "rev-parse", WORK).strip(),
        git(tree, "rev-parse", "HEAD").strip(),
    ] == [work, mine]
    assert _run_printed(root, moved).returncode == 0
    if change == "new-patch":
        (tree / "src/a.py").write_text("x = 2\n")
        git(tree, "commit", "-q", "--amend", "-C", "HEAD", "-a")
    result = run(root, "merge", TREE)
    landed = git(repo, "rev-parse", WORK).strip()
    if change == "same-patch":
        assert result.returncode == 0, result.stderr
        assert git(repo, "rev-parse", f"{WORK}~").strip() == work != landed
    else:
        assert _argv(result)[1:] == ["reports", "validate", "--all"] and landed == work


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
        act, line, where = fixes(result)[0].split("`")
        assert act == "fix: Agent action: make "
        assert shlex.split(line) == [
            "python",
            "scripts/ci.py",
            "job",
        ]
        assert where == f" exit 0 in {tree} and commit the fix in this worktree"


def test_a_job_merge_needs_a_verdict_naming_its_ci_matrix_run(root: Path) -> None:
    """No verdict refuses; an APPROVED verdict lands the job with or without a
    remote CI run named — the repo's `verify:` line is the job gate (no host is assumed)."""
    repo = root / "repos/r"
    head = land(root, "src/a.py")
    assert _argv(run(root, "merge", TREE))[1:] == ["reports", "validate", "--all"]
    approve(root, head)
    landed = run(root, "merge", TREE)
    assert landed.returncode == 0, landed.stderr
    approve(root, head, at="T11:00:00Z")
    assert run(root, "merge", TREE).returncode == 0
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
    ("declared", "act"),
    [("", "add this repo's job gate as a verify: line to"),
     ("FOO=1 python scripts/ci.py job", "make the verify: line of")],
    ids=["absent", "env-assignment"],
)  # fmt: skip
def test_a_job_gate_reads_the_work_branch_verify_line_not_its_own(
    root: Path, declared: str, act: str
) -> None:
    """A job whose task rewrote `verify:` is still judged by the work branch's
    line; its absent or unstartable refusal names the work branch, and doing that act lands."""
    rc, tree, agents = root / RC_TREE, root / TREE, root / "repos/r/AGENTS.md"
    good = agents.read_text()
    rest = "".join(ln for ln in good.splitlines(keepends=True) if not ln.startswith("verify:"))
    commit(rc, "AGENTS.md", (f"verify: {declared}\n" if declared else "") + rest)
    git(tree, "merge", "-q", "--ff-only", WORK)
    land(root, "AGENTS.md", good)  # the job's own line never judges it
    approve(root, land(root, "src/a.py"), name=NEW_JOB)
    refused = run(root, "merge", TREE)
    assert refused.returncode == 1 and "Traceback" not in refused.stderr
    tail = (f" and commit it on {WORK}" if not declared else
            f" on {WORK} one argv list that starts: it runs without a shell"
            " — no VAR=value prefix, no sh -c")  # fmt: skip
    assert fixes(refused) == [f"fix: Agent action: {act} {agents}{tail}"]
    commit(rc, "AGENTS.md", good)
    git(tree, "rebase", "-q", WORK)
    approve(root, git(tree, "rev-parse", "HEAD").strip(), at="T11:00:00Z", name=NEW_JOB)
    landed = run(root, "merge", TREE)
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
    real_run = subprocess.run

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
        (task / rel).write_text("value = 1\n", encoding="utf-8")
        git(task, "add", rel)
    git(task, "commit", "-qm", "feat(J1.T2): implementation")

    refused = run(root, "merge", str(task))

    assert refused.returncode == 1
    assert test_path in refused.stderr
    assert git(job, "rev-parse", "HEAD").strip() != git(task, "rev-parse", "HEAD").strip()


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


def test_a_dirty_main_tree_refuses_its_tasks_merge(root: Path) -> None:
    task, sha = _task_tree(root)
    (root / TREE / "wip.py").write_text("")  # untracked in the tree the task lands on

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

    assert _argv(run(root, "merge", str(tree)))[1:] == ["reports", "validate", "--all"]
    approve(root, head)
    red = run(root, "merge", str(tree))

    assert red.returncode == 1 and red.stdout.splitlines().count("ci job") == 1
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == work and tree.exists()


def test_an_open_task_blocks_its_main_tree_merge(root: Path) -> None:
    task, _ = _task_tree(root)
    approve(root, commit(root / TREE, "src/b.py"))
    work = git(root / "repos/r", "rev-parse", WORK).strip()

    refused = run(root, "merge", TREE)

    assert refused.returncode == 1
    assert _argv(refused) == [sys.executable, str(SCRIPT), "merge", str(task)]
    assert git(root / "repos/r", "rev-parse", WORK).strip() == work


def test_an_open_main_tree_blocks_its_release_tree_merge(root: Path) -> None:
    refused = run(root, "merge", RC_TREE)

    assert refused.returncode == 1
    assert _argv(refused) == [sys.executable, str(SCRIPT), "merge", str(root / TREE)]


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
@pytest.mark.parametrize("declared_verify", [True, False], ids=["verify-once", "no-verify"])
def test_a_plain_tree_is_refused_by_merge_with_the_list_fix(
    tmp_path: Path, declared_verify: bool, name: str
) -> None:
    root = make_workspace(tmp_path)
    repo = root / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    law = "verify: python scripts/ci.py job\n" if declared_verify else "# local law\n"
    commit(repo, "AGENTS.md", law)
    tree = _plain_tree(root, name)
    head = commit(tree, "src/a.py")
    approve(root, head)

    refused = run(root, "merge", str(tree))

    assert refused.returncode == 1
    assert "not a worktree name" in refused.stderr
    assert [f.removeprefix("fix: ") for f in fixes(refused)] == [
        shell_line(sys.executable, str(SCRIPT), "list")
    ]
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
    body = json.loads(handoff.read_text())
    handoff.write_text(json.dumps({**body, "self_pull": {"refs": ["src/only_in_tree.py"]}}))
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
    ],
    ids=["quoted-word", "quoted-windows-path-with-space", "sh-c-argument"],
)
def test_a_quote_groups_one_word_of_a_declared_line(
    tmp_path: Path, law: bytes, argv: list[str]
) -> None:
    """Words split on whitespace, a quote groups a word, a backslash stays literal."""
    end = _law_end(tmp_path, law)

    assert end._declared_argv(tmp_path, "work", "verify:") == argv


def test_an_unbalanced_quote_in_a_declared_line_is_one_refusal_with_one_fix(tmp_path: Path) -> None:
    end = _law_end(tmp_path, b'verify: pytest -m "not e2e tests\n')

    with pytest.raises(end.Refusal) as refused:
        end._declared_argv(tmp_path, "work", "verify:")

    assert refused.value.fix.startswith("Agent action: ")
    assert "\n" not in refused.value.fix
