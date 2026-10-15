"""`worktree.py sync <path>` rebases a tree and the trees below it, parents first (the release
tree onto the work branch, each job's main tree onto the release tree, each task onto its main
tree), skipping a tree that already holds its base. The first conflict or dirty tree stops it with
one `fix:` naming the tree; a re-run finishes; nothing is pushed. After a lane lands on the work
branch, `sync` of the release tree lets its `merge` pass.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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
    probe = subprocess.run(
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
    bases = [WORK, *(f"wt/{name}" for name in CHAIN)]
    assert [_holds(root, base, name) for base, name in zip(bases, CHAIN, strict=True)] == [True] * 3
    for name in CHAIN:  # every tree keeps its own commit
        leaf = name.rsplit("/", 1)[1]
        assert (root / "worktrees/r" / name / f"src/{leaf}.py").read_text() == "x = 1\n"


def test_sync_skips_a_tree_that_holds_its_base(root: Path) -> None:
    commit(root / "worktrees/r" / RC, "src/rc2.py")  # the job is behind its tree; the tree is not
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


def _conflict(root: Path) -> subprocess.CompletedProcess[str]:
    """The work branch and the job's tree both write `src/c.py`; the task is behind the job."""
    commit(root / "worktrees/r" / NEW_JOB, "src/c.py", "mine\n")
    _move_work(root, "src/c.py", "theirs\n")
    return run(root, "sync", str(root / "worktrees/r" / RC))


def test_sync_stops_at_the_first_conflict_with_one_fix_line_and_a_rerun_finishes(
    root: Path,
) -> None:
    job, task = root / "worktrees/r" / NEW_JOB, root / "worktrees/r" / NEW_TASK
    task_head = git(task, "rev-parse", "HEAD")
    stopped = _conflict(root)
    assert stopped.returncode == 1 and str(job) in stopped.stderr
    assert len(fixes(stopped)) == 1 and fixes(stopped)[0].startswith("fix: Agent action: ")
    assert git(task, "rev-parse", "HEAD") == task_head  # nothing below the conflict moved
    subprocess.run(
        ["git", "-C", str(job), "rebase", f"wt/{RC}"], capture_output=True
    )  # if not under way
    (job / "src/c.py").write_text("resolved\n")
    git(job, "add", "src/c.py")
    git(job, "-c", "core.editor=true", "rebase", "--continue")
    again = run(root, "sync", str(root / "worktrees/r" / RC))
    assert again.returncode == 0, again.stderr
    assert (
        _holds(root, f"wt/{NEW_JOB}", NEW_TASK) and (task / "src/c.py").read_text() == "resolved\n"
    )


def test_sync_refuses_a_dirty_tree_and_touches_nothing_below_it(root: Path) -> None:
    job, task = root / "worktrees/r" / NEW_JOB, root / "worktrees/r" / NEW_TASK
    _move_work(root)
    (job / "src/main.py").write_text("edited\n")
    heads = git(job, "rev-parse", "HEAD"), git(task, "rev-parse", "HEAD")
    refused = run(root, "sync", str(root / "worktrees/r" / RC))
    assert refused.returncode == 1 and str(job) in refused.stderr and len(fixes(refused)) == 1
    assert (git(job, "rev-parse", "HEAD"), git(task, "rev-parse", "HEAD")) == heads
    assert (job / "src/main.py").read_text() == "edited\n"


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
    draft = (lane / plan).read_text().replace("**Status:** Approved", "**Status:** Draft", 1)
    approve(root, commit(lane, plan, draft), name=LANE)
    assert run(root, "merge", str(lane)).returncode == 0
    moved = run(root, "merge", str(rc))
    assert moved.returncode == 1 and "moved past" in moved.stderr
    assert fixes(moved) == [f"fix: dadaia worktree sync {rc}"]
    assert run(root, "sync", str(rc)).returncode == 0
    landed = run(root, "merge", str(rc))
    assert landed.returncode == 0, landed.stderr
