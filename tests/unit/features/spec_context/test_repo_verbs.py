"""FR17 (v0.4.4, T-044-28) — the `SpecContextService` create/add/remove-repo methods.

Intent: CONTRACT — A17.1 (idempotent, fails loudly on unknown context/slug), A17.3
(refuses the main repo's own slug as associated), context-repo-add-accepts-foreign-
context-slug (T-044-45 F-1: refuses a slug already owned by ANOTHER context, as its
main repo or an associated repo) and its `create`-seam mirror
context-create-accepts-slug-owned-by-another-context (S5-FR23 Firing 5 finding: the
same `_foreign_slug_owner` predicate applied at `create`'s own `--repo` slug, the
second registry seam that writes into the shared `repos/<slug>` namespace).
JsonContextStore-driven (SMALL/unit tier): a pure registry-mutation concern, no real
git/disk behavior under test — the CLI-level surface (argument parsing,
on-disk-left-untouched messaging for A17.2) is proven in
``tests/integration/test_cli_context_repo_verbs.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.container import scan_publish_candidates
from dadaia_workspace.core.exceptions import (  # noqa: E402
    AssociatedRepoConflictError,
    AssociatedRepoNotFoundError,
    ContextNotFoundError,
    InvalidContextNameError,
)
from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fakes import register_dead  # noqa: E402
from tests.fixtures.real_git import clone, git, seeded_remote
from tests.fixtures.stores import context_store


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "repos").mkdir()
    return root


@pytest.fixture()
def store(workspace_root: Path) -> JsonContextStore:
    return context_store(workspace_root / ".dadaia" / "states")


@pytest.fixture()
def service(store: JsonContextStore, workspace_root: Path) -> SpecContextService:
    return SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
    )


_URL = "https://github.com/org/assoc-repo"
_ASSOC = AssociatedRepo(slug="assoc-repo", url=_URL)
_OTHER_ASSOC = AssociatedRepo(slug="other-assoc", url="https://github.com/org/other-assoc")


def _save(
    store: JsonContextStore, name: str, slug: str, assoc: tuple[AssociatedRepo, ...] = ()
) -> None:
    store.save(
        SpecContextProject(
            name=name, state=ContextState.DEAD, repo_slug=slug, repo_url=f"https://github.com/org/{slug}",
            created_at="2026-08-23T00:00:00+00:00", associated_repos=assoc,
        )
    )  # fmt: skip


@pytest.fixture()
def seeded(store: JsonContextStore) -> JsonContextStore:
    """`proj` (main `main-repo`) beside `other-proj`, which owns `other-repo` (main) and `other-assoc` (associated)."""
    _save(store, "proj", "main-repo")
    _save(store, "other-proj", "other-repo", (_OTHER_ASSOC,))
    return store


# fmt: off
@pytest.mark.parametrize(("preadd", "context", "slug", "url", "raises", "added", "final"), [
    pytest.param(False, "proj", "assoc-repo", _URL, None, True, (_ASSOC,), id="A17.1-new-slug-registered-and-persisted"),
    pytest.param(True, "proj", "assoc-repo", _URL, None, False, (_ASSOC,), id="A17.1-same-slug-same-url-idempotent-beside-a-foreign-context"),
    pytest.param(True, "proj", "assoc-repo", _URL + "-renamed", AssociatedRepoConflictError, None, (_ASSOC,), id="A17.1-same-slug-other-url-refused-untouched"),
    pytest.param(False, "proj", "main-repo", _URL, AssociatedRepoConflictError, None, (), id="A17.3-own-main-slug-refused"),
    pytest.param(False, "nope", "assoc-repo", _URL, ContextNotFoundError, None, (), id="A17.1-unknown-context"),
    pytest.param(False, "proj", "other-repo", _URL, AssociatedRepoConflictError, None, (), id="F-1-slug-owned-by-another-context-as-main"),
    pytest.param(False, "proj", "other-assoc", _URL, AssociatedRepoConflictError, None, (), id="F-1-slug-owned-by-another-context-as-associated"),
    pytest.param(False, "proj", "brand-new", "u", None, True, (AssociatedRepo(slug="brand-new", url="u"),), id="F-1-unowned-slug-still-accepted"),
    pytest.param(False, "proj", "../escape", "", InvalidContextNameError, None, (), id="allowlist-refuses-a-path-slug"),
])
# fmt: on
def test_add_repo_refuses_slug_owned_by_another_context_as_main_repo(
    service: SpecContextService, seeded: JsonContextStore, preadd: bool, context: str, slug: str, url: str,
    raises: type[Exception] | None, added: bool | None, final: tuple[AssociatedRepo, ...],
) -> None:  # fmt: skip
    """A17.1/A17.3; context-repo-add-accepts-foreign-context-slug (T-044-45 F-1): one predicate over
    every context's main AND associated slugs refuses a slug another context owns — a foreign slug
    would arm that context's `dead()` to rmtree this one's tree; its own slug stays an idempotent no-op."""
    if preadd:
        service.add_repo("proj", "assoc-repo", _URL)
    if raises:
        with pytest.raises(raises, match="other-proj" if slug.startswith("other") else None):
            service.add_repo(context, slug, url)
    else:
        assert service.add_repo(context, slug, url)[1] is added
    stored = seeded.get("proj")
    assert stored is not None and stored.associated_repos == final


_OWN = (AssociatedRepo(slug="main-repo", url="u"),)
_TWICE = (AssociatedRepo(slug="infra", url="u"), AssociatedRepo(slug="infra", url="u"))
_INFRA = (AssociatedRepo(slug="infra", url="https://github.com/org/infra"),)


# fmt: off
@pytest.mark.parametrize(("name", "slug", "assoc", "raises", "match"), [
    pytest.param("new-proj", "other-repo", (), AssociatedRepoConflictError, "other-proj", id="slug-owned-by-another-context-as-main"),
    pytest.param("new-proj", "other-assoc", (), AssociatedRepoConflictError, "other-proj", id="slug-owned-by-another-context-as-associated"),
    pytest.param("meu projeto", "ok", (), InvalidContextNameError, "letters, digits", id="allowlist-name-with-space"),
    pytest.param("projeto-café", "ok", (), InvalidContextNameError, "letters, digits", id="allowlist-name-non-ascii"),
    pytest.param("ok", "../escape", (), InvalidContextNameError, "letters, digits", id="allowlist-slug-escape"),
    pytest.param("ok", "a/b", (), InvalidContextNameError, "letters, digits", id="allowlist-slug-with-slash"),
    pytest.param("new-proj", "main-repo", _OWN, AssociatedRepoConflictError, "own main repo", id="A17.3-associated-equals-main"),
    pytest.param("new-proj", "main-repo", _TWICE, AssociatedRepoConflictError, "more than once", id="A17.3-associated-given-twice"),
    pytest.param("new-proj", "brand-new-repo", (), None, None, id="unowned-slug-accepted"),
    pytest.param("new-proj", "main-2", _INFRA, None, None, id="associated-repos-in-the-same-guarded-write"),
])
# fmt: on
def test_create_refuses_a_name_or_slug_outside_the_allowlist(
    service: SpecContextService, store: JsonContextStore, name: str, slug: str,
    assoc: tuple[AssociatedRepo, ...], raises: type[Exception] | None, match: str | None,
) -> None:  # fmt: skip
    """import-registers-unvalidated-slugs-that-doctor-fix-inv5-rmtrees and
    context-create-accepts-slug-owned-by-another-context: `SpecContextService.register`, the ONE seam
    every registry insert goes through, owns the allowlist, A17.3 and the foreign-slug predicate."""
    _save(store, "other-proj", "other-repo", (_OTHER_ASSOC,))
    if raises:
        with pytest.raises(raises, match=match):
            register_dead(service, name, slug, "https://github.com/org/x", associated_repos=assoc)
        assert store.get(name) is None
    else:
        ctx = register_dead(service, name, slug, "https://github.com/org/x", associated_repos=assoc)
        assert (ctx.repo_slug, ctx.associated_repos) == (slug, assoc)
        assert store.get(name) == ctx


# fmt: off
@pytest.mark.parametrize(("context", "slug", "removes", "raises", "left"), [
    pytest.param("proj", "assoc-repo", 1, None, (), id="removes-the-registered-repo"),
    pytest.param("proj", "assoc-repo", 2, AssociatedRepoNotFoundError, (), id="A17.1-second-remove-fails-loudly"),
    pytest.param("proj", "never-registered", 1, AssociatedRepoNotFoundError, (_ASSOC,), id="unknown-slug"),
    pytest.param("nope", "assoc-repo", 1, ContextNotFoundError, (_ASSOC,), id="unknown-context"),
])
# fmt: on
def test_remove_repo_converges_to_not_registered(
    service: SpecContextService, seeded: JsonContextStore, context: str, slug: str, removes: int,
    raises: type[Exception] | None, left: tuple[AssociatedRepo, ...],
) -> None:  # fmt: skip
    service.add_repo("proj", "assoc-repo", _URL)
    for _ in range(removes - 1):
        service.remove_repo(context, slug)
    if raises:
        with pytest.raises(raises):
            service.remove_repo(context, slug)
    else:
        assert service.remove_repo(context, slug).associated_repos == ()
    stored = seeded.get("proj")
    assert stored is not None and stored.associated_repos == left


def test_remove_repo_never_touches_git(
    service: SpecContextService, seeded: JsonContextStore, workspace_root: Path
) -> None:
    """A17.2 (service layer half): removing a registry entry leaves the checkout and history as they were."""
    remote = seeded_remote(workspace_root.parent, "assoc-repo")
    repo = clone(remote, workspace_root / "repos" / "assoc-repo")
    head = git(repo, "rev-parse", "HEAD")
    service.add_repo("proj", "assoc-repo", remote.as_uri())
    service.remove_repo("proj", "assoc-repo")
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == ""
