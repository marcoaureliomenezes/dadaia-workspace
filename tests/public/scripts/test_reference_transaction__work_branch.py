"""The ``reference-transaction`` hook on real git, work-branch side.

The shipped script is copied into a tmp repo with a bare origin, under a workspace-shaped
``.dadaia/.venv/bin/dadaia`` the hook resolves as in production. That runner executes this
tree's real ``ci ref-gate-check``; a second one exits non-zero, as a venv older than the hook.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import os
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import dadaia_workspace

pytestmark = pytest.mark.medium

_SCRIPT = Path(dadaia_workspace.__file__).parent / "public" / "scripts" / "reference-transaction.sh"
_SOURCE = Path(dadaia_workspace.__file__).parent.parent
_WORK = "feature/0.5.0"
_REAL = f"""#!/bin/sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={shlex.quote(str(_SOURCE))} exec {shlex.quote(sys.executable)} -m dadaia_workspace "$@"
"""


class _Repo:
    def __init__(self, root: Path) -> None:
        self.root = root / "ws" / "repo"
        self.origin = root / "origin.git"
        self.runner = root / "ws" / ".dadaia" / ".venv" / "bin" / "dadaia"

    def install_runner(self, text: str) -> None:
        self.runner.parent.mkdir(parents=True, exist_ok=True)
        self.runner.write_text(text, encoding="utf-8")
        self.runner.chmod(self.runner.stat().st_mode | stat.S_IXUSR)

    def git(
        self, *args: str, cwd: Path | None = None, wt: bool = False
    ) -> subprocess.CompletedProcess[str]:
        env = {k: v for k, v in os.environ.items() if k != "DADAIA_WT"}
        if wt:
            env["DADAIA_WT"] = "1"
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
    r.install_runner(_REAL)
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
    assert "[ref-gate] BLOCKED" in done.stderr
    fixes = [ln for ln in done.stderr.splitlines() if "fix:" in ln]
    assert len(fixes) == 1, done.stderr
    argv = shlex.split(fixes[0].split("fix:", 1)[1])
    assert argv[:4] == [str(r.runner), "worktree", "new", "repo"], fixes[0]
    # `--help` forwards to the installed script: the line's launcher and verb resolve.
    assert subprocess.run([*argv, "--help"], capture_output=True, check=False).returncode == 0
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


def test_a_marked_ff_merge_of_a_wt_branch_into_the_work_branch_passes(repo: _Repo) -> None:
    other = _other_ahead(repo)
    done = repo.git("merge", "-q", "--ff-only", other, wt=True)
    assert done.returncode == 0, done.stderr
    assert repo.ok("rev-parse", f"refs/heads/{_WORK}") == other


def test_an_audit_only_commit_on_the_work_branch_passes(repo: _Repo) -> None:
    audit = repo.root / "specs" / "audits"
    audit.mkdir(parents=True)
    (audit / "2026-10-14.md").write_text("finding\n", encoding="utf-8")
    repo.ok("add", "-A")
    done = repo.git("commit", "-q", "-m", "audit")
    assert done.returncode == 0, done.stderr


@pytest.mark.parametrize("code", [1, 2])
def test_a_runner_fault_warns_and_lets_the_commit_through(repo: _Repo, code: int) -> None:
    repo.install_runner(f"#!/bin/sh\necho boom >&2\nexit {code}\n")
    done = repo.git("commit", "-q", "--allow-empty", "-m", "on the work branch")
    assert done.returncode == 0, done.stderr
    assert "boom" in done.stderr
    assert "ref gate failed" in done.stderr
