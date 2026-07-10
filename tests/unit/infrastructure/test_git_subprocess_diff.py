"""Unit tests for GitSubprocessClient.diff_name_only (T-PI-06).

Drives a real throwaway git repo under pytest ``tmp_path`` (never inside the
source tree). The helper returns the worker's net changes — tracked
modifications/deletions (``git diff --name-only``) plus untracked, non-gitignored
files — so PI's Ring-2 boundary has a trustworthy, model-independent signal.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, capture_output=True)
    (path / "tracked.py").write_text("original\n")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True)


def test_diff_name_only_clean_and_dirty_repo(tmp_path: Path) -> None:
    """Clean repo -> empty tuple; a repo with tracked+untracked changes reports both,
    deduped and deterministically ordered."""
    clean_repo = tmp_path / "clean-repo"
    _init_repo(clean_repo)
    clean_changed = GitSubprocessClient().diff_name_only(clean_repo)
    assert clean_changed == ()
    assert isinstance(clean_changed, tuple)

    dirty_repo = tmp_path / "dirty-repo"
    _init_repo(dirty_repo)
    (dirty_repo / "tracked.py").write_text("modified\n")
    (dirty_repo / "another.txt").write_text("x\n")

    changed = GitSubprocessClient().diff_name_only(dirty_repo)
    assert "tracked.py" in changed
    assert "another.txt" in changed
    assert isinstance(changed, tuple)
    assert all(isinstance(item, str) for item in changed)
    # No duplicates and deterministically ordered.
    assert list(changed) == sorted(set(changed))
