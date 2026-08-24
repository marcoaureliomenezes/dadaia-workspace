"""FR17 (v0.4.4, T-044-28) — the `SpecContextService` add/remove-repo methods.

Intent: CONTRACT — A17.1 (idempotent, fails loudly on unknown context/slug), A17.3
(refuses the main repo's own slug as associated), context-repo-add-accepts-foreign-
context-slug (T-044-45 F-1: refuses a slug already owned by ANOTHER context, as its
main repo or an associated repo). FakeContextStore-driven (SMALL/unit tier): a pure
registry-mutation concern, no real git/disk behavior under test — the CLI-level
surface (argument parsing, on-disk-left-untouched messaging for A17.2) is proven in
``tests/integration/test_cli_context_repo_verbs.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.core.exceptions import ContextNotFoundError  # noqa: E402
from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import (  # noqa: E402
    AssociatedRepoConflictError,
    AssociatedRepoNotFoundError,
    SpecContextService,
)
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


def _seed(store: FakeContextStore) -> None:
    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.DEAD,
            repo_slug="main-repo",
            repo_url="https://github.com/org/main-repo",
            created_at="2026-08-23T00:00:00+00:00",
        )
    )


def _seed_other(
    store: FakeContextStore,
    name: str,
    repo_slug: str,
    associated_repos: tuple[AssociatedRepo, ...] = (),
) -> None:
    store.save(
        SpecContextProject(
            name=name,
            state=ContextState.DEAD,
            repo_slug=repo_slug,
            repo_url=f"https://github.com/org/{repo_slug}",
            created_at="2026-08-23T00:00:00+00:00",
            associated_repos=associated_repos,
        )
    )


# --------------------------------------------------------------------- add_repo


def test_add_repo_registers_new_associated_repo(
    service: SpecContextService, store: FakeContextStore
) -> None:
    _seed(store)
    ctx, was_added = service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo")
    assert was_added is True
    assert ctx.associated_repos == (
        AssociatedRepo(slug="assoc-repo", url="https://github.com/org/assoc-repo"),
    )
    # Persisted, not just returned.
    stored = store.get("proj")
    assert stored is not None
    assert stored.associated_repos == ctx.associated_repos


def test_add_repo_is_idempotent_same_slug_same_url(
    service: SpecContextService, store: FakeContextStore
) -> None:
    _seed(store)
    service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo")
    ctx2, was_added2 = service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo")
    assert was_added2 is False
    assert len(ctx2.associated_repos) == 1


def test_add_repo_refuses_same_slug_different_url(
    service: SpecContextService, store: FakeContextStore
) -> None:
    _seed(store)
    service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo")
    with pytest.raises(AssociatedRepoConflictError):
        service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo-renamed")
    # Original registration is untouched by the refused attempt.
    stored = store.get("proj")
    assert stored is not None
    assert stored.associated_repos == (
        AssociatedRepo(slug="assoc-repo", url="https://github.com/org/assoc-repo"),
    )


def test_add_repo_refuses_main_repo_slug(
    service: SpecContextService, store: FakeContextStore
) -> None:
    _seed(store)
    with pytest.raises(AssociatedRepoConflictError):
        service.add_repo("proj", "main-repo", "https://github.com/org/main-repo")
    stored = store.get("proj")
    assert stored is not None
    assert stored.associated_repos == ()


def test_add_repo_unknown_context_raises(service: SpecContextService) -> None:
    with pytest.raises(ContextNotFoundError):
        service.add_repo("does-not-exist", "assoc-repo", "https://github.com/org/assoc-repo")


def test_add_repo_refuses_slug_owned_by_another_context_as_main_repo(
    service: SpecContextService, store: FakeContextStore
) -> None:
    """T-044-45 F-1 / bug context-repo-add-accepts-foreign-context-slug: `add_repo`
    refused only ``slug == ctx.repo_slug`` (this context's own main slug) — a slug
    that is ANOTHER context's main repo slug sailed through, arming that other
    context's `dead()` to commit/push/rmtree a foreign working tree the moment this
    context is later made dead. Same repro shape as the review's own reproduction
    (throwaway store, two contexts, `add_repo(ctx-a, slug=ctx-b's main slug)`)."""
    _seed(store)
    _seed_other(store, "other-proj", "other-repo")

    with pytest.raises(AssociatedRepoConflictError, match="other-proj"):
        service.add_repo("proj", "other-repo", "https://github.com/org/other-repo")

    # Refused cleanly: nothing was registered on either context.
    stored = store.get("proj")
    assert stored is not None
    assert stored.associated_repos == ()


def test_add_repo_refuses_slug_owned_by_another_context_as_associated_repo(
    service: SpecContextService, store: FakeContextStore
) -> None:
    """Same class (T-044-45 F-1), the other ownership shape: the slug is already
    registered as an ASSOCIATED repo of another context, not that context's main
    repo. The review's fix direction is one predicate consulting `store.list_all()`
    against both `repo_slug` AND `associated_repos` — this pins the second half."""
    _seed(store)
    _seed_other(
        store,
        "other-proj",
        "other-main",
        associated_repos=(
            AssociatedRepo(slug="other-assoc", url="https://github.com/org/other-assoc"),
        ),
    )

    with pytest.raises(AssociatedRepoConflictError, match="other-proj"):
        service.add_repo("proj", "other-assoc", "https://github.com/org/other-assoc")

    stored = store.get("proj")
    assert stored is not None
    assert stored.associated_repos == ()


def test_add_repo_same_slug_own_context_stays_idempotent_no_regression(
    service: SpecContextService, store: FakeContextStore
) -> None:
    """No regression on A17.1: the new cross-context predicate must never fire for
    THIS context's own already-registered slug — re-adding it stays the existing
    idempotent no-op (same behavior as
    ``test_add_repo_is_idempotent_same_slug_same_url``, exercised again here
    alongside a foreign context in the registry, to prove the new predicate skips
    ``other.name == name``)."""
    _seed(store)
    _seed_other(store, "other-proj", "other-repo")
    service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo")

    ctx2, was_added2 = service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo")

    assert was_added2 is False
    assert ctx2.associated_repos == (
        AssociatedRepo(slug="assoc-repo", url="https://github.com/org/assoc-repo"),
    )


def test_add_repo_unknown_slug_with_no_owner_is_still_accepted(
    service: SpecContextService, store: FakeContextStore
) -> None:
    """An entirely unowned slug — not this context's main slug, not any other
    context's main or associated slug — is still accepted (the predicate refuses
    ownership conflicts, never slugs in general)."""
    _seed(store)
    _seed_other(store, "other-proj", "other-repo")

    ctx, was_added = service.add_repo("proj", "brand-new-repo", "https://github.com/org/new")

    assert was_added is True
    assert ctx.associated_repos == (
        AssociatedRepo(slug="brand-new-repo", url="https://github.com/org/new"),
    )


# --------------------------------------------------------------------- remove_repo


def test_remove_repo_removes_registered_repo(
    service: SpecContextService, store: FakeContextStore
) -> None:
    _seed(store)
    service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo")
    ctx = service.remove_repo("proj", "assoc-repo")
    assert ctx.associated_repos == ()
    stored = store.get("proj")
    assert stored is not None
    assert stored.associated_repos == ()


def test_remove_repo_never_touches_git(
    service: SpecContextService, store: FakeContextStore, git: FakeGitClient
) -> None:
    """A17.2 (service layer half): removing a registry entry never drives the git
    port — the FakeGitClient records zero clone/commit/push/checkout activity."""
    _seed(store)
    service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo")
    service.remove_repo("proj", "assoc-repo")
    assert git.cloned == []
    assert git.committed == []
    assert git.pushed == []
    assert git.checked_out == []


def test_remove_repo_unknown_slug_raises(
    service: SpecContextService, store: FakeContextStore
) -> None:
    _seed(store)
    with pytest.raises(AssociatedRepoNotFoundError):
        service.remove_repo("proj", "never-registered")


def test_remove_repo_unknown_context_raises(service: SpecContextService) -> None:
    with pytest.raises(ContextNotFoundError):
        service.remove_repo("does-not-exist", "assoc-repo")


def test_remove_repo_second_call_on_same_slug_fails_loudly(
    service: SpecContextService, store: FakeContextStore
) -> None:
    """A17.1 idempotency for `remove`: the operation converges to "not registered" —
    calling it again on the now-absent slug fails loudly, it is not a silent no-op."""
    _seed(store)
    service.add_repo("proj", "assoc-repo", "https://github.com/org/assoc-repo")
    service.remove_repo("proj", "assoc-repo")
    with pytest.raises(AssociatedRepoNotFoundError):
        service.remove_repo("proj", "assoc-repo")
