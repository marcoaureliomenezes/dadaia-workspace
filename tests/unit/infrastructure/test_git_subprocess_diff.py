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


def test_diff_name_only_clean_repo_returns_empty_tuple(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    changed = GitSubprocessClient().diff_name_only(repo)
    assert changed == ()
    assert isinstance(changed, tuple)


def test_diff_name_only_reports_tracked_and_untracked(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.py").write_text("modified\n")
    (repo / "another.txt").write_text("x\n")

    changed = GitSubprocessClient().diff_name_only(repo)
    assert "tracked.py" in changed
    assert "another.txt" in changed
    assert isinstance(changed, tuple)
    assert all(isinstance(item, str) for item in changed)
    # No duplicates and deterministically ordered.
    assert list(changed) == sorted(set(changed))
