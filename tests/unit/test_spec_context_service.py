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
from tests.fakes import FakeContextStore, FakeGitClient, register_dead
from tests.helpers.privacy_fixtures import aws_key_shape, internal_host, private_ip


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
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
    )


# ------------------------------------------------------------------ create


def test_create_stores_context_and_rejects_duplicate(
    service: SpecContextService, store: FakeContextStore
) -> None:
    ctx = register_dead(service, "proj", "my-repo", "https://github.com/org/my-repo")
    assert store.get("proj") is not None
    assert ctx.state == ContextState.DEAD
    assert ctx.repo_slug == "my-repo"

    with pytest.raises(ContextAlreadyExistsError):
        register_dead(service, "proj", "other", "https://github.com/org/other")


# ------------------------------------------------------------------ alive (T-10b)


def test_alive_clone_behavior_state_and_not_found(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    register_dead(service, "proj", "my-repo", "https://github.com/org/my-repo")

    # AC-T10b-1: alive() sets state=ALIVE, alive_since=<now>, dead_since=null; it
    # clones since the repo dir is absent.
    ctx = service.alive("proj")
    assert ctx.state == ContextState.ALIVE
    assert ctx.alive_since is not None
    assert ctx.dead_since is None
    assert len(git.cloned) == 1
    assert git.cloned[0][0] == "https://github.com/org/my-repo"

    # AC-T10b-3: alive() on an already-ALIVE context is idempotent (no error, no
    # re-clone since the repo now exists).
    ctx2 = service.alive("proj")
    assert ctx2.state == ContextState.ALIVE
    assert len(git.cloned) == 1

    # No clone at all when the repo dir is already present before the first alive().
    other_svc = service
    (workspace_root / "repos" / "other-repo").mkdir(parents=True)
    register_dead(other_svc, "other", "other-repo", "https://github.com/org/other-repo")
    other_svc.alive("other")
    assert len(git.cloned) == 1  # unchanged — no new clone for "other"

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
    git: FakeGitClient,
    workspace_root: Path,
    name: str,
    filename: str,
    write_fn: object,
    expect_secret_absent: str | None,
) -> None:
    from dadaia_workspace.features.spec_context.service import DeadSecretFoundError

    register_dead(service, "proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    git._has_remote.add(repo)
    write_fn(repo)  # type: ignore[operator]
    git._untracked[repo] = [filename]

    with pytest.raises(DeadSecretFoundError) as exc:
        service.dead("proj", commit=True)

    assert filename in str(exc.value)
    if expect_secret_absent is not None:
        assert expect_secret_absent not in str(exc.value)
    # Nothing pushed/committed; repo untouched.
    assert repo not in git.pushed
    assert repo not in git.committed
    assert repo.exists()
    assert service.show("proj").state == ContextState.ALIVE


# ------------------------------------------------------------------ delete


def test_delete_removes_dead_context_not_found_and_alive_raises(
    service: SpecContextService, store: FakeContextStore, workspace_root: Path
) -> None:
    with pytest.raises(ContextNotFoundError):
        service.delete("ghost")

    register_dead(service, "proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    with pytest.raises(ContextStateError):
        service.delete("proj")

    register_dead(service, "proj2", "my-repo2", "https://github.com/org/my-repo2")
    service.delete("proj2")
    assert store.get("proj2") is None
