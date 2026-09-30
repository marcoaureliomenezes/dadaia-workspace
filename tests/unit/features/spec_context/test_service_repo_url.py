"""Unit tests for the repo_url lifecycle (T-011-08 / FR-W2-03, ADR-7).

Covers:
- ``create`` persists an explicit repo_url and refuses an empty one with no checkout.
- ``alive``/``dead`` back-fill repo_url from ``git remote get-url origin`` when the record
  URL is empty and the repo is on disk — exercised against a REAL ``GitSubprocessClient``
  with a local ``file://`` fixture remote as origin (per AC-W2-03).

CRITICAL last-chance capture: alive()/dead() back-filling repo_url — dead() specifically
BEFORE rmtree — are the data-loss guards this file exists to keep.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fcntl")

from pathlib import Path  # noqa: E402

from dadaia_workspace.container import scan_publish_candidates
from dadaia_workspace.core.exceptions import RepoUrlMissingError  # noqa: E402
from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient  # noqa: E402
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
def fake_service(store: JsonContextStore, workspace_root: Path) -> SpecContextService:
    return SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
    )


# ---------------------------------------------------------------------------
# create — explicit and empty repo_url
# ---------------------------------------------------------------------------


def test_create_persists_a_url_and_admits_an_empty_one_only_over_a_checkout(
    fake_service: SpecContextService, store: JsonContextStore, workspace_root: Path
) -> None:
    """Bug context-create-admits-uncloneable-empty-url: a repo with no URL and no
    ``repos/<slug>`` checkout is refused before any write — ``alive`` could only run
    ``git clone ''``; over an existing checkout the empty URL stays (alive back-fills)."""
    ctx = register_dead(fake_service, "foo", "foo", "https://example.test/foo.git")
    assert ctx.repo_url == "https://example.test/foo.git"
    assert store.get("foo").repo_url == "https://example.test/foo.git"  # type: ignore[union-attr]

    with pytest.raises(RepoUrlMissingError, match="repos/bar"):
        register_dead(fake_service, "bar", "bar", "")
    with pytest.raises(RepoUrlMissingError, match="repos/side"):
        fake_service.add_repo("foo", "side")
    assert store.get("bar") is None
    assert store.get("foo").associated_repos == ()  # type: ignore[union-attr]

    git(workspace_root, "init", "-q", str(workspace_root / "repos" / "bar"))
    assert register_dead(fake_service, "bar", "bar", "").repo_url == ""


@pytest.mark.parametrize("verb", ["alive", "dead"])
def test_alive_and_dead_backfill_an_empty_repo_url_from_origin(
    fake_service: SpecContextService, store: JsonContextStore, workspace_root: Path, verb: str
) -> None:
    """CRITICAL last-chance capture (ADR-7, AC-W2-03): an empty record URL is back-filled from the
    on-disk ``origin`` — dead() BEFORE its hold removes the checkout — over a real ``file://`` remote."""
    remote = seeded_remote(workspace_root.parent, "foo")
    repo = clone(remote, workspace_root / "repos" / "foo")
    if verb == "alive":
        register_dead(fake_service, "foo", "foo", "")
    else:
        store.save(SpecContextProject(name="foo", state=ContextState.ALIVE, repo_slug="foo", repo_url="",
                                      created_at="2026-01-01T00:00:00+00:00", alive_since="2026-01-01T00:00:00+00:00",
                                      current_branch=git(repo, "branch", "--show-current")))  # fmt: skip

    ctx = getattr(fake_service, verb)("foo")

    assert ctx.state == (ContextState.ALIVE if verb == "alive" else ContextState.DEAD)
    assert ctx.repo_url == store.get("foo").repo_url == str(remote)  # type: ignore[union-attr]
    assert repo.exists() is (verb == "alive")
