"""Intent: CONTRACT — v0.9.0 A8.2: ``--redact`` is strictly opt-in.

Without the flag, ``context list`` still carries the true context name and never a
``[REDACTED-CONTEXT-`` placeholder, and the ``--json`` renderings of ``context list`` and
``context show`` keep their key set.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.contract

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES)

    venv_bin = tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True, exist_ok=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n")
    entry.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
        "DADAIA_CONTEXT",
    ):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _register_alive_ctx(workspace: Path, name: str = "caller-ctx") -> None:
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": name,
                        "state": "alive",
                        "repo_slug": name,
                        "repo_url": f"https://example.com/{name}.git",
                        "created_at": "2026-01-01T00:00:00Z",
                        "alive_since": "2026-01-01T00:00:00Z",
                        "dead_since": None,
                        "current_branch": "main",
                    }
                ],
            }
        )
    )
    (workspace / "repos" / name).mkdir(parents=True, exist_ok=True)


def test_context_list_default_table_output_is_unredacted(workspace: Path) -> None:
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code == 0, result.output
    assert "caller-ctx" in result.output
    assert "[REDACTED-CONTEXT-" not in result.output


_KEYS = {
    "name",
    "state",
    "main_repo",
    "repo_url",
    "created_at",
    "alive_since",
    "dead_since",
    "current_branch",
    "stored_branch",
    "associated_repos",
    "gitflow",
}


def test_context_json_key_sets_are_unchanged(workspace: Path) -> None:
    _register_alive_ctx(workspace)
    listed = _runner.invoke(app, ["context", "list", "--json"])
    shown = _runner.invoke(app, ["context", "show", "caller-ctx", "--json"])
    assert listed.exit_code == 0 and shown.exit_code == 0, listed.output + shown.output
    assert [set(row) for row in json.loads(listed.stdout)] == [_KEYS]
    assert set(json.loads(shown.stdout)) == _KEYS | {"session"}
    assert json.loads(shown.stdout)["name"] == "caller-ctx"
