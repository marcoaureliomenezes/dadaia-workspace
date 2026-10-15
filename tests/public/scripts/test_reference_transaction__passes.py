"""The ``reference-transaction`` hook on real git, the refs it lets through.

Each test copies the shipped script into a tmp repo's ``.git/hooks`` and drives plain git;
a stub ``dadaia`` on PATH records every call, so "no python runner call" is observable.

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
_EMAIL = "test@example.invalid"


class _Repo:
    def __init__(self, root: Path) -> None:
        self.root = root / "repo"
        self.calls = root / "stub-calls.log"
        self.bin = root / "bin"

    def git(
        self, *args: str, cwd: Path | None = None, wt: bool = False
    ) -> subprocess.CompletedProcess[str]:
        env = {k: v for k, v in os.environ.items() if k != "DADAIA_WT"}
        env["PATH"] = f"{self.bin}{os.pathsep}{env['PATH']}"
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

    def calls_made(self) -> str:
        return self.calls.read_text(encoding="utf-8") if self.calls.exists() else ""


@pytest.fixture
def repo(tmp_path: Path) -> _Repo:
    r = _Repo(tmp_path)
    r.bin.mkdir()
    stub = r.bin / "dadaia"
    stub.write_text(f'#!/bin/sh\necho "$@" >> "{r.calls}"\nexit 0\n', encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    r.root.mkdir()
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", _EMAIL],
        ["config", "user.name", "Test"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
    ):
        assert r.git(*args).returncode == 0
    # The hook is installed after the seed commit, as an installer would on an existing repo.
    assert _SCRIPT.is_file(), f"hook script missing: {_SCRIPT}"
    hook = r.root / ".git" / "hooks" / "reference-transaction"
    shutil.copy(_SCRIPT, hook)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    return r


def _add_tree(r: _Repo, name: str = "x") -> Path:
    tree = r.root.parent / f"tree-{name}"
    done = r.git("worktree", "add", "-q", "-b", f"wt/{name}", str(tree), wt=True)
    assert done.returncode == 0, done.stderr
    return tree


def test_commit_in_an_existing_wt_tree_passes_without_a_runner_call(repo: _Repo) -> None:
    tree = _add_tree(repo)
    repo.calls.unlink(missing_ok=True)
    done = repo.git("commit", "-q", "--allow-empty", "-m", "work", cwd=tree)
    assert done.returncode == 0, done.stderr
    assert repo.calls_made() == ""


def test_creating_the_archive_tag_passes(repo: _Repo) -> None:
    done = repo.git("tag", "archive/wt/x")
    assert done.returncode == 0, done.stderr
    assert repo.git("tag", "--list", "archive/wt/x").stdout.strip() == "archive/wt/x"


def test_creating_a_harness_native_worktree_branch_passes(repo: _Repo) -> None:
    tree = repo.root.parent / "native"
    done = repo.git("worktree", "add", "-q", "-b", "worktree-native", str(tree))
    assert done.returncode == 0, done.stderr
    assert (tree / ".git").exists()
