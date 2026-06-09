"""Unit tests for SpecContextService current ALIVE/DEAD behavior."""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import json  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.core.exceptions import (  # noqa: E402
    ContextAlreadyExistsError,
    ContextLockedError,
    ContextNotFoundError,
    ContextStateError,
)
from dadaia_workspace.core.models.spec_context import ContextState  # noqa: E402
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402


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
def git() -> FakeGitClient:
    return FakeGitClient()


@pytest.fixture()
def service(
    store: FakeContextStore,
    git: FakeGitClient,
    workspace_root: Path,
) -> SpecContextService:
    return SpecContextService(
        context_store=store,
        git_client=git,
        workspace_root=workspace_root,
    )


# ------------------------------------------------------------------ create


def test_create_stores_context(service: SpecContextService, store: FakeContextStore) -> None:
    ctx = service.create("proj", "my-repo", "https://github.com/org/my-repo")
    assert store.get("proj") is not None
    assert ctx.state == ContextState.DEAD
    assert ctx.repo_slug == "my-repo"


def test_create_duplicate_raises(service: SpecContextService) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    with pytest.raises(ContextAlreadyExistsError):
        service.create("proj", "other", "https://github.com/org/other")


# ------------------------------------------------------------------ alive (T-10b)


def test_alive_clones_if_absent(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    assert len(git.cloned) == 1
    assert git.cloned[0][0] == "https://github.com/org/my-repo"


def test_alive_no_clone_if_repo_present(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    (workspace_root / "repos" / "my-repo").mkdir(parents=True)
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    assert len(git.cloned) == 0


def test_alive_sets_alive_state(service: SpecContextService) -> None:
    """AC-T10b-1: alive() sets state=ALIVE, alive_since=<now>, dead_since=null."""
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    ctx = service.alive("proj")
    assert ctx.state == ContextState.ALIVE
    assert ctx.alive_since is not None
    assert ctx.dead_since is None


def test_alive_idempotent_on_already_alive(
    service: SpecContextService, workspace_root: Path
) -> None:
    """AC-T10b-3: alive() on an already-ALIVE context is idempotent (no error)."""
    (workspace_root / "repos" / "my-repo").mkdir(parents=True)
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    # second call must not raise
    ctx = service.alive("proj")
    assert ctx.state == ContextState.ALIVE


def test_alive_not_found_raises(service: SpecContextService) -> None:
    with pytest.raises(ContextNotFoundError):
        service.alive("ghost")


# ------------------------------------------------------------------ dead (T-10b)


def test_dead_removes_repo_and_marks_dead(
    service: SpecContextService, workspace_root: Path, git: FakeGitClient
) -> None:
    """AC-T10b-2: dead() sets state=DEAD, dead_since=<now>."""
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    assert repo.exists()
    ctx = service.dead("proj")
    assert not repo.exists()
    assert ctx.state == ContextState.DEAD
    assert ctx.dead_since is not None


def test_dead_state_error_when_not_alive(service: SpecContextService) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    with pytest.raises(ContextStateError):
        service.dead("proj")


def test_dead_not_found_raises(service: SpecContextService) -> None:
    with pytest.raises(ContextNotFoundError):
        service.dead("ghost")


def test_dead_raises_context_locked_when_impl_lock_held(
    service: SpecContextService, workspace_root: Path
) -> None:
    """v0.1.6: dead() when a LIVE TTL-lease record exists raises ContextLockedError.

    The four-store lock model is retired; a live single-record lease
    (.dadaia/states/ctx_locks/<ctx>.lock.json, fresh heartbeat) is the guard.
    """
    from datetime import UTC
    from datetime import datetime as _datetime

    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")

    # Create a LIVE lease record (fresh heartbeat → is_held True).
    lock_dir = workspace_root / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    now = _datetime.now(tz=UTC).isoformat()
    (lock_dir / "proj.lock.json").write_text(
        json.dumps(
            {
                "context": "proj",
                "release": "v1",
                "session_id": "sess_abc123",
                "mode": "IMPLEMENTATION",
                "acquired_at": now,
                "heartbeat": now,
                "ttl": 1800,
            }
        )
    )

    with pytest.raises(ContextLockedError):
        service.dead("proj")


def test_dead_syncs_dirty_repo(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    git._dirty.add(repo)
    service.dead("proj")
    assert repo in git.committed


def test_dead_pushes_when_remote_present(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    git._has_remote.add(repo)
    service.dead("proj")
    assert repo in git.pushed


# ------------------------------------------------------------------ delete


def test_delete_removes_dead_context(service: SpecContextService, store: FakeContextStore) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.delete("proj")
    assert store.get("proj") is None


def test_delete_not_found_raises(service: SpecContextService) -> None:
    with pytest.raises(ContextNotFoundError):
        service.delete("ghost")


def test_delete_alive_context_raises(service: SpecContextService, workspace_root: Path) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    with pytest.raises(ContextStateError):
        service.delete("proj")
