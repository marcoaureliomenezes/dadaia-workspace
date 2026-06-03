"""Integration tests for GitSubprocessClient with real git commands."""

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _init_git_repo(path: Path, initial_commit: bool = True) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)
    if initial_commit:
        (path / "README.md").write_text("init")
        subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True)


def test_clone_succeeds_from_local_repo(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _init_git_repo(src)
    dest = tmp_path / "dest"
    client = GitSubprocessClient()
    client.clone(str(src), dest)
    assert dest.exists()


def test_clone_raises_on_invalid_url(tmp_path: Path) -> None:
    client = GitSubprocessClient()
    dest = tmp_path / "dest"
    with pytest.raises(GitCloneError):
        client.clone("/no/such/repo", dest)


def test_is_dirty_returns_false_on_clean_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    client = GitSubprocessClient()
    assert client.is_dirty(repo) is False


def test_is_dirty_returns_true_when_file_modified(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "README.md").write_text("changed")
    client = GitSubprocessClient()
    assert client.is_dirty(repo) is True


def test_commit_all_creates_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "new.txt").write_text("hello")
    client = GitSubprocessClient()
    client.commit_all(repo, "add new.txt")
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"], cwd=repo, capture_output=True, text=True
    )
    assert "add new.txt" in result.stdout


def test_commit_all_does_not_raise_on_nothing_to_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    client = GitSubprocessClient()
    client.commit_all(repo, "empty commit")  # nothing to commit → should not raise


def test_has_remote_returns_false_on_local_only_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    client = GitSubprocessClient()
    assert client.has_remote(repo) is False


def test_has_remote_returns_true_when_remote_set(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _init_git_repo(src)
    dest = tmp_path / "dest"
    subprocess.run(["git", "clone", str(src), str(dest)], capture_output=True, check=True)
    client = GitSubprocessClient()
    assert client.has_remote(dest) is True


def test_current_branch_returns_branch_name(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    client = GitSubprocessClient()
    branch = client.current_branch(repo)
    assert branch in ("main", "master")


def test_checkout_switches_branch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, capture_output=True)
    subprocess.run(["git", "checkout", "master"], cwd=repo, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, capture_output=True)
    client = GitSubprocessClient()
    orig = client.current_branch(repo)
    client.checkout(repo, "feature")
    assert client.current_branch(repo) == "feature"
    client.checkout(repo, orig)
    assert client.current_branch(repo) == orig


def test_checkout_raises_on_nonexistent_branch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    client = GitSubprocessClient()
    with pytest.raises(GitSyncError):
        client.checkout(repo, "no-such-branch")
