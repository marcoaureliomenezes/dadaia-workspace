"""Unit tests for SpecContextService current ALIVE/DEAD behavior.

The suite proves lock-free context transitions plus the untracked-review and
secret/private-IP/.pem redaction gates. Secret values must never be echoed back in a
``DeadSecretFoundError`` message.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
)
from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.features.spec_context.service import SpecContextService
from tests.fakes import FakeContextStore, FakeGitClient


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


def test_create_stores_context_and_rejects_duplicate(
    service: SpecContextService, store: FakeContextStore
) -> None:
    ctx = service.create("proj", "my-repo", "https://github.com/org/my-repo")
    assert store.get("proj") is not None
    assert ctx.state == ContextState.DEAD
    assert ctx.repo_slug == "my-repo"

    with pytest.raises(ContextAlreadyExistsError):
        service.create("proj", "other", "https://github.com/org/other")


# ------------------------------------------------------------------ alive (T-10b)


def test_alive_clone_behavior_state_and_not_found(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")

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
    other_svc.create("other", "other-repo", "https://github.com/org/other-repo")
    other_svc.alive("other")
    assert len(git.cloned) == 1  # unchanged — no new clone for "other"

    with pytest.raises(ContextNotFoundError):
        service.alive("ghost")


# ------------------------------------------------------------------ dead (T-10b)


def test_dead_removes_repo_syncs_dirty_pushes_and_state_error(
    service: SpecContextService, workspace_root: Path, git: FakeGitClient
) -> None:
    """AC-T10b-2: dead() sets state=DEAD, dead_since=<now>, syncs the dirty tracked
    tree, and pushes when a remote is present — the normal end-to-end flow, and its
    clean-tree-unchanged regression (no untracked ⇒ gate is a no-op)."""
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    assert repo.exists()
    git._dirty.add(repo)
    git._has_remote.add(repo)

    ctx = service.dead("proj")

    assert not repo.exists()
    assert ctx.state == ContextState.DEAD
    assert ctx.dead_since is not None
    assert repo in git.committed  # tracked-dirty auto-synced (FR-R7)
    assert repo in git.pushed

    # Calling dead() again (already DEAD, not ALIVE) is a state error.
    with pytest.raises(ContextStateError):
        service.dead("proj")

    with pytest.raises(ContextNotFoundError):
        service.dead("ghost")


def test_dead_ignores_residual_legacy_lock_record(
    service: SpecContextService, workspace_root: Path
) -> None:
    """A pre-doctrine lock file can never block a context transition."""
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")

    lock_dir = workspace_root / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / "proj.lock.json").write_text('{"legacy": true}', encoding="utf-8")

    assert service.dead("proj").state is ContextState.DEAD


# ------------------------------------------------------ dead() review gate (F-5 / AC-R7-01)


def test_dead_refuses_on_untracked_files_without_commit(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    """AC-R7-01: untracked files + no --commit ⇒ refuse, push nothing, repo untouched."""
    from dadaia_workspace.features.spec_context.service import DeadReviewRequiredError

    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    git._has_remote.add(repo)
    # Plant an untracked file on disk + tell the fake git it is untracked.
    (repo / "leftover.txt").write_text("operator forgot to gitignore this")
    git._untracked[repo] = ["leftover.txt"]

    with pytest.raises(DeadReviewRequiredError) as exc:
        service.dead("proj")

    # Files are listed in the message.
    assert "leftover.txt" in str(exc.value)
    # NOTHING pushed, NOTHING committed, repo left on disk untouched.
    assert repo not in git.pushed
    assert repo not in git.committed
    assert repo.exists()
    assert (repo / "leftover.txt").exists()
    # Context is still ALIVE (state not mutated).
    assert service.show("proj").state == ContextState.ALIVE


def test_dead_with_commit_and_clean_untracked_passes(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    """AC-R7-01: --commit + clean (secret-free) untracked files ⇒ proceeds + pushes."""
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    git._has_remote.add(repo)
    git._dirty.add(repo)
    (repo / "notes.md").write_text("# just some harmless notes\nnothing secret here\n")
    git._untracked[repo] = ["notes.md"]

    ctx = service.dead("proj", commit=True)

    assert ctx.state == ContextState.DEAD
    assert repo in git.committed
    assert repo in git.pushed
    assert not repo.exists()


@pytest.mark.parametrize(
    ("name", "filename", "write_fn", "expect_secret_absent"),
    [
        (
            # AC-R7-01: --commit + a planted secret in an untracked file ⇒ block the
            # push. The value is never echoed back in the exception message.
            "planted_secret",
            "config.env",
            lambda repo: (repo / "config.env").write_text(
                "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n"
            ),
            "AKIAIOSFODNN7EXAMPLE",
        ),
        (
            # A planted private IP / internal hostname also blocks --commit push.
            "planted_private_ip",
            "hosts.txt",
            lambda repo: (repo / "hosts.txt").write_text(
                "db host: 10.4.2.17 (db-primary.internal)\n"
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

    service.create("proj", "my-repo", "https://github.com/org/my-repo")
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


def test_scan_flags_key_suffixes_and_skips_other_binary(tmp_path: Path) -> None:
    """R-2: cert/key suffixes flag on presence; an unrelated binary suffix stays clean."""
    from dadaia_workspace.features.spec_context.service import _scan_file_for_secrets

    for suffix in (".pem", ".key", ".p12", ".pfx"):
        f = tmp_path / f"material{suffix}"
        f.write_bytes(b"\x00binary\xff")
        assert _scan_file_for_secrets(f) == ["cert-key-file-suffix"], suffix

    # A decodable PEM block triggers BOTH the suffix rule and the content rule.
    pem = tmp_path / "real.pem"
    pem.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n")
    hits = _scan_file_for_secrets(pem)
    assert "cert-key-file-suffix" in hits
    assert "private-key-block" in hits

    # An unrelated binary suffix (not key material, not text-decodable) stays clean.
    blob = tmp_path / "image.png"
    blob.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01")
    assert _scan_file_for_secrets(blob) == []


# ------------------------------------------------------------------ delete


def test_delete_removes_dead_context_not_found_and_alive_raises(
    service: SpecContextService, store: FakeContextStore, workspace_root: Path
) -> None:
    with pytest.raises(ContextNotFoundError):
        service.delete("ghost")

    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    with pytest.raises(ContextStateError):
        service.delete("proj")

    service.create("proj2", "my-repo2", "https://github.com/org/my-repo2")
    service.delete("proj2")
    assert store.get("proj2") is None
