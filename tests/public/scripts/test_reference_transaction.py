"""The ``reference-transaction`` hook on real git, creation side.

Each test copies the shipped script into a tmp repo's ``.git/hooks`` and drives plain git;
a stub ``dadaia`` at the workspace venv path the hook resolves records every call, so "no
python runner call" is observable.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.core.platform import PLATFORM
from tests.fixtures.harness_env import git_bash, suite_env
from tests.fixtures.stores import fake_venv, own_venv_python
from tests.helpers import oslib
from tests.helpers.oslib import make_executable, read_text, run

pytestmark = pytest.mark.medium

_SCRIPT = Path(dadaia_workspace.__file__).parent / "public" / "scripts" / "reference-transaction.sh"
_EMAIL = "test@example.invalid"


class _Repo:
    def __init__(self, root: Path, ws: str = "ws") -> None:
        self.root = root / ws / "repo"
        self.calls = root / "stub-calls.log"
        self.stub = own_venv_python(root / ws).with_name(f"dadaia{PLATFORM.venv_exe_suffix}")

    def git(
        self, *args: str, cwd: Path | None = None, wt: bool = False
    ) -> subprocess.CompletedProcess[str]:
        env = {k: v for k, v in os.environ.items() if k != "DADAIA_WT"}
        if wt:
            env["DADAIA_WT"] = "1"
        return run(["git", *args], cwd=cwd or self.root, env=env, timeout=60)

    def calls_made(self) -> str:
        return read_text(self.calls) if self.calls.exists() else ""


def _make_repo(tmp_path: Path, ws: str) -> _Repo:
    r = _Repo(tmp_path, ws)
    record = f"import sys\nopen({str(r.calls)!r}, 'a', newline='\\n').write(' '.join(sys.argv[1:]) + '\\n')\n"
    fake_venv(r.root.parent, cli="#!python\n" + record)
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
    make_executable(hook)
    return r


@pytest.fixture
def repo(tmp_path: Path) -> _Repo:
    return _make_repo(tmp_path, "ws")


def _add_tree(r: _Repo, name: str = "x") -> Path:
    tree = r.root.parent / f"tree-{name}"
    done = r.git("worktree", "add", "-q", "-b", f"wt/{name}", str(tree), wt=True)
    assert done.returncode == 0, done.stderr
    return tree


@pytest.mark.parametrize(("ws", "name"), [("ws", "x"), ("ws", "a;b"), ("my ws", "x")])
def test_raw_worktree_add_is_refused_with_one_runnable_fix(
    tmp_path: Path, ws: str, name: str
) -> None:
    repo = _make_repo(tmp_path, ws)
    done = repo.git("worktree", "add", "-q", "-b", f"wt/{name}", str(repo.root.parent / "tree"))
    assert done.returncode != 0
    fixes = [ln for ln in done.stderr.splitlines() if "fix:" in ln]
    assert len(fixes) == 1, done.stderr
    line = oslib.command(str(repo.stub), "worktree", "new", "repo", name)
    assert fixes[0] == f"fix: {line}"
    if not line.startswith("Agent action:"):  # an act is a sentence, not a command to run
        assert oslib.run_line(line).returncode == 0
        assert repo.calls_made() == f"worktree new repo {name}\n"
    assert (
        run(
            ["git", "rev-parse", "--verify", "-q", f"refs/heads/wt/{name}"], cwd=repo.root
        ).returncode
        != 0
    )


def test_raw_worktree_add_without_a_runner_names_the_agent_action(repo: _Repo) -> None:
    repo.stub.unlink()
    done = repo.git("worktree", "add", "-q", "-b", "wt/x", str(repo.root.parent / "tree"))
    assert done.returncode != 0
    fixes = [ln for ln in done.stderr.splitlines() if "fix:" in ln]
    assert len(fixes) == 1, done.stderr
    assert fixes[0].startswith("fix: Agent action: ")


def test_worktree_add_with_the_marker_passes(repo: _Repo) -> None:
    tree = _add_tree(repo)
    assert (tree / ".git").exists()


def test_commit_in_an_existing_wt_tree_passes_without_a_runner_call(repo: _Repo) -> None:
    tree = _add_tree(repo)
    repo.calls.unlink(missing_ok=True)
    done = repo.git("commit", "-q", "--allow-empty", "-m", "work", cwd=tree)
    assert done.returncode == 0, done.stderr
    assert repo.calls_made() == ""


def test_branch_deletion_passes(repo: _Repo) -> None:
    tree = _add_tree(repo)
    assert repo.git("worktree", "remove", "--force", str(tree)).returncode == 0
    done = repo.git("branch", "-D", "wt/x")
    assert done.returncode == 0, done.stderr


def test_wt_clean_path_passes(repo: _Repo) -> None:
    tree = _add_tree(repo)
    assert repo.git("worktree", "remove", "--force", str(tree)).returncode == 0
    assert repo.git("worktree", "prune").returncode == 0
    assert repo.git("branch", "-D", "wt/x").returncode == 0
    assert repo.git("for-each-ref", "refs/heads/wt/").stdout == ""


def test_an_update_to_origins_sha_and_a_non_branch_ref_make_no_runner_call(repo: _Repo) -> None:
    remote = repo.root.parent / "origin.git"
    assert repo.git("init", "-q", "--bare", str(remote)).returncode == 0
    assert repo.git("remote", "add", "origin", str(remote)).returncode == 0
    assert repo.git("push", "-q", "origin", "main").returncode == 0
    assert repo.git("fetch", "-q", "origin").returncode == 0
    assert repo.git("commit", "-q", "--allow-empty", "-m", "ahead").returncode == 0
    ahead = repo.git("rev-parse", "HEAD").stdout.strip()
    base = repo.git("rev-parse", "origin/main").stdout.strip()
    repo.calls.unlink(missing_ok=True)
    assert repo.git("reset", "-q", "--hard", "origin/main").returncode == 0
    assert repo.git("update-ref", "refs/stash", base).returncode == 0
    assert repo.git("update-ref", "refs/stash", ahead, base).returncode == 0
    assert repo.calls_made() == ""


def test_the_marker_passes_every_update_without_a_runner_call(repo: _Repo) -> None:
    done = repo.git("commit", "-q", "--allow-empty", "-m", "marked", wt=True)
    assert done.returncode == 0, done.stderr
    assert repo.calls_made() == ""


def test_unresolvable_runner_warns_and_exits_zero(repo: _Repo) -> None:
    repo.stub.unlink()
    git_dir = str(Path(shutil.which("git") or "git").parent)
    sh_dir = (
        str(Path(git_bash()).parents[1] / "usr" / "bin") if PLATFORM.windows else ""
    )  # git spawns its hook through `sh`
    path = os.pathsep.join(filter(None, [git_dir, sh_dir, os.defpath]))
    env = suite_env(os.environ, repo.root, overrides={"PATH": path})
    done = run(
        ["git", "commit", "-q", "--allow-empty", "-m", "on main"],
        cwd=repo.root,
        env=env,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    assert "could not locate the dadaia runner" in done.stderr, done.stderr


def _no_venv(repo: _Repo) -> None:
    shutil.rmtree(repo.root.parent / ".dadaia")


def test_a_firing_other_than_prepared_decides_nothing(repo: _Repo) -> None:
    """git fires the hook again as `committed`; the shim leaves before it looks for a venv."""
    _no_venv(repo)
    hook = repo.root / ".git" / "hooks" / "reference-transaction"
    env = suite_env(os.environ, repo.root)
    done = run([git_bash(), str(hook), "committed"], cwd=repo.root, input="", env=env, timeout=60)
    assert (done.returncode, done.stderr) == (0, "")


def test_with_no_venv_at_all_the_shim_warns_and_passes(repo: _Repo) -> None:
    _no_venv(repo)
    done = repo.git("commit", "-q", "--allow-empty", "-m", "no venv")
    assert done.returncode == 0, done.stderr
    assert "could not locate the dadaia runner" in done.stderr, done.stderr


def test_the_repos_own_venv_is_the_last_resort(repo: _Repo) -> None:
    """No workspace venv above the repo: the hook runs from the repo's own `.venv`."""
    _no_venv(repo)
    fake_venv(repo.root.parent / "own")
    shutil.move(repo.root.parent / "own" / ".dadaia" / ".venv", repo.root / ".venv")
    done = repo.git("worktree", "add", "-q", "-b", "wt/x", str(repo.root.parent / "tree"))
    assert done.returncode != 0
    assert "[ref-gate] BLOCKED refs/heads/wt/x" in done.stderr, done.stderr


def test_a_venv_without_the_package_is_a_runner_fault_and_passes(repo: _Repo) -> None:
    """A half-installed workspace (the interpreter cannot import the hook) must not brick git."""
    env = suite_env(os.environ, repo.root, unset=("PYTHONPATH",))
    done = run(
        ["git", "commit", "-q", "--allow-empty", "-m", "x"], cwd=repo.root, env=env, timeout=60
    )
    assert done.returncode == 0, done.stderr
    assert "update allowed" in done.stderr, done.stderr
