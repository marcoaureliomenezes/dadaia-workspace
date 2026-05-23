"""Unit tests for SpecContextService — Bug 3 (T-BCR-04).

Bug 3: shutil.rmtree fails with PermissionError on root-owned files.
Fix: detect non-writable files before rmtree and raise GitSyncError with
     a descriptive message suggesting 'sudo chown'.
"""

import stat
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import GitSyncError
from dadaia_workspace.features.spec_context.service import SpecContextService
from tests.fakes import FakeContextStore, FakeGitClient, FakePrimaryContextStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "repos").mkdir()
    return root


@pytest.fixture()
def store() -> FakeContextStore:
    return FakeContextStore()


@pytest.fixture()
def primary() -> FakePrimaryContextStore:
    return FakePrimaryContextStore()


@pytest.fixture()
def git() -> FakeGitClient:
    return FakeGitClient()


@pytest.fixture()
def service(
    store: FakeContextStore,
    primary: FakePrimaryContextStore,
    git: FakeGitClient,
    workspace_root: Path,
) -> SpecContextService:
    return SpecContextService(
        context_store=store,
        primary_store=primary,
        git_client=git,
        workspace_root=workspace_root,
    )


# ---------------------------------------------------------------------------
# Bug 3 — shutil.rmtree must not swallow PermissionError silently
# ---------------------------------------------------------------------------


def test_deactivate_raises_gitsyncerror_on_non_writable_files(
    service: SpecContextService,
    store: FakeContextStore,
    git: FakeGitClient,
    workspace_root: Path,
) -> None:
    """When the repo directory contains non-writable files, deactivate must raise
    GitSyncError with an actionable message instead of allowing PermissionError
    to propagate unhandled.
    """
    # Bootstrap: create a second context so proj is not primary
    (workspace_root / "repos" / "r2").mkdir(parents=True)
    service.create("other", "r2", "https://github.com/org/r2")
    service.activate("other")

    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.activate("proj")
    assert not service.show("proj").is_primary

    repo = workspace_root / "repos" / "my-repo"
    assert repo.exists()

    # Create a file inside the repo then make it non-writable
    locked_file = repo / "locked.txt"
    locked_file.write_text("content")
    locked_file.chmod(stat.S_IRUSR | stat.S_IRGRP)  # read-only

    try:
        with pytest.raises(GitSyncError) as exc_info:
            service.deactivate("proj")

        msg = str(exc_info.value)
        assert "non-writable" in msg.lower() or "chown" in msg.lower(), (
            f"Error message must be actionable. Got: {msg!r}"
        )
        assert str(repo) in msg or "locked.txt" in msg
    finally:
        # Restore permissions so tmp_path cleanup can proceed
        locked_file.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)


def test_deactivate_succeeds_when_all_files_are_writable(
    service: SpecContextService,
    workspace_root: Path,
    git: FakeGitClient,
) -> None:
    """Baseline: deactivate must still succeed (remove repo dir) when all files
    are writable — the permission check must not block normal operation.
    """
    (workspace_root / "repos" / "r2").mkdir(parents=True)
    service.create("other", "r2", "https://github.com/org/r2")
    service.activate("other")

    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.activate("proj")
    assert not service.show("proj").is_primary

    repo = workspace_root / "repos" / "my-repo"
    # Place a writable file — must not impede rmtree
    (repo / "writable.txt").write_text("data")

    service.deactivate("proj")
    assert not repo.exists()
