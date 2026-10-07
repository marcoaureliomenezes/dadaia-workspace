"""GitSubprocessClient against real git.

Bug 4 (first push sets
upstream, a mismatched upstream pushes by explicit refspec, v0.1.50 FR3); v0.4.3 A10.2
(commit_paths ignores pre-staged content); SA-H3-2 (the operator's own identity, never a
fallback); review 6 N2 (a failed step carries git's stdout).
"""

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.conftest import _GIT_QUIET

pytestmark = pytest.mark.slow


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _repo(path: Path) -> Path:
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "op@example.com")
    _git(path, "config", "user.name", "Operator")
    (path / "README.md").write_text("init")
    _git(path, "add", "-A")
    _git(path, "commit", "-qm", "init")
    return path


def test_repo_lifecycle_clone_dirty_commit_remote_branch_checkout_and_error_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """clone -> dirty_paths (a rename once, by its new path; an untracked file) -> has_remote
    -> current_branch/checkout; an invalid clone and a missing branch raise."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(_GIT_QUIET))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    client = GitSubprocessClient()
    src = _repo(tmp_path / "src")
    dest = tmp_path / "dest"
    client.clone(str(src), dest)

    assert client.dirty_paths(dest) == []
    (dest / "new.txt").write_text("hello")
    _git(dest, "mv", "README.md", "R.md")
    assert client.dirty_paths(dest) == ["R.md", "new.txt"]
    _git(dest, "reset", "-q", "--hard")
    (dest / "new.txt").unlink()

    assert (client.has_remote(src), client.has_remote(dest)) == (False, True)
    branch = client.current_branch(dest)
    _git(dest, "branch", "feature")
    client.checkout(dest, "feature")
    assert client.current_branch(dest) == "feature"
    client.checkout(dest, branch)
    assert client.current_branch(dest) == branch

    with pytest.raises(GitCloneError):
        client.clone("/no/such/repo", tmp_path / "error-dest")
    with pytest.raises(GitSyncError):
        client.checkout(dest, "no-such-branch")


def test_a_failed_git_step_carries_gits_full_output(tmp_path: Path) -> None:
    """Review 6 N2: git writes CONFLICT to stdout — the error carries it."""
    repo = _repo(tmp_path / "r")
    client = GitSubprocessClient()
    client.git(repo, "checkout", "-q", "-b", "b")
    (repo / "README.md").write_text("b")
    client.git(repo, "commit", "-qam", "b")
    client.git(repo, "checkout", "-q", "-")
    (repo / "README.md").write_text("c")
    client.git(repo, "commit", "-qam", "c")
    with pytest.raises(GitSyncError, match="CONFLICT"):
        client.git(repo, "merge", "b")


def test_push_first_push_sets_upstream_and_mismatched_branch_uses_explicit_refspec(
    tmp_path: Path,
) -> None:
    """Bug 4 / v0.1.50 FR3: plain ``git push`` fails under push.default=simple when the
    upstream name differs; the client pushes HEAD:<upstream branch> instead."""
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    local = _repo(tmp_path / "local")
    _git(local, "remote", "add", "origin", str(bare))
    client = GitSubprocessClient()

    client.push(local)
    assert _git(local, "rev-parse", "--abbrev-ref", "@{u}").returncode == 0

    _git(local, "push", "-q", "origin", "HEAD:refs/heads/main")
    _git(local, "checkout", "-q", "-b", "work")
    _git(local, "branch", "--set-upstream-to=origin/main", "work")
    _git(local, "config", "push.default", "simple")
    _git(local, "commit", "-q", "--allow-empty", "-m", "next")
    client.push(local)

    assert _git(bare, "rev-parse", "main").stdout == _git(local, "rev-parse", "HEAD").stdout


def test_commit_paths_ignores_operator_pre_staged_unrelated_content(tmp_path: Path) -> None:
    """A10.2: the commit is path-scoped; the operator's staged file stays staged."""
    repo = _repo(tmp_path / "repo")
    (repo / "operator-staged.txt").write_text("operator content")
    _git(repo, "add", "operator-staged.txt")
    (repo / "tool-written.txt").write_text("tool content")

    GitSubprocessClient().commit_paths(repo, "chore(scaffold): tool write", ["tool-written.txt"])

    assert _git(repo, "show", "--name-only", "--format=", "HEAD").stdout == "tool-written.txt\n"
    assert "A  operator-staged.txt" in _git(repo, "status", "--porcelain").stdout


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="context-clone-fails-past-windows-max-path")  # fmt: skip
def test_clone_writes_longpaths_into_the_clone_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows' 260-character limit: the clone's own config carries core.longpaths=true."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(_GIT_QUIET))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    dest = tmp_path / "dest"
    GitSubprocessClient().clone(str(_repo(tmp_path / "src")), dest)

    assert _git(dest, "config", "--get", "core.longpaths").stdout.strip() == "true"
