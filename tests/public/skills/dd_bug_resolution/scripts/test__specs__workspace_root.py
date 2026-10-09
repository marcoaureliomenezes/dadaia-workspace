"""skill-script-root-walks-ignore-the-fence: every skill script that looks for the workspace
above its cwd or itself skips a root `DADAIA_FENCED_ROOTS` fences (ADR 0088) — the worktree
script's root, the dev-server registry, the release closure's worktree wait, and the fix line a
missing specs tree prints. Size: MEDIUM (real git and scripts in a tmp workspace)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.ledger_scripts import load_owner
from tests.fixtures.harness_env import suite_env
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import JOB, git, make_workspace, run


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    """A workspace whose own skill scripts are staged inside it, and a folder in it with no repo."""
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    skills = (
        "dd-gitflow-default",
        "dd-bug-resolution",
        "dd-cli-library",
        "dd-release-implementation",
    )
    for skill in skills:
        stage_skill_scripts(skill, root / ".agents/skills" / skill / "scripts")
    (root / "folder").mkdir()
    return root


def _fenced(ws: Path, script: str, *argv: str) -> subprocess.CompletedProcess[str]:
    """*script* of the staged skills, run from `ws/folder` with the workspace fenced."""
    path = next((ws / ".agents/skills").glob(f"*/scripts/{script}"))
    env = suite_env(os.environ, Path.home(), overrides={"DADAIA_FENCED_ROOTS": str(ws)})
    return subprocess.run(
        [sys.executable, str(path), *argv],
        cwd=ws / "folder", env=env, capture_output=True, text=True,
    )  # fmt: skip


def test_the_worktree_script_finds_no_root_in_a_fenced_workspace(ws: Path) -> None:
    refused = _fenced(ws, "worktree.py", "list")
    assert refused.returncode == 1
    assert "no workspace root above the cwd or this script" in refused.stderr


def test_the_dev_server_registry_finds_no_sentinel_in_a_fenced_workspace(ws: Path) -> None:
    refused = _fenced(ws, "registry.py", "list")
    assert refused.returncode == 1
    assert "no workspace sentinel above the cwd" in refused.stderr


def test_a_missing_specs_tree_names_no_fenced_workspace_cli(ws: Path) -> None:
    refused = _fenced(ws, "bugs.py", "status")
    assert refused.returncode == 1
    assert [x for x in refused.stderr.splitlines() if x.startswith("fix: ")] == [
        "fix: Operator action: re-run inside a repo that holds its specs/ tree"
    ]


def test_the_closure_waits_for_no_worktree_of_a_fenced_workspace(
    ws: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(ws / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(ws, "new", "r", JOB).returncode == 0  # an open tree: unfenced, closure waits
    wait = load_owner("dd-release-implementation", "_release_phase")._refuse_open_worktrees
    monkeypatch.setenv("DADAIA_FENCED_ROOTS", str(ws))
    assert wait(ws / "repos/r/specs") is None
