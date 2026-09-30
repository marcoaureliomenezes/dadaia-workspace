"""Intent: CONTRACT — reaper-deletes-linked-git-worktrees: `sweep.remove`/`sweep.move`,
the one chokepoint of every reaper deletion and slop move, never touches a registered
linked worktree — an expired one under `.dadaia/tmp/` or one at an unlisted root entry.
Size: MEDIUM — git's own `.git`-file shape and `prunable` verdict are the contract.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.stores import context_store

_TWO_DAYS_AGO = time.time() - 2 * 86_400

pytestmark = pytest.mark.slow(reason="real git init + worktree add subprocesses")


def _git(cwd: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True
    )
    return done.stdout


def _workspace_with_worktree(root: Path, worktree_rel: str) -> tuple[Path, Path]:
    for zone in ("tmp", "states", "sessions", "reaped"):
        (root / ".dadaia" / zone).mkdir(parents=True, exist_ok=True)
    repo = root / "repos" / "lib"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / "f.txt").write_text("f", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-q", "-m", "init")
    worktree = root / worktree_rel
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "-q", "-b", "wt/a", str(worktree))
    (worktree / "uncommitted.txt").write_text("work in progress", encoding="utf-8")
    return repo, worktree


def _age_tree(top: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(top, topdown=False):
        for name in [*filenames, *dirnames]:
            os.utime(Path(dirpath) / name, (_TWO_DAYS_AGO, _TWO_DAYS_AGO))
    os.utime(top, (_TWO_DAYS_AGO, _TWO_DAYS_AGO))


def _fix(root: Path) -> list[str]:
    return DoctorService(
        context_store(root / ".dadaia" / "states"), GitSubprocessClient(), root
    ).fix()


@pytest.mark.parametrize(
    ("worktree_rel", "aged"),
    [(".dadaia/tmp/claude/20200101/wt-a", ".dadaia/tmp/claude"), ("scratch/wt-b", "")],
    ids=["ttl-reaper-expired-worktree", "slop-mover-unlisted-root-entry"],
)
def test_doctor_fix_never_reaps_or_moves_a_linked_worktree(
    tmp_path: Path, worktree_rel: str, aged: str
) -> None:
    repo, worktree = _workspace_with_worktree(tmp_path, worktree_rel)
    if aged:
        _age_tree(tmp_path / aged)

    _fix(tmp_path)

    assert (worktree / "uncommitted.txt").read_text(encoding="utf-8") == "work in progress"
    assert (worktree / ".git").is_file()
    assert "prunable" not in _git(repo, "worktree", "list", "--porcelain")
