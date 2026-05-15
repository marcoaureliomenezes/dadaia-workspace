"""dadaia context CLI — happy path + error paths."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_context_create_lists_state_inativo(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    assert result.exit_code == 0, result.output
    list_out = _runner.invoke(app, ["context", "list"])
    assert "alpha" in list_out.output
    assert "inativo" in list_out.output


def test_context_show_json_returns_structured(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    result = _runner.invoke(app, ["context", "show", "alpha", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["name"] == "alpha"
    assert data["state"] == "inativo"
    assert data["is_primary"] is False


def test_context_create_rejects_duplicate(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    result = _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    assert result.exit_code != 0


def test_context_promote_requires_existing_context(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "promote", "ghost"])
    assert result.exit_code != 0


def test_context_deactivate_requires_name(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "deactivate"])
    assert result.exit_code != 0


def test_context_show_json_unknown_returns_error(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "show", "ghost", "--json"])
    assert result.exit_code != 0


def test_context_show_table_output(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "beta", "--repo", "beta"])
    result = _runner.invoke(app, ["context", "show", "beta"])
    assert result.exit_code == 0, result.output
    assert "beta" in result.output


def test_context_show_no_primary_json(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "show", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data.get("context") is None


def test_context_list_empty_workspace(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code == 0, result.output
    assert "No contexts" in result.output


def test_context_delete_inativo_context(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "to-del", "--repo", "to-del"])
    result = _runner.invoke(app, ["context", "delete", "to-del"])
    assert result.exit_code == 0, result.output
    assert "deleted" in result.output.lower() or "to-del" in result.output


def test_context_delete_nonexistent_errors(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "delete", "ghost"])
    assert result.exit_code != 0


def test_context_use_existing_context(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "myctx", "--repo", "myctx"])
    result = _runner.invoke(app, ["context", "use", "myctx"])
    assert result.exit_code == 0, result.output
    assert "DADAIA_CONTEXT=myctx" in result.output


def test_context_use_nonexistent_errors(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "use", "ghost"])
    assert result.exit_code != 0


def test_context_list_shows_primary_marker(workspace: Path) -> None:
    # Write a context directly as is_primary=True to cover the primary marker branch
    states = workspace / ".dadaia" / "states"
    ctx_data = {
        "version": "1",
        "contexts": [
            {
                "name": "primary-ctx",
                "state": "ativo",
                "repo_slug": "primary-ctx",
                "repo_url": "",
                "is_primary": True,
                "specs_dir": str(workspace / "repos" / "primary-ctx" / "specs"),
                "created_at": "2026-01-01T00:00:00Z",
                "activated_at": "2026-01-01T00:00:00Z",
            }
        ],
    }
    import json as _json

    (states / "spec_contexts.json").write_text(_json.dumps(ctx_data))
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code == 0, result.output
    assert "primary-ctx" in result.output


def test_context_workspace_not_initialized_exits(tmp_path: Path, monkeypatch) -> None:
    # No .dadaia/ → workspace not initialized
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code != 0
