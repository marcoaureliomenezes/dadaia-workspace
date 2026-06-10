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


def test_dead_with_commit_blocks_on_planted_secret(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    """AC-R7-01: --commit + a planted secret in an untracked file ⇒ block the push."""
    from dadaia_workspace.features.spec_context.service import DeadSecretFoundError

    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    git._has_remote.add(repo)
    secret_value = "AKIAIOSFODNN7EXAMPLE"
    (repo / "config.env").write_text(f"AWS_ACCESS_KEY_ID={secret_value}\n")
    git._untracked[repo] = ["config.env"]

    with pytest.raises(DeadSecretFoundError) as exc:
        service.dead("proj", commit=True)

    # File named, secret value redacted (never echoed back).
    assert "config.env" in str(exc.value)
    assert secret_value not in str(exc.value)
    # Nothing pushed/committed; repo untouched.
    assert repo not in git.pushed
    assert repo not in git.committed
    assert repo.exists()
    assert service.show("proj").state == ContextState.ALIVE


def test_dead_with_commit_blocks_on_planted_private_ip(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    """AC-R7-01: a planted private IP / internal hostname also blocks --commit push."""
    from dadaia_workspace.features.spec_context.service import DeadSecretFoundError

    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    git._has_remote.add(repo)
    (repo / "hosts.txt").write_text("db host: 10.4.2.17 (db-primary.internal)\n")
    git._untracked[repo] = ["hosts.txt"]

    with pytest.raises(DeadSecretFoundError):
        service.dead("proj", commit=True)

    assert repo not in git.pushed
    assert repo.exists()


def test_dead_with_commit_blocks_on_untracked_pem_key_file(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    """R-2 (v0.1.10 rc-2 sec LOW): a private-key file (.pem) in the untracked push
    set is a finding by its *suffix alone* — the binary-suffix family was skipped by
    the old text-only scan. dead() --commit must block regardless of byte content."""
    from dadaia_workspace.features.spec_context.service import DeadSecretFoundError

    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    git._has_remote.add(repo)
    # Non-PEM-formatted bytes: caught purely by the .pem suffix, not by content.
    (repo / "server.pem").write_bytes(b"\x00\x01\x02opaque-key-bytes\xff\xfe")
    git._untracked[repo] = ["server.pem"]

    with pytest.raises(DeadSecretFoundError) as exc:
        service.dead("proj", commit=True)

    assert "server.pem" in str(exc.value)
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


def test_dead_clean_tree_unchanged_no_untracked(
    service: SpecContextService, git: FakeGitClient, workspace_root: Path
) -> None:
    """AC-R7-01 regression: a clean tree (no untracked) ⇒ dead() behaves as before."""
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    git._has_remote.add(repo)
    git._dirty.add(repo)
    # No untracked files registered → gate is a no-op.

    ctx = service.dead("proj")  # no --commit needed

    assert ctx.state == ContextState.DEAD
    assert repo in git.committed  # tracked-dirty still auto-synced (FR-R7)
    assert repo in git.pushed
    assert not repo.exists()


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
