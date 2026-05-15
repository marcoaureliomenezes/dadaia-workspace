"""Unit tests for SpecContextService."""

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
)
from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.features.spec_context.service import SpecContextService
from tests.fakes import FakeContextStore, FakeGitClient, FakePrimaryContextStore


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


# ------------------------------------------------------------------ create


def test_create_stores_context(service: SpecContextService, store: FakeContextStore) -> None:
    ctx = service.create("proj", "my-repo", "https://github.com/org/my-repo")
    assert store.get("proj") is not None
    assert ctx.state == ContextState.INATIVO
    assert ctx.is_primary is False
    assert ctx.repo_slug == "my-repo"


def test_create_duplicate_raises(service: SpecContextService) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    with pytest.raises(ContextAlreadyExistsError):
        service.create("proj", "other", "https://github.com/org/other")


# ------------------------------------------------------------------ activate


def test_activate_clones_if_absent(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.activate("proj")
    assert len(git.cloned) == 1
    assert git.cloned[0][0] == "https://github.com/org/my-repo"


def test_activate_no_clone_if_repo_present(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    (workspace_root / "repos" / "my-repo").mkdir(parents=True)
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.activate("proj")
    assert len(git.cloned) == 0


def test_activate_auto_promotes_first(
    service: SpecContextService, primary: FakePrimaryContextStore
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    ctx = service.activate("proj")
    assert ctx.is_primary is True
    assert primary.read() is not None
    assert primary.read()["name"] == "proj"  # type: ignore[index]


def test_activate_no_auto_promote_if_primary_exists(
    service: SpecContextService, primary: FakePrimaryContextStore, workspace_root: Path
) -> None:
    (workspace_root / "repos" / "r1").mkdir(parents=True)
    (workspace_root / "repos" / "r2").mkdir(parents=True)
    service.create("p1", "r1", "https://github.com/org/r1")
    service.create("p2", "r2", "https://github.com/org/r2")
    service.activate("p1")
    service.activate("p2")
    assert service.show("p1").is_primary is True
    assert service.show("p2").is_primary is False


def test_activate_not_found_raises(service: SpecContextService) -> None:
    with pytest.raises(ContextNotFoundError):
        service.activate("ghost")


# ------------------------------------------------------------------ deactivate


def test_deactivate_removes_repo_and_marks_inativo(
    service: SpecContextService, workspace_root: Path, git: FakeGitClient
) -> None:
    # Create a second ctx to be primary so we can deactivate the first
    (workspace_root / "repos" / "r2").mkdir(parents=True)
    service.create("other", "r2", "https://github.com/org/r2")
    service.activate("other")  # auto-promote
    # Now promote other so we can deactivate proj
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    ctx = service.activate("proj")
    # proj is NOT primary (other already was primary); safe to deactivate
    assert ctx.is_primary is False
    repo = workspace_root / "repos" / "my-repo"
    assert repo.exists()
    service.deactivate("proj")
    assert not repo.exists()
    assert service.show("proj").state == ContextState.INATIVO


def test_deactivate_primary_raises(service: SpecContextService, workspace_root: Path) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.activate("proj")
    with pytest.raises(ContextStateError, match="primary"):
        service.deactivate("proj")


def test_deactivate_inativo_raises(service: SpecContextService) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    with pytest.raises(ContextStateError):
        service.deactivate("proj")


# ------------------------------------------------------------------ promote


def test_promote_sets_is_primary(
    service: SpecContextService, primary: FakePrimaryContextStore, workspace_root: Path
) -> None:
    (workspace_root / "repos" / "r1").mkdir(parents=True)
    (workspace_root / "repos" / "r2").mkdir(parents=True)
    service.create("p1", "r1", "https://github.com/org/r1")
    service.create("p2", "r2", "https://github.com/org/r2")
    service.activate("p1")  # p1 auto-promoted
    service.activate("p2")  # p2 not promoted
    service.promote("p2")
    assert service.show("p1").is_primary is False
    assert service.show("p2").is_primary is True
    assert primary.read()["name"] == "p2"  # type: ignore[index]


def test_promote_inativo_raises(service: SpecContextService) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    with pytest.raises(ContextStateError):
        service.promote("proj")


def test_promote_not_found_raises(service: SpecContextService) -> None:
    with pytest.raises(ContextNotFoundError):
        service.promote("ghost")


def test_promote_already_primary_is_idempotent(
    service: SpecContextService, workspace_root: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.activate("proj")  # auto-promotes
    ctx = service.promote("proj")  # already primary — should return same ctx
    assert ctx.is_primary is True


# ------------------------------------------------------------------ delete


def test_delete_removes_inativo_context(
    service: SpecContextService, store: FakeContextStore
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.delete("proj")
    assert store.get("proj") is None


def test_delete_not_found_raises(service: SpecContextService) -> None:
    with pytest.raises(ContextNotFoundError):
        service.delete("ghost")


def test_delete_ativo_context_raises(service: SpecContextService, workspace_root: Path) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.activate("proj")
    with pytest.raises(ContextStateError):
        service.delete("proj")


# ------------------------------------------------------------------ deactivate edge cases


def test_deactivate_syncs_dirty_repo(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    (workspace_root / "repos" / "r2").mkdir(parents=True)
    service.create("other", "r2", "https://github.com/org/r2")
    service.activate("other")
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.activate("proj")
    assert service.show("proj").is_primary is False
    repo = workspace_root / "repos" / "my-repo"
    git._dirty.add(repo)
    service.deactivate("proj")
    assert repo in git.committed


def test_deactivate_pushes_when_remote_present(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    (workspace_root / "repos" / "r2").mkdir(parents=True)
    service.create("other", "r2", "https://github.com/org/r2")
    service.activate("other")
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.activate("proj")
    assert service.show("proj").is_primary is False
    repo = workspace_root / "repos" / "my-repo"
    git._has_remote.add(repo)
    service.deactivate("proj")
    assert repo in git.pushed
