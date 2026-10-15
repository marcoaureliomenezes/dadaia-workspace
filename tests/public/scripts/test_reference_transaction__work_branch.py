"""The ``reference-transaction`` hook on real git, work-branch side.

The shipped script is copied into a tmp repo with a bare origin. The stub ``dadaia`` answers
``ci ref-gate-check`` with the policy "a work ref moves only to origin's sha", so these tests
pin the hook's wiring: stdin passthrough, exit code, and the fix line reaching stderr.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

import dadaia_workspace

pytestmark = pytest.mark.medium

_SCRIPT = Path(dadaia_workspace.__file__).parent / "public" / "scripts" / "reference-transaction.sh"
_WORK = "feature/0.5.0"
_STUB = """#!/bin/sh
case "$*" in *ref-gate-check*) ;; *) exit 0 ;; esac
while read old new ref; do
  case "$ref" in refs/heads/feature/*) ;; *) continue ;; esac
  case "$old" in *[!0]*) ;; *) continue ;; esac
  case "$new" in *[!0]*) ;; *) continue ;; esac
  origin=$(git rev-parse -q --verify "refs/remotes/origin/${ref#refs/heads/}")
  if [ "$new" != "$origin" ]; then
    echo "[ref-gate] BLOCKED $ref" >&2
    echo "fix: dadaia worktree new dadaia-workspace <name>" >&2
    exit 1
  fi
done
exit 0
"""


class _Repo:
    def __init__(self, root: Path) -> None:
        self.root = root / "repo"
        self.origin = root / "origin.git"
        self.bin = root / "bin"

    def git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = {k: v for k, v in os.environ.items() if k != "DADAIA_WT"}
        env["PATH"] = f"{self.bin}{os.pathsep}{env['PATH']}"
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.root,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def ok(self, *args: str, cwd: Path | None = None) -> str:
        done = self.git(*args, cwd=cwd)
        assert done.returncode == 0, done.stderr
        return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> _Repo:
    r = _Repo(tmp_path)
    r.bin.mkdir()
    stub = r.bin / "dadaia"
    stub.write_text(_STUB, encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    r.root.mkdir()
    r.ok("init", "-q", "--bare", str(r.origin), cwd=tmp_path)
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "test@example.invalid"],
        ["config", "user.name", "Test"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
        ["remote", "add", "origin", str(r.origin)],
        ["checkout", "-q", "-b", _WORK],
        ["push", "-q", "-u", "origin", _WORK],
    ):
        r.ok(*args)
    # Installed last, as an installer would on an existing repo.
    assert _SCRIPT.is_file(), f"hook script missing: {_SCRIPT}"
    hook = r.root / ".git" / "hooks" / "reference-transaction"
    shutil.copy(_SCRIPT, hook)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    return r


def _other_ahead(r: _Repo) -> str:
    r.ok("checkout", "-q", "-b", "other")
    r.ok("commit", "-q", "--allow-empty", "-m", "elsewhere")
    sha = r.ok("rev-parse", "HEAD")
    r.ok("checkout", "-q", _WORK)
    return sha


def _assert_refused(r: _Repo, done: subprocess.CompletedProcess[str], before: str) -> None:
    assert done.returncode != 0
    fixes = [ln for ln in done.stderr.splitlines() if "fix:" in ln]
    assert len(fixes) == 1, done.stderr
    assert "dadaia worktree " in fixes[0], fixes[0]
    assert r.ok("rev-parse", f"refs/heads/{_WORK}") == before


def test_raw_commit_on_the_work_branch_is_refused(repo: _Repo) -> None:
    before = repo.ok("rev-parse", "HEAD")
    done = repo.git("commit", "-q", "--allow-empty", "-m", "raw")
    _assert_refused(repo, done, before)


def test_raw_ff_merge_on_the_work_branch_is_refused(repo: _Repo) -> None:
    before = repo.ok("rev-parse", "HEAD")
    other = _other_ahead(repo)
    done = repo.git("merge", "--ff-only", other)
    _assert_refused(repo, done, before)


def test_raw_hard_reset_on_the_work_branch_is_refused(repo: _Repo) -> None:
    before = repo.ok("rev-parse", "HEAD")
    other = _other_ahead(repo)
    done = repo.git("reset", "--hard", other)
    _assert_refused(repo, done, before)


def test_pull_ff_only_from_origin_passes(repo: _Repo, tmp_path: Path) -> None:
    peer = tmp_path / "peer"
    repo.ok("clone", "-q", "-b", _WORK, str(repo.origin), str(peer), cwd=tmp_path)
    for args in (
        ["config", "user.email", "test@example.invalid"],
        ["config", "user.name", "Test"],
        ["commit", "-q", "--allow-empty", "-m", "from peer"],
        ["push", "-q", "origin", _WORK],
    ):
        repo.ok(*args, cwd=peer)
    pushed = repo.ok("rev-parse", "HEAD", cwd=peer)
    done = repo.git("pull", "-q", "--ff-only")
    assert done.returncode == 0, done.stderr
    assert repo.ok("rev-parse", f"refs/heads/{_WORK}") == pushed
    assert repo.ok("rev-parse", f"refs/remotes/origin/{_WORK}") == pushed


def test_branch_rename_passes(repo: _Repo) -> None:
    done = repo.git("branch", "-m", _WORK, "feature/0.5.1")
    assert done.returncode == 0, done.stderr
