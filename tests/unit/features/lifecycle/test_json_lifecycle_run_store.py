from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore


def test_run_store_allows_temp_workspace_under_ambient_temp_git(
    tmp_path: Path, monkeypatch
) -> None:
    """Ambient temp-root `.git` must not make a standalone temp workspace look repo-local."""
    temp_root = tmp_path / "tmp"
    temp_root.mkdir()
    (temp_root / ".git").mkdir()
    workspace = temp_root / "pytest-workspace"
    (workspace / ".dadaia").mkdir(parents=True)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(temp_root))

    store = JsonLifecycleRunStore(workspace)

    assert store.root == workspace / ".dadaia" / "states" / "lifecycle"


def test_run_store_still_rejects_repo_local_dadaia_below_temp_root(
    tmp_path: Path, monkeypatch
) -> None:
    temp_root = tmp_path / "tmp"
    temp_root.mkdir()
    repo = temp_root / "repo"
    workspace = repo / "nested-workspace"
    (repo / ".git").mkdir(parents=True)
    (workspace / ".dadaia").mkdir(parents=True)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(temp_root))

    with pytest.raises(LifecycleRunStoreError, match="repository tree"):
        JsonLifecycleRunStore(workspace)
