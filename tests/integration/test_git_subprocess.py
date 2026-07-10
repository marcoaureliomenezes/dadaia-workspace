"""Integration tests for GitSubprocessClient with real git commands.

Merged per plan-integration.md (11 -> 2): (1) one repo-lifecycle fn: clone -> is_dirty
false/true -> commit_all -> nothing-to-commit noop -> has_remote -> current_branch ->
checkout; (2) error paths (clone invalid, checkout missing). Eleven separate `git init`
fixtures collapse to two.
"""

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


def test_repo_lifecycle_clone_dirty_commit_remote_branch_checkout_and_error_paths(
    tmp_path: Path,
) -> None:
    """One fn walking the full GitSubprocessClient repo lifecycle against real git:
    clone -> is_dirty(false) -> is_dirty(true) -> commit_all -> nothing-to-commit noop
    -> has_remote(false/true) -> current_branch -> checkout. Plus the error paths:
    clone of an invalid URL and checkout of a missing branch."""
    client = GitSubprocessClient()

    src = tmp_path / "src"
    _init_git_repo(src)
    dest = tmp_path / "dest"
    client.clone(str(src), dest)
    assert dest.exists()
    # CI runners have no global git identity — commits in the clone need a local one.
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=dest, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=dest, capture_output=True)

    # is_dirty: clean, then dirty after a modification.
    assert client.is_dirty(dest) is False
    (dest / "README.md").write_text("changed")
    assert client.is_dirty(dest) is True

    # commit_all creates a real commit.
    (dest / "new.txt").write_text("hello")
    client.commit_all(dest, "add new.txt")
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"], cwd=dest, capture_output=True, text=True
    )
    assert "add new.txt" in result.stdout

    # commit_all is a no-op (does not raise) when there is nothing to commit.
    client.commit_all(dest, "empty commit")

    # has_remote: local-only repo is False; a clone of it has a remote.
    local_only = tmp_path / "local-only"
    _init_git_repo(local_only)
    assert client.has_remote(local_only) is False
    assert client.has_remote(dest) is True

    # current_branch + checkout round-trip.
    branch = client.current_branch(dest)
    assert branch in ("main", "master")
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=dest, capture_output=True)
    subprocess.run(["git", "checkout", branch], cwd=dest, capture_output=True)
    orig = client.current_branch(dest)
    client.checkout(dest, "feature")
    assert client.current_branch(dest) == "feature"
    client.checkout(dest, orig)
    assert client.current_branch(dest) == orig

    # Error paths: clone of an invalid URL, checkout of a missing branch.
    error_dest = tmp_path / "error-dest"
    with pytest.raises(GitCloneError):
        client.clone("/no/such/repo", error_dest)

    with pytest.raises(GitSyncError):
        client.checkout(dest, "no-such-branch")
