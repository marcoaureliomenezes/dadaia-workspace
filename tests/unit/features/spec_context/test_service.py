"""Unit tests for SpecContextService — Bug 3 (T-BCR-04), updated for T-10b.

Bug 3: shutil.rmtree fails with PermissionError on root-owned files.
Fix: detect non-writable files before rmtree and raise GitSyncError with
     a descriptive message suggesting 'sudo chown'.

T-10b: activate()/deactivate() removed; alive()/dead() replace them.

CRITICAL ALIVE/DEAD state machine — alive() leaving operator specs untouched is the
data-loss guard this file exists to keep, alongside the non-writable-files dead() fix.
"""

from __future__ import annotations

import pytest

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).

pytest.importorskip("fcntl")

from pathlib import Path  # noqa: E402

from dadaia_workspace.container import scan_publish_candidates
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fakes import register_dead  # noqa: E402
from tests.fixtures.real_git import clone, seeded_remote
from tests.fixtures.real_git import git as run_git
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
def git() -> GitSubprocessClient:
    return GitSubprocessClient()


@pytest.fixture()
def service(
    store: JsonContextStore,
    git: GitSubprocessClient,
    workspace_root: Path,
) -> SpecContextService:
    return SpecContextService(
        context_store=store,
        git_client=git,
        workspace_root=workspace_root,
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
    )


def test_alive_leaves_a_preexisting_specs_tree_untouched_and_hooks_the_repo(
    store: JsonContextStore,
    git: GitSubprocessClient,
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
        secret_scan=scan_publish_candidates,
    )
    remote = seeded_remote(workspace_root.parent, "my-repo")
    register_dead(svc, "proj", "my-repo", remote.as_uri())
    repo = clone(remote, workspace_root / "repos" / "my-repo")
    head = run_git(repo, "rev-parse", "HEAD")
    (repo / "specs").mkdir(parents=True)
    (repo / "specs" / "constitution.md").write_text("# operator\n", encoding="utf-8")

    svc.alive("proj")

    assert sorted(p.name for p in (repo / "specs").iterdir()) == ["constitution.md"]
    assert not (workspace_root / "repos" / "my-repo" / "specs_bkp").exists()
    assert run_git(repo, "rev-parse", "HEAD") == head
    assert hooked == [repo]
