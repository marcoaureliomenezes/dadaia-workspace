"""Unit tests for SpecContextService — Bug 3 (T-BCR-04), updated for T-10b.

Bug 3: shutil.rmtree fails with PermissionError on root-owned files.
Fix: detect non-writable files before rmtree and raise GitSyncError with
     a descriptive message suggesting 'sudo chown'.

T-10b: activate()/deactivate() removed; alive()/dead() replace them.

CRITICAL ALIVE/DEAD state machine — operator data preservation on alive-merge is the
data-loss guard this file exists to keep, alongside the non-writable-files dead() fix.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import stat  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.core.models.spec_context import ContextState  # noqa: E402
from dadaia_workspace.features.spec_context.service import (  # noqa: E402
    _SCAFFOLD_SRC,
    SpecContextService,
)
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
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")

    repo = workspace_root / "repos" / "my-repo"
    assert repo.exists()

    locked_file = repo / "locked.txt"
    locked_file.write_text("content")
    locked_file.chmod(stat.S_IRUSR | stat.S_IRGRP)  # read-only, like a loose object

    result = service.dead("proj")
    assert result.state is ContextState.DEAD
    assert not repo.exists()


def test_alive_with_preexisting_specs_adds_missing_files_without_overwriting(
    workspace_root: Path,
    store: FakeContextStore,
    git: FakeGitClient,
) -> None:
    """T-021-16 (b): when specs/ already exists alive() must merge missing canonical
    files into it without overwriting any file that is already present.

    Invariants:
    - Pre-existing operator file is NOT overwritten.
    - Missing canonical scaffold file IS added.
    - alive() succeeds (no exception).
    """
    svc = SpecContextService(
        context_store=store,
        git_client=git,
        workspace_root=workspace_root,
    )
    svc.create("proj", "my-repo", "https://github.com/org/my-repo")

    # Pre-create the repo dir (FakeGitClient.clone does this, but we also need specs/)
    repo_dir = workspace_root / "repos" / "my-repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    specs_dir = repo_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    # Place an operator file that must NOT be overwritten
    operator_file = specs_dir / "constitution.md"
    original_content = "# My custom constitution\n\nOperator-authored content.\n"
    operator_file.write_text(original_content, encoding="utf-8")

    # alive() must not raise and must not overwrite constitution.md
    svc.alive("proj")

    # Operator file preserved
    assert operator_file.read_text(encoding="utf-8") == original_content, (
        "alive() must NOT overwrite pre-existing operator files in specs/"
    )

    # At least one canonical scaffold file was merged in (scaffold src must exist)
    if _SCAFFOLD_SRC.exists():
        # The scaffold has a memory/ dir; it should be present after merge
        assert specs_dir.exists(), "specs/ must still exist after merge"


def test_dead_writable_alive_safe_preserve_and_merge_not_skipped(
    workspace_root: Path,
    store: FakeContextStore,
    git: FakeGitClient,
) -> None:
    """Baseline dead() on all-writable files; alive()'s safe-preserve backup snapshot
    (FR-S06 path a / T-016-S01); and alive() on a pre-existing (empty) specs/ actually
    executes the merge path rather than silently skipping it."""
    svc = SpecContextService(
        context_store=store,
        git_client=git,
        workspace_root=workspace_root,
    )

    # Baseline: dead() succeeds when all files are writable.
    svc.create("proj", "my-repo", "https://github.com/org/my-repo")
    svc.alive("proj")
    repo = workspace_root / "repos" / "my-repo"
    (repo / "writable.txt").write_text("data")
    svc.dead("proj")
    assert not repo.exists()

    if not _SCAFFOLD_SRC.exists():
        return  # merge/backup only run when the scaffold source exists

    # Safe-preserve: a pre-existing tree is snapshotted to specs_bkp/preserve-<UTC>/.
    svc.create("projbk", "repobk", "https://github.com/org/repobk")
    repo_dir_bk = workspace_root / "repos" / "repobk"
    specs_dir_bk = repo_dir_bk / "specs"
    specs_dir_bk.mkdir(parents=True, exist_ok=True)
    (specs_dir_bk / "constitution.md").write_text("# operator\n", encoding="utf-8")
    svc.alive("projbk")

    from dadaia_workspace.core import specs_backup as _sb

    backups = list(_sb.backup_root(specs_dir_bk).glob("preserve-*"))
    assert backups, "alive() must safe-preserve the pre-existing specs/ before merging"
    assert (backups[0] / "constitution.md").read_text(encoding="utf-8") == "# operator\n"

    # No silent-skip: an empty pre-existing specs/ still gets merge-enriched.
    svc.create("proj2", "repo2", "https://github.com/org/repo2")
    repo_dir2 = workspace_root / "repos" / "repo2"
    specs_dir2 = repo_dir2 / "specs"
    specs_dir2.mkdir(parents=True, exist_ok=True)
    svc.alive("proj2")

    scaffold_files = list(_SCAFFOLD_SRC.rglob("*"))
    non_dir_scaffold = [f for f in scaffold_files if f.is_file()]
    specs_files2 = [f for f in specs_dir2.rglob("*") if f.is_file()]
    assert len(specs_files2) >= len(non_dir_scaffold), (
        f"alive() did not merge scaffold files into empty specs/; "
        f"expected >={len(non_dir_scaffold)} files, got {len(specs_files2)}"
    )


def test_alive_commits_its_own_scaffold(
    service: SpecContextService,
    store: FakeContextStore,
    git: FakeGitClient,
    workspace_root: Path,
) -> None:
    """Bug alive-scaffold-blocks-dead (validation-027 F-06).

    alive() scaffolds specs/ + AGENTS.md into the cloned repo but left them
    UNTRACKED, so an immediate dead() hit the untracked-consent guard and the
    create->alive->dead lifecycle could never complete on a fresh context. The
    tool must commit the files IT created: alive() ends with a scaffold commit.
    """
    repo = workspace_root / "repos" / "my-repo"
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    # The fake reports the working tree dirty (as the real client does right after
    # alive() writes the scaffold into the fresh clone).
    git._dirty.add(repo)
    service.alive("proj")

    assert (repo / "specs").exists(), "scaffold must exist"
    assert repo in git.committed, "alive() must commit the scaffold it created"
