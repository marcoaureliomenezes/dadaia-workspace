"""Unit tests for SpecContextService — Bug 3 (T-BCR-04), updated for T-10b.

Bug 3: shutil.rmtree fails with PermissionError on root-owned files.
Fix: detect non-writable files before rmtree and raise GitSyncError with
     a descriptive message suggesting 'sudo chown'.

T-10b: activate()/deactivate() removed; alive()/dead() replace them.

CRITICAL ALIVE/DEAD state machine — alive() leaving operator specs untouched is the
data-loss guard this file exists to keep, alongside the non-writable-files dead() fix.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import stat  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.core.models.spec_context import ContextState  # noqa: E402
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient, register_dead  # noqa: E402


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
    )


def test_dead_succeeds_on_non_writable_files(
    service: SpecContextService,
    store: FakeContextStore,
    git: FakeGitClient,
    workspace_root: Path,
) -> None:
    """v0.1.50 FR3 (bug context-dead-nonwritable-guard-rejects-standard-git-objects):
    read-only files (git loose objects are 0444 BY DESIGN) no longer refuse dead() —
    rmtree runs with a chmod-and-retry handler, replacing the old GitSyncError guard.
    """
    register_dead(service, "proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")

    repo = workspace_root / "repos" / "my-repo"
    assert repo.exists()

    locked_file = repo / "locked.txt"
    locked_file.write_text("content")
    locked_file.chmod(stat.S_IRUSR | stat.S_IRGRP)  # read-only, like a loose object

    result = service.dead("proj")
    assert result.state is ContextState.DEAD
    assert not repo.exists()


def test_alive_leaves_a_preexisting_specs_tree_untouched_and_hooks_the_repo(
    store: FakeContextStore,
    git: FakeGitClient,
    workspace_root: Path,
) -> None:
    """0.4.8 AC3.7: alive() never merges, backs up or commits specs — an operator tree
    stays byte-identical, nothing is committed, and the hook installer runs on the repo."""
    hooked: list[Path] = []
    svc = SpecContextService(
        context_store=store,
        git_client=git,
        workspace_root=workspace_root,
        install_hooks=hooked.append,
    )
    register_dead(svc, "proj", "my-repo", "https://github.com/org/my-repo")
    repo = workspace_root / "repos" / "my-repo"
    (repo / "specs").mkdir(parents=True)
    (repo / "specs" / "constitution.md").write_text("# operator\n", encoding="utf-8")
    git._dirty.add(repo)

    svc.alive("proj")

    assert sorted(p.name for p in (repo / "specs").iterdir()) == ["constitution.md"]
    assert not (workspace_root / "repos" / "my-repo" / "specs_bkp").exists()
    assert repo not in git.committed
    assert hooked == [repo]
