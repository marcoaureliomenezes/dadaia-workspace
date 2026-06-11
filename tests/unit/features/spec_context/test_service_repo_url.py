"""Unit tests for the repo_url lifecycle (T-011-08 / FR-W2-03, ADR-7).

Covers:
- ``create`` persists an explicit repo_url (CLI layer overrides catalog; service stores it).
- ``update_url`` repair verb through the store ``update()`` API.
- ``alive``/``dead`` back-fill repo_url from ``git remote get-url origin`` when the record
  URL is empty and the repo is on disk — exercised against a REAL ``GitSubprocessClient``
  with a local ``file://`` fixture remote as origin (per AC-W2-03).
"""

from __future__ import annotations

import pytest

pytest.importorskip("fcntl")

import shutil  # noqa: E402
import subprocess  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.core.exceptions import ContextNotFoundError  # noqa: E402
from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

_HAS_GIT = shutil.which("git") is not None


def _make_writable(root: Path) -> None:
    import os
    import stat

    for p in root.rglob("*"):
        with __import__("contextlib").suppress(OSError):
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD | (stat.S_IEXEC if p.is_dir() else 0))


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
def fake_service(store: FakeContextStore, workspace_root: Path) -> SpecContextService:
    return SpecContextService(
        context_store=store,
        git_client=FakeGitClient(),
        workspace_root=workspace_root,
    )


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@e",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@e",
            "PATH": __import__("os").environ.get("PATH", ""),
            "HOME": str(cwd),
        },
    )


# --------------------------------------------------------------------- create


def test_create_persists_explicit_repo_url(
    fake_service: SpecContextService, store: FakeContextStore
) -> None:
    ctx = fake_service.create("foo", "foo", "https://example.test/foo.git")
    assert ctx.repo_url == "https://example.test/foo.git"
    assert store.get("foo").repo_url == "https://example.test/foo.git"  # type: ignore[union-attr]


def test_create_persists_empty_url_when_unknown(
    fake_service: SpecContextService,
) -> None:
    ctx = fake_service.create("foo", "foo", "")
    assert ctx.repo_url == ""


# --------------------------------------------------------------------- update_url


def test_update_url_repairs_through_store(
    fake_service: SpecContextService, store: FakeContextStore
) -> None:
    fake_service.create("foo", "foo", "")
    updated = fake_service.update_url("foo", "https://example.test/foo.git")
    assert updated.repo_url == "https://example.test/foo.git"
    assert store.get("foo").repo_url == "https://example.test/foo.git"  # type: ignore[union-attr]


def test_update_url_preserves_state_and_branch(
    fake_service: SpecContextService, store: FakeContextStore
) -> None:
    fake_service.create("foo", "foo", "")
    # Simulate an ALIVE record with a branch set.
    existing = store.get("foo")
    assert existing is not None
    store.update(
        type(existing)(
            name=existing.name,
            state=ContextState.ALIVE,
            repo_slug=existing.repo_slug,
            repo_url="",
            created_at=existing.created_at,
            alive_since="2026-01-01T00:00:00+00:00",
            dead_since=None,
            current_branch="feature/x",
        )
    )
    updated = fake_service.update_url("foo", "https://example.test/foo.git")
    assert updated.state == ContextState.ALIVE
    assert updated.current_branch == "feature/x"
    assert updated.alive_since == "2026-01-01T00:00:00+00:00"
    assert updated.repo_url == "https://example.test/foo.git"


def test_update_url_missing_context_raises(fake_service: SpecContextService) -> None:
    with pytest.raises(ContextNotFoundError):
        fake_service.update_url("nope", "https://example.test/x.git")


# --------------------------------------------------------------------- back-fill (real git)


@pytest.mark.skipif(not _HAS_GIT, reason="git not available")
def test_alive_backfills_repo_url_from_origin_remote(
    store: FakeContextStore, workspace_root: Path, tmp_path: Path
) -> None:
    """alive() back-fills an empty repo_url from the on-disk origin remote.

    Uses a REAL GitSubprocessClient + a local ``file://`` fixture remote (AC-W2-03).
    """
    # Build a bare upstream remote.
    upstream = tmp_path / "upstream.git"
    _git(["init", "--bare", str(upstream)], cwd=tmp_path)
    file_url = upstream.as_uri()  # file:// URL

    # Place an on-disk repo whose origin points at the file:// remote, already DEAD->ALIVE-able.
    repo_path = workspace_root / "repos" / "foo"
    repo_path.mkdir(parents=True)
    _git(["init"], cwd=repo_path)
    _git(["remote", "add", "origin", file_url], cwd=repo_path)

    service = SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
    )
    # Record exists with EMPTY url and is DEAD (repo already present so clone is skipped).
    service.create("foo", "foo", "")

    ctx = service.alive("foo")
    assert ctx.state == ContextState.ALIVE
    assert ctx.repo_url == file_url
    # Persisted, not just returned.
    assert store.get("foo").repo_url == file_url  # type: ignore[union-attr]


@pytest.mark.skipif(not _HAS_GIT, reason="git not available")
def test_dead_backfills_repo_url_before_rmtree(
    store: FakeContextStore, workspace_root: Path, tmp_path: Path
) -> None:
    upstream = tmp_path / "upstream.git"
    _git(["init", "--bare", str(upstream)], cwd=tmp_path)
    file_url = upstream.as_uri()

    repo_path = workspace_root / "repos" / "foo"
    repo_path.mkdir(parents=True)
    _git(["init"], cwd=repo_path)
    _git(["checkout", "-b", "main"], cwd=repo_path)
    _git(["remote", "add", "origin", file_url], cwd=repo_path)
    # A committed tree pushed upstream so dead()'s clean-tree path is taken (no untracked
    # files → no commit_all; the existing upstream branch → push is a no-op, no new objects).
    (repo_path / "README.md").write_text("hi\n", encoding="utf-8")
    _git(["add", "-A"], cwd=repo_path)
    _git(["commit", "-m", "init"], cwd=repo_path)
    _git(["push", "-u", "origin", "main"], cwd=repo_path)

    # ALIVE record with EMPTY url, pointing at the on-disk repo (no alive() scaffold here —
    # we want a clean tree so dead() does not regenerate 0444 pack objects after chmod).
    ctx0 = SpecContextProject(
        name="foo",
        state=ContextState.ALIVE,
        repo_slug="foo",
        repo_url="",
        created_at="2026-01-01T00:00:00+00:00",
        alive_since="2026-01-01T00:00:00+00:00",
        dead_since=None,
        current_branch="main",
    )
    store.save(ctx0)

    service = SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
    )

    # Real git pack objects land 0444; dead()'s non-writable guard would otherwise block
    # the rmtree (orthogonal to this test). Make the tree writable first.
    _make_writable(repo_path)

    ctx = service.dead("foo")
    assert ctx.state == ContextState.DEAD
    assert ctx.repo_url == file_url  # back-filled before rmtree removed the repo
    assert not repo_path.exists()
