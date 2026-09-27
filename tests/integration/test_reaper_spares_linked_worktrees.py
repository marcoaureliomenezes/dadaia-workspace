"""The reaper never destroys a registered linked git worktree.

Intent: CONTRACT — reaper-deletes-linked-git-worktrees. Size: MEDIUM (integration: a real
``git worktree add``; the ``.git``-is-a-file shape and git's own ``prunable`` verdict are
the contract, and no fake reproduces them).

Structural cause pinned: ``sweep.remove``/``sweep.move`` — the one chokepoint every
reaper deletion and slop move passes through — judged only "inside the workspace?".
The TTL walk descends into a worktree and expires it file by file (its ``.git`` file
included), and a slop move relocates it; either orphans git's registration and
destroys uncommitted work.
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


def _assert_intact(repo: Path, worktree: Path) -> None:
    assert (worktree / "uncommitted.txt").read_text(encoding="utf-8") == "work in progress"
    assert (worktree / ".git").is_file()
    assert "prunable" not in _git(repo, "worktree", "list", "--porcelain")


def _fix(root: Path) -> list[str]:
    return DoctorService(
        context_store(root / ".dadaia" / "states"), GitSubprocessClient(), root
    ).fix()


def test_ttl_reaper_never_deletes_an_expired_linked_worktree(tmp_path: Path) -> None:
    repo, worktree = _workspace_with_worktree(tmp_path, ".dadaia/tmp/claude/20200101/wt-a")
    _age_tree(tmp_path / ".dadaia" / "tmp" / "claude")

    _fix(tmp_path)

    _assert_intact(repo, worktree)


def test_slop_mover_never_moves_a_linked_worktree(tmp_path: Path) -> None:
    """A worktree at an unlisted root entry is slop by classification — held, never moved."""
    repo, worktree = _workspace_with_worktree(tmp_path, "scratch/wt-b")

    _fix(tmp_path)

    _assert_intact(repo, worktree)
