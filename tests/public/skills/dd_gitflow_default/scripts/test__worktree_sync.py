"""`worktree.py sync <path>` rebases a tree and the trees below it, parents first (the release
tree onto the work branch, each job's main tree onto the release tree, each task onto its main
tree), skipping a tree that already holds its base. The first conflict or dirty tree stops it with
one `fix:` naming the tree; a re-run finishes; nothing is pushed. After a lane lands on the work
branch, `sync` of the release tree lets its `merge` pass.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import run_bash
from tests.helpers.oslib import cli_argv, command, read_text, venv_dir, write_text
from tests.helpers.oslib import run as os_run
from tests.helpers.worktree_ws import (
    NEW_JOB,
    NEW_TASK,
    approve,
    commit,
    fixes,
    git,
    make_workspace,
    open_tree,
    run,
)

_BUGS = (
    Path(__file__).resolve().parents[5]
    / "dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py"
)
WORK = "feature/0.5.0"
RC, LANE = "0.5.0/rc-1/wt-rc", "0.5.0/wt-backlog-x"
CHAIN = [RC, NEW_JOB, NEW_TASK]  # each tree is cut from the one before; the first from WORK


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path := tmp_path / "my ws").mkdir()
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", WORK)
    for name in CHAIN:
        open_tree(tmp_path, name)
        commit(tmp_path / "worktrees/r" / name, f"src/{name.rsplit('/', 1)[1]}.py")
    return tmp_path


def _holds(root: Path, base: str, name: str) -> bool:
    """Whether the tree *name* has *base* as an ancestor."""
    probe = os_run(
        ["git", "-C", str(root / "repos/r"), "merge-base", "--is-ancestor", base, f"wt/{name}"]
    )
    return probe.returncode == 0


def _heads(root: Path) -> list[str]:
    return [git(root / "repos/r", "rev-parse", f"wt/{name}").strip() for name in CHAIN]


def _move_work(root: Path, rel: str = "src/w.py", text: str = "x = 1\n") -> None:
    commit(root / "repos/r", rel, text)


def test_sync_rebases_the_tree_and_those_below_it_parents_first(root: Path) -> None:
    _move_work(root)
    result = run(root, "sync", str(root / "worktrees/r" / RC))
    assert result.returncode == 0, result.stderr
    # a child holds its parent's rebased tip only if the parent went first
    bases = [WORK, *(f"wt/{name}" for name in CHAIN[:-1])]
    assert [_holds(root, base, name) for base, name in zip(bases, CHAIN, strict=True)] == [True] * 3
    for name in CHAIN:  # every tree keeps its own commit
        leaf = name.rsplit("/", 1)[1]
        assert read_text(root / "worktrees/r" / name / f"src/{leaf}.py") == "x = 1\n"


def test_sync_keeps_a_commit_once_on_the_parent_and_later_removed_from_it(root: Path) -> None:
    repo, rc = root / "repos/r", root / "worktrees/r" / RC
    git(repo, "merge", "-q", "--ff-only", f"wt/{RC}")  # the work branch once held the tree's commit
    git(repo, "reset", "-q", "--hard", "HEAD~1")  # and then lost it
    _move_work(root)
    assert run(root, "sync", str(rc)).returncode == 0
    assert _holds(root, WORK, RC)
    assert (rc / "src/wt-rc.py").is_file()


def test_sync_skips_a_tree_that_holds_its_base(root: Path) -> None:
    commit(root / "worktrees/r" / RC, "src/rc2.py")  # the job is behind its tree; the tree is not
    _move_work(root)
    git(root / "worktrees/r" / RC, "merge", "-q", "--no-edit", WORK)  # the tree holds WORK by merge
    before = _heads(root)
    assert run(root, "sync", str(root / "worktrees/r" / RC)).returncode == 0
    after = _heads(root)
    assert after[0] == before[0] and after[1:] != before[1:]
    assert _holds(root, f"wt/{RC}", NEW_JOB) and _holds(root, f"wt/{NEW_JOB}", NEW_TASK)


def test_sync_of_a_task_leaves_its_parents_alone(root: Path) -> None:
    commit(root / "worktrees/r" / NEW_JOB, "src/j2.py")
    before = _heads(root)
    assert run(root, "sync", str(root / "worktrees/r" / NEW_TASK)).returncode == 0
    after = _heads(root)
    assert after[:2] == before[:2] and _holds(root, f"wt/{NEW_JOB}", NEW_TASK)


def test_sync_stops_at_the_first_conflict_with_one_fix_line_and_a_rerun_finishes(
    root: Path,
) -> None:
    job, task = root / "worktrees/r" / NEW_JOB, root / "worktrees/r" / NEW_TASK
    commit(job, "src/c.py", "mine\n")  # the work branch will write src/c.py too
    git(root / "repos/r", "worktree", "remove", "-f", "-f", str(task))
    git(root / "repos/r", "branch", "-D", f"wt/{NEW_TASK}")
    open_tree(root, NEW_TASK)  # re-cut: the task now carries the job's conflicting commit
    commit(task, "src/t2.py")
    _move_work(root, "src/c.py", "theirs\n")
    heads = git(job, "rev-parse", "HEAD"), git(task, "rev-parse", "HEAD")
    stopped = run(root, "sync", str(root / "worktrees/r" / RC))
    assert stopped.returncode == 1 and str(job) in stopped.stderr
    assert len(fixes(stopped)) == 1 and fixes(stopped)[0].startswith("fix: Agent action: ")
    # agent default, unruled: a conflict leaves the rebase aborted, the tree at its pre-sync head
    assert (git(job, "rev-parse", "HEAD"), git(task, "rev-parse", "HEAD")) == heads
    underway = git(job, "rev-parse", "--path-format=absolute", "--git-path", "rebase-merge")
    assert git(job, "status", "--porcelain") == "" and not Path(underway.strip()).exists()
    conflicted = os_run(["git", "-C", str(job), "rebase", f"wt/{RC}"])
    assert conflicted.returncode == 1  # the agent resolves it by hand
    write_text(job / "src/c.py", "resolved\n")
    git(job, "add", "src/c.py")
    git(job, "-c", "core.editor=true", "rebase", "--continue")
    again = run(root, "sync", str(root / "worktrees/r" / RC))
    assert again.returncode == 0, again.stderr
    assert _holds(root, f"wt/{NEW_JOB}", NEW_TASK) and read_text(task / "src/c.py") == "resolved\n"


def test_sync_refuses_a_dirty_tree_and_touches_nothing_below_it(root: Path) -> None:
    job, task = root / "worktrees/r" / NEW_JOB, root / "worktrees/r" / NEW_TASK
    _move_work(root)
    write_text(job / "src/main.py", "edited\n")
    heads = git(job, "rev-parse", "HEAD"), git(task, "rev-parse", "HEAD")
    rc_head = _heads(root)[0]
    refused = run(root, "sync", str(root / "worktrees/r" / RC))
    assert refused.returncode == 1 and str(job) in refused.stderr and len(fixes(refused)) == 1
    assert (git(job, "rev-parse", "HEAD"), git(task, "rev-parse", "HEAD")) == heads
    assert _heads(root)[0] == rc_head
    assert read_text(job / "src/main.py") == "edited\n"


def test_sync_never_pushes(root: Path, tmp_path: Path) -> None:
    remote = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    repo = root / "repos/r"
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-q", "origin", WORK)
    _move_work(root)
    listed = git(repo, "ls-remote", "origin")
    assert run(root, "sync", str(root / "worktrees/r" / RC)).returncode == 0
    assert git(repo, "ls-remote", "origin") == listed


def test_after_a_lane_lands_sync_lets_the_release_tree_merge(root: Path) -> None:
    for name in (NEW_TASK, NEW_JOB):  # an open child blocks the release tree's merge
        tree = root / "worktrees/r" / name
        git(root / "repos/r", "worktree", "remove", "-f", "-f", str(tree))
        git(root / "repos/r", "branch", "-D", f"wt/{name}")
    rc = root / "worktrees/r" / RC
    approve(root, commit(rc, "src/r.py"), name=RC)
    lane = open_tree(root, LANE)
    plan = "specs/releases/0.5.0/rc-1/PLAN.md"
    draft = read_text(lane / plan).replace("**Status:** Approved", "**Status:** Draft", 1)
    approve(root, commit(lane, plan, draft), name=LANE)
    assert run(root, "merge", str(lane)).returncode == 0
    moved = run(root, "merge", str(rc))
    assert moved.returncode == 1 and "moved past" in moved.stderr
    printed = command(*cli_argv(venv_dir(root)), "worktree", "sync", str(rc))
    assert fixes(moved) == [f"fix: {printed}"]
    if not printed.startswith("Agent action: "):  # a runnable line starts the launcher
        assert run_bash(printed, cwd=root).returncode == 0
    assert run(root, "sync", str(rc)).returncode == 0
    landed = run(root, "merge", str(rc))
    assert landed.returncode == 0, landed.stderr


def test_a_missing_tree_refuses_naming_it(root: Path) -> None:
    gone = root / "worktrees/r/0.5.0/rc-1/job-2/wt-main"
    refused = run(root, "sync", str(gone))
    assert refused.returncode == 1 and str(gone) in refused.stderr
    [_fix] = fixes(refused)


def test_sync_of_a_lane_leaves_the_bug_it_resolved_fixed_with_no_ledger_step(root: Path) -> None:
    lane = open_tree(root, LANE)
    (lane / "src").mkdir(exist_ok=True)
    (lane / "specs/bugs").mkdir(parents=True)
    write_text(lane / "src/fix.py", "fixed = 1\n")
    git(lane, "add", "src/fix.py")
    git(lane, "commit", "-q", "-m", "fix(bugs): a-bug \u2014 the cause")
    sha = git(lane, "rev-parse", "HEAD").strip()
    record = {"id": "a-bug", "ts": "2026-10-19T10:00:00Z", "reported_by": "t", "title": "t",
              "severity": "LOW", "component": "src/fix.py", "context": "c", "symptom": "s",
              "repro": "r", "expected": "e", "status": "resolved", "cause": "the cause",
              "caused_by": "none", "closed_at": "2026-10-19T11:00:00Z", "solution": "s",
              "fix_sha": sha}  # fmt: skip
    write_text(lane / "specs/bugs/BUGS.jsonl", json.dumps(record) + "\n")
    git(lane, "add", "specs/bugs/BUGS.jsonl")
    git(lane, "commit", "-q", "-m", "chore(bugs): resolve a-bug \u2014 the cause")
    check = [sys.executable, str(_BUGS), "check", "--specs", str(lane / "specs")]
    assert os_run(check).returncode == 0
    _move_work(root)
    assert run(root, "sync", str(lane)).returncode == 0
    assert git(lane, "rev-parse", "HEAD~1").strip() != sha  # the rebase rewrote the cited commit
    done = os_run(check)
    assert done.returncode == 0, done.stdout + done.stderr
