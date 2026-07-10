"""Integration tests for the dead() review gate + secret scan (F-5 / AC-R7-01).

These drive the REAL ``GitSubprocessClient`` (real ``git ls-files --others
--exclude-standard`` for untracked detection, real commit/push) against a real
git repo + bare remote in ``tmp_path``, mirroring the existing dead()/git-subprocess
test conventions. The structural secret scan runs over real on-disk file content.

Covered:
  - untracked file + no --commit  ⇒ refuse, push NOTHING, repo left on disk.
  - --commit + secret-free untracked ⇒ commit + push + repo removed.
  - --commit + planted secret      ⇒ DeadSecretFoundError, push NOTHING, repo kept.
  - gitignored file is NOT treated as untracked (gate stays silent).
  - clean tree (only tracked content) ⇒ unchanged behaviour.
"""

from __future__ import annotations

import contextlib
import stat
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import (  # noqa: E402
    DeadReviewRequiredError,
    DeadSecretFoundError,
    SpecContextService,
)
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient  # noqa: E402
from tests.fakes import FakeContextStore  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _run(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, capture_output=True, check=True)


def _bare_remote(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _run(["git", "init", "--bare", str(bare)])
    return bare


def _clone_with_initial_commit(remote: Path, dest: Path) -> None:
    _run(["git", "clone", str(remote), str(dest)])
    _run(["git", "config", "user.email", "test@test.com"], cwd=dest)
    _run(["git", "config", "user.name", "Test"], cwd=dest)
    (dest / "README.md").write_text("init\n")
    _run(["git", "add", "-A"], cwd=dest)
    _run(["git", "commit", "-m", "init"], cwd=dest)
    _run(["git", "push", "-u", "origin", "HEAD"], cwd=dest)


class _WritableObjectsGitClient(GitSubprocessClient):
    """Real git client that re-grants user-write after a commit.

    git writes loose objects 0444; the pre-existing dead() non-writable guard
    (an orthogonal product quirk, see memory) would then block rmtree. Re-granting
    write after commit isolates THIS test to the review-gate behaviour under test —
    list_untracked / commit / push all stay real.
    """

    def commit_all(self, path: Path, msg: str) -> None:
        super().commit_all(path, msg)
        _make_tree_writable(path)


def _make_service(workspace_root: Path) -> tuple[SpecContextService, FakeContextStore]:
    store = FakeContextStore()
    service = SpecContextService(
        context_store=store,
        git_client=_WritableObjectsGitClient(),
        workspace_root=workspace_root,
    )
    return service, store


def _make_tree_writable(root: Path) -> None:
    """git packs objects read-only; dead()'s non-writable guard would otherwise fire.

    This mirrors the documented operator workaround (`chmod -R u+w`) so the
    rmtree path is exercised; the review gate under test runs before any of this.
    """
    for path in root.rglob("*"):
        with contextlib.suppress(OSError):
            path.chmod(path.stat().st_mode | stat.S_IWUSR)


def _alive_ctx(store: FakeContextStore, repo_slug: str) -> None:
    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.ALIVE,
            repo_slug=repo_slug,
            repo_url="https://example.invalid/proj.git",
            created_at="2026-06-09T00:00:00+00:00",
            alive_since="2026-06-09T00:00:00+00:00",
            dead_since=None,
            current_branch="main",
        )
    )


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "repos").mkdir(parents=True)
    return root


def test_dead_refuses_untracked_without_commit_real_git(
    tmp_path: Path, workspace_root: Path
) -> None:
    remote = _bare_remote(tmp_path)
    repo = workspace_root / "repos" / "proj-repo"
    _clone_with_initial_commit(remote, repo)
    (repo / "forgotten.txt").write_text("private notes the operator forgot\n")

    service, store = _make_service(workspace_root)
    _alive_ctx(store, "proj-repo")

    with pytest.raises(DeadReviewRequiredError) as exc:
        service.dead("proj")

    assert "forgotten.txt" in str(exc.value)
    # Repo left on disk untouched; context still ALIVE.
    assert repo.exists()
    assert (repo / "forgotten.txt").exists()
    assert store.get("proj").state == ContextState.ALIVE  # type: ignore[union-attr]
    # Nothing was pushed to the remote (still only the initial commit).
    log = subprocess.run(["git", "log", "--oneline"], cwd=remote, capture_output=True, text=True)
    assert "auto-sync before dead" not in log.stdout


def test_dead_with_commit_secret_free_untracked_pushes_real_git(
    tmp_path: Path, workspace_root: Path
) -> None:
    remote = _bare_remote(tmp_path)
    repo = workspace_root / "repos" / "proj-repo"
    _clone_with_initial_commit(remote, repo)
    (repo / "notes.md").write_text("# harmless notes\nno secrets here at all\n")

    service, store = _make_service(workspace_root)
    _alive_ctx(store, "proj-repo")

    _make_tree_writable(repo)
    ctx = service.dead("proj", commit=True)

    assert ctx.state == ContextState.DEAD
    assert not repo.exists()
    # The remote received the auto-sync commit carrying the new file.
    log = subprocess.run(["git", "log", "--oneline"], cwd=remote, capture_output=True, text=True)
    assert "auto-sync before dead" in log.stdout


def test_dead_with_commit_planted_secret_blocks_real_git(
    tmp_path: Path, workspace_root: Path
) -> None:
    remote = _bare_remote(tmp_path)
    repo = workspace_root / "repos" / "proj-repo"
    _clone_with_initial_commit(remote, repo)
    secret = "AKIAIOSFODNN7EXAMPLE"
    (repo / "creds.env").write_text(f"AWS_ACCESS_KEY_ID={secret}\n")

    service, store = _make_service(workspace_root)
    _alive_ctx(store, "proj-repo")

    with pytest.raises(DeadSecretFoundError) as exc:
        service.dead("proj", commit=True)

    assert "creds.env" in str(exc.value)
    assert secret not in str(exc.value)  # redacted
    # Push blocked: repo kept, remote unchanged, context still ALIVE.
    assert repo.exists()
    assert store.get("proj").state == ContextState.ALIVE  # type: ignore[union-attr]
    log = subprocess.run(["git", "log", "--oneline"], cwd=remote, capture_output=True, text=True)
    assert "auto-sync before dead" not in log.stdout


def test_dead_proceeds_gitignored_clean_tree_and_readonly_objects_real_git(
    tmp_path: Path, workspace_root: Path
) -> None:
    """Three "dead() proceeds" scenarios, each with its own repo/remote fixture:
    (1) a gitignored file is NOT untracked-for-review, so the gate stays silent even
    without --commit; (2) a clean tree (only tracked content) proceeds without
    --commit; (3) v0.1.50 FR3 (bug
    context-dead-nonwritable-guard-rejects-standard-git-objects): 0444 loose objects
    are git-normal — dead() rmtree-chmod-retries with the PLAIN GitSubprocessClient
    (no _WritableObjectsGitClient workaround needed)."""
    # (1) gitignored file — gate stays silent.
    (tmp_path / "remote1").mkdir()
    remote1 = _bare_remote(tmp_path / "remote1")
    repo1 = workspace_root / "repos" / "proj-repo-gitignored"
    _clone_with_initial_commit(remote1, repo1)
    (repo1 / ".gitignore").write_text("ignored.txt\n")
    _run(["git", "add", ".gitignore"], cwd=repo1)
    _run(["git", "commit", "-m", "add gitignore"], cwd=repo1)
    (repo1 / "ignored.txt").write_text("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n")

    service1, store1 = _make_service(workspace_root)
    _alive_ctx(store1, "proj-repo-gitignored")
    _make_tree_writable(repo1)
    ctx1 = service1.dead("proj")
    assert ctx1.state == ContextState.DEAD
    assert not repo1.exists()

    # (2) clean tree — proceeds without --commit.
    (tmp_path / "remote2").mkdir()
    remote2 = _bare_remote(tmp_path / "remote2")
    repo2 = workspace_root / "repos" / "proj-repo-clean"
    _clone_with_initial_commit(remote2, repo2)

    store2 = FakeContextStore()
    service2 = SpecContextService(
        context_store=store2,
        git_client=_WritableObjectsGitClient(),
        workspace_root=workspace_root,
    )
    _alive_ctx(store2, "proj-repo-clean")
    _make_tree_writable(repo2)
    ctx2 = service2.dead("proj")
    assert ctx2.state == ContextState.DEAD
    assert not repo2.exists()

    # (3) read-only git loose objects — rmtree-chmod-retry succeeds with the plain client.
    import os

    (tmp_path / "remote3").mkdir()
    remote3 = _bare_remote(tmp_path / "remote3")
    dest = workspace_root / "repos" / "proj-readonly"
    _clone_with_initial_commit(remote3, dest)

    store3 = FakeContextStore()
    service3 = SpecContextService(
        context_store=store3,
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
    )
    _alive_ctx(store3, "proj-readonly")

    readonly = [
        p
        for p in (dest / ".git" / "objects").rglob("*")
        if p.is_file() and not os.access(p, os.W_OK)
    ]
    assert readonly, "precondition: git wrote read-only loose objects"

    result = service3.dead("proj", commit=False)
    assert result.state is ContextState.DEAD
    assert not dest.exists()
