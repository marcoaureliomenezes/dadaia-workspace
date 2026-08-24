"""FR16 (v0.4.4, T-044-27) — associated_repos survives every reconstruction site.

Intent: CONTRACT — A16.1 (N=0 regression) plus the T-044-26 report's flagged gap:
``alive()``, ``dead()`` and ``update_url()`` each rebuild a ``SpecContextProject`` by
hand; before this task none of the three forwarded ``associated_repos``, so a context
that had gained associated repos would silently lose them on its very next alive()/
dead()/update_url() call. FakeGitClient-driven (SMALL/unit tier): this is a pure
reconstruction/propagation concern, no real git behavior under test — the real-git
clone/commit/push/removal behavior for the associated set is proven in
``tests/integration/test_associated_repos_alive_dead.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
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
    store: FakeContextStore, git: FakeGitClient, workspace_root: Path
) -> SpecContextService:
    return SpecContextService(context_store=store, git_client=git, workspace_root=workspace_root)


def _seed_ctx_with_associated(store: FakeContextStore, workspace_root: Path) -> None:
    (workspace_root / "repos" / "main-repo").mkdir(parents=True, exist_ok=True)
    (workspace_root / "repos" / "assoc-repo").mkdir(parents=True, exist_ok=True)
    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.ALIVE,
            repo_slug="main-repo",
            repo_url="https://github.com/org/main-repo",
            created_at="2026-08-23T00:00:00+00:00",
            alive_since="2026-08-23T00:00:00+00:00",
            associated_repos=(
                AssociatedRepo(slug="assoc-repo", url="https://github.com/org/assoc-repo"),
            ),
        )
    )


def test_alive_reconstruction_preserves_associated_repos(
    service: SpecContextService, store: FakeContextStore, workspace_root: Path
) -> None:
    _seed_ctx_with_associated(store, workspace_root)
    # Already ALIVE: exercises the fast-path AND the ensure-clone loop.
    ctx = service.alive("proj")
    assert ctx.associated_repos == (
        AssociatedRepo(slug="assoc-repo", url="https://github.com/org/assoc-repo"),
    )


def test_dead_reconstruction_preserves_associated_repos(
    service: SpecContextService, store: FakeContextStore, workspace_root: Path
) -> None:
    _seed_ctx_with_associated(store, workspace_root)
    ctx = service.dead("proj")
    assert ctx.state == ContextState.DEAD
    assert ctx.associated_repos == (
        AssociatedRepo(slug="assoc-repo", url="https://github.com/org/assoc-repo"),
    )
    # And a subsequent alive() can still see them to re-clone (proves the store
    # round-trip, not just the return value of dead() itself).
    stored = store.get("proj")
    assert stored is not None
    assert stored.associated_repos == ctx.associated_repos


def test_update_url_reconstruction_preserves_associated_repos(
    service: SpecContextService, store: FakeContextStore, workspace_root: Path
) -> None:
    _seed_ctx_with_associated(store, workspace_root)
    updated = service.update_url("proj", "https://github.com/org/main-repo-renamed")
    assert updated.repo_url == "https://github.com/org/main-repo-renamed"
    assert updated.associated_repos == (
        AssociatedRepo(slug="assoc-repo", url="https://github.com/org/assoc-repo"),
    )


def test_alive_with_zero_associated_repos_behaves_exactly_as_today(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    """A16.1 regression: N=0 — no behavior change to the single-repo path."""
    service.create("proj", "my-repo", "https://github.com/org/my-repo")

    ctx = service.alive("proj")
    assert ctx.state == ContextState.ALIVE
    assert len(git.cloned) == 1
    assert ctx.associated_repos == ()

    ctx2 = service.alive("proj")
    assert ctx2.state == ContextState.ALIVE
    assert len(git.cloned) == 1  # idempotent, no re-clone
