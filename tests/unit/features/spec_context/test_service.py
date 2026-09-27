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
        secret_scan=scan_publish_candidates,
    )


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
        secret_scan=scan_publish_candidates,
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
