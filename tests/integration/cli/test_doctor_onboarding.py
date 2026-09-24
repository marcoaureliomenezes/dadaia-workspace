"""`dadaia doctor` reports the derived onboarding step and refuses a ghost context.

Intent: CONTRACT — 0.4.8 FR6 AC6.1, AC6.3, AC3.1 doctor half (T-048-07). Size: MEDIUM
(integration: a real initialized workspace, a real git checkout as the level-2 repo).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES[:1])
    venv_bin = tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True, exist_ok=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n")
    entry.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    for var in ("DADAIA_CONTEXT", "DADAIA_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _register_specless_context(root: Path, name: str) -> None:
    repo = root / "repos" / name
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)  # noqa: S603, S607
    for target, source in workspace_layout.INSTALLED_GIT_HOOKS:  # what `create` installs
        shipped = (workspace_layout.public_scripts_dir() / source).read_bytes()
        (repo / ".git" / "hooks" / target).write_bytes(shipped)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": name,
                        "state": "alive",
                        "repo_slug": name,
                        "repo_url": f"file:///nowhere/{name}.git",
                        "created_at": "2026-01-01T00:00:00Z",
                        "alive_since": "2026-01-01T00:00:00Z",
                        "dead_since": None,
                        "current_branch": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _findings(output: str) -> list[dict[str, str]]:
    payload = json.loads(output)
    return [f for section in payload["sections"].values() for f in section["findings"]]


def test_zero_contexts_is_no_longer_silent(workspace: Path) -> None:
    """R2: the next step is one info finding with its fix line; the exit is unaffected."""
    result = _runner.invoke(app, ["doctor"])
    assert "ONBOARDING info Next:" in result.output, result.output
    assert f"fix: {workspace}/.dadaia/.venv/bin/dadaia context create" in result.output


@pytest.mark.slow(reason="git init subprocess")
def test_a_specless_context_is_level_two_not_an_error(workspace: Path) -> None:
    """AC3.1: right after `context create` the doctor is clean and names `specs init`."""
    _register_specless_context(workspace, "app")
    result = _runner.invoke(app, ["doctor", "--context", "app", "--json"])
    findings = _findings(result.output)
    assert [f for f in findings if f["verdict"] == "error"] == [], result.output
    assert result.exit_code == 0, result.output
    info = [f["fix"] for f in findings if f["verdict"] == "info"]
    assert any(fix.endswith("specs init --context app") for fix in info), info


def test_a_ghost_context_exits_one_with_no_specs_check(workspace: Path) -> None:
    """R4 / AC6.3: a named context that is not registered never falls back to a tree."""
    result = _runner.invoke(app, ["doctor", "--context", "ghost"])
    assert result.exit_code == 1
    assert "Error: Context 'ghost' not found." in result.output
    assert "fix: .dadaia/.venv/bin/dadaia context list" in result.output
    assert "SPEC-DOC" not in result.output
