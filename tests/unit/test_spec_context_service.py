"""Unit tests for SpecContextService current ALIVE/DEAD behavior.

The suite proves lock-free context transitions plus the untracked-review and
secret/private-IP/.pem redaction gates. Secret values must never be echoed back in a
``DeadSecretFoundError`` message.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.container import scan_publish_candidates
from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
)
from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fakes import register_dead
from tests.fixtures.real_git import git, seeded_remote
from tests.fixtures.stores import context_store
from tests.helpers.privacy_fixtures import aws_key_shape, internal_host, private_ip


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
def remote(tmp_path: Path) -> str:
    return seeded_remote(tmp_path, "my-repo", branch="feature/0.1.0").as_uri()


@pytest.fixture()
def service(
    store: JsonContextStore,
    workspace_root: Path,
) -> SpecContextService:
    return SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
    )


# ------------------------------------------------------------------ create


def test_create_stores_context_and_rejects_duplicate(
    service: SpecContextService, store: JsonContextStore
) -> None:
    ctx = register_dead(service, "proj", "my-repo", "https://github.com/org/my-repo")
    assert store.get("proj") is not None
    assert ctx.state == ContextState.DEAD
    assert ctx.repo_slug == "my-repo"

    with pytest.raises(ContextAlreadyExistsError):
        register_dead(service, "proj", "other", "https://github.com/org/other")


# ------------------------------------------------------------------ alive (T-10b)


def test_alive_clone_behavior_state_and_not_found(
    service: SpecContextService, remote: str, workspace_root: Path
) -> None:
    register_dead(service, "proj", "my-repo", remote)
    repo = workspace_root / "repos" / "my-repo"

    # AC-T10b-1: alive() sets state=ALIVE, alive_since=<now>, dead_since=null; it
    # clones since the repo dir is absent.
    ctx = service.alive("proj")
    assert ctx.state == ContextState.ALIVE
    assert ctx.alive_since is not None
    assert ctx.dead_since is None
    assert git(repo, "remote", "get-url", "origin") == remote

    # AC-T10b-3: alive() on an already-ALIVE context is idempotent (no error, no
    # re-clone since the repo now exists).
    (repo / "local.txt").write_text("kept\n", encoding="utf-8")
    ctx2 = service.alive("proj")
    assert ctx2.state == ContextState.ALIVE
    assert (repo / "local.txt").read_text(encoding="utf-8") == "kept\n"

    # No clone at all when the repo dir is already present before the first alive().
    (workspace_root / "repos" / "other-repo").mkdir(parents=True)
    register_dead(service, "other", "other-repo", remote)
    service.alive("other")
    assert list((workspace_root / "repos" / "other-repo").iterdir()) == []

    with pytest.raises(ContextNotFoundError):
        service.alive("ghost")


# ------------------------------------------------------------------ dead (T-10b)


@pytest.mark.parametrize(
    ("name", "filename", "write_fn", "expect_secret_absent"),
    [
        (
            # AC-R7-01: --commit + a planted secret in an untracked file ⇒ block the
            # push. The value is never echoed back in the exception message.
            "planted_secret",
            "config.env",
            lambda repo: (repo / "config.env").write_text(f"AWS_ACCESS_KEY_ID={aws_key_shape()}\n"),
            aws_key_shape(),
        ),
        (
            # A planted private IP / internal hostname also blocks --commit push.
            "planted_private_ip",
            "hosts.txt",
            lambda repo: (repo / "hosts.txt").write_text(
                f"db host: {private_ip()} ({internal_host('db-primary')})\n"
            ),
            None,
        ),
        (
            # R-2 (v0.1.10 rc-2 sec LOW): a private-key file (.pem) in the untracked
            # push set is a finding by its *suffix alone* — the binary-suffix family
            # was skipped by the old text-only scan. dead() --commit must block
            # regardless of byte content.
            "pem_suffix_binary",
            "server.pem",
            lambda repo: (repo / "server.pem").write_bytes(b"\x00\x01\x02opaque-key-bytes\xff\xfe"),
            None,
        ),
    ],
)
def test_dead_with_commit_blocks_on_redacted_findings(
    service: SpecContextService,
    remote: str,
    workspace_root: Path,
    name: str,
    filename: str,
    write_fn: object,
    expect_secret_absent: str | None,
) -> None:
    from dadaia_workspace.features.spec_context.service import DeadSecretFoundError

    register_dead(service, "proj", "my-repo", remote)
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    head = git(repo, "rev-parse", "HEAD")
    write_fn(repo)  # type: ignore[operator]

    with pytest.raises(DeadSecretFoundError) as exc:
        service.dead("proj", commit=True)

    assert filename in str(exc.value)
    if expect_secret_absent is not None:
        assert expect_secret_absent not in str(exc.value)
    # Nothing pushed/committed; repo untouched.
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "rev-parse", "origin/feature/0.1.0") == head
    assert repo.exists()
    assert service.show("proj").state == ContextState.ALIVE


# ------------------------------------------------------------------ delete


def test_delete_removes_dead_context_not_found_and_alive_raises(
    service: SpecContextService, store: JsonContextStore, remote: str
) -> None:
    with pytest.raises(ContextNotFoundError):
        service.delete("ghost")

    register_dead(service, "proj", "my-repo", remote)
    service.alive("proj")
    with pytest.raises(ContextStateError):
        service.delete("proj")

    register_dead(service, "proj2", "my-repo2", "https://github.com/org/my-repo2")
    service.delete("proj2")
    assert store.get("proj2") is None
