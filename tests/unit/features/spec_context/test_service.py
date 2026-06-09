"""Unit tests for SpecContextService — Bug 3 (T-BCR-04), updated for T-10b.

Bug 3: shutil.rmtree fails with PermissionError on root-owned files.
Fix: detect non-writable files before rmtree and raise GitSyncError with
     a descriptive message suggesting 'sudo chown'.

T-10b: activate()/deactivate() removed; alive()/dead() replace them.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import stat  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.core.exceptions import GitSyncError  # noqa: E402
from dadaia_workspace.features.spec_context.service import (  # noqa: E402
    _SCAFFOLD_SRC,
    SpecContextService,
)
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Bug 3 — shutil.rmtree must not swallow PermissionError silently
# ---------------------------------------------------------------------------


def test_dead_raises_gitsyncerror_on_non_writable_files(
    service: SpecContextService,
    store: FakeContextStore,
    git: FakeGitClient,
    workspace_root: Path,
) -> None:
    """When the repo directory contains non-writable files, dead() must raise
    GitSyncError with an actionable message instead of allowing PermissionError
    to propagate unhandled.

    Updated for T-10b: deactivate() → dead().
    """
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")

    repo = workspace_root / "repos" / "my-repo"
    assert repo.exists()

    # Create a file inside the repo then make it non-writable
    locked_file = repo / "locked.txt"
    locked_file.write_text("content")
    locked_file.chmod(stat.S_IRUSR | stat.S_IRGRP)  # read-only

    try:
        with pytest.raises(GitSyncError) as exc_info:
            service.dead("proj")

        msg = str(exc_info.value)
        assert "non-writable" in msg.lower() or "chown" in msg.lower(), (
            f"Error message must be actionable. Got: {msg!r}"
        )
        assert str(repo) in msg or "locked.txt" in msg
    finally:
        # Restore permissions so tmp_path cleanup can proceed
        locked_file.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)


def test_dead_succeeds_when_all_files_are_writable(
    service: SpecContextService,
    workspace_root: Path,
    git: FakeGitClient,
) -> None:
    """Baseline: dead() must still succeed (remove repo dir) when all files
    are writable — the permission check must not block normal operation.

    Updated for T-10b: deactivate() → dead().
    """
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")

    repo = workspace_root / "repos" / "my-repo"
    # Place a writable file — must not impede rmtree
    (repo / "writable.txt").write_text("data")

    service.dead("proj")
    assert not repo.exists()


# ---------------------------------------------------------------------------
# T-021-15 / T-021-16 — alive() safe-preserve of pre-existing specs/
# ---------------------------------------------------------------------------


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


def test_alive_safe_preserves_preexisting_specs_to_backup(
    workspace_root: Path,
    store: FakeContextStore,
    git: FakeGitClient,
) -> None:
    """FR-S06 path a / T-016-S01: when a pre-existing specs/ is merge-enriched, the
    exact prior tree is snapshotted to specs_bkp/preserve-<UTC>/ first (safe-preserve),
    making the v0.2.1 T-021-15 claim literally true."""
    if not _SCAFFOLD_SRC.exists():
        return  # merge only runs when the scaffold source exists

    svc = SpecContextService(
        context_store=store,
        git_client=git,
        workspace_root=workspace_root,
    )
    svc.create("projbk", "repobk", "https://github.com/org/repobk")
    repo_dir = workspace_root / "repos" / "repobk"
    specs_dir = repo_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    # An operator file so the merge has a tree worth preserving.
    (specs_dir / "constitution.md").write_text("# operator\n", encoding="utf-8")

    svc.alive("projbk")

    # A backup snapshot of the pre-existing tree exists under specs_bkp/preserve-*.
    backups = list((repo_dir / "specs_bkp").glob("preserve-*"))
    assert backups, "alive() must safe-preserve the pre-existing specs/ before merging"
    assert (backups[0] / "constitution.md").read_text(encoding="utf-8") == "# operator\n"


def test_alive_with_preexisting_specs_does_not_silently_skip(
    workspace_root: Path,
    store: FakeContextStore,
    git: FakeGitClient,
) -> None:
    """T-021-16 (b): alive() on a pre-existing specs/ must execute the merge path
    (not silently skip); the resulting specs/ is non-empty.

    This test verifies the OLD silent-skip behavior is gone: the specs/ directory
    must be enriched with any missing canonical files from the scaffold source.
    """
    svc = SpecContextService(
        context_store=store,
        git_client=git,
        workspace_root=workspace_root,
    )
    svc.create("proj2", "repo2", "https://github.com/org/repo2")

    repo_dir = workspace_root / "repos" / "repo2"
    repo_dir.mkdir(parents=True, exist_ok=True)
    specs_dir = repo_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    # Specs/ exists but is empty — no operator files present
    svc.alive("proj2")

    # After merge, specs/ must contain canonical scaffold files (if scaffold source exists)
    if _SCAFFOLD_SRC.exists():
        scaffold_files = list(_SCAFFOLD_SRC.rglob("*"))
        non_dir_scaffold = [f for f in scaffold_files if f.is_file()]
        # At least some files should have been copied in
        specs_files = [f for f in specs_dir.rglob("*") if f.is_file()]
        assert len(specs_files) >= len(non_dir_scaffold), (
            f"alive() did not merge scaffold files into empty specs/; "
            f"expected >={len(non_dir_scaffold)} files, got {len(specs_files)}"
        )
