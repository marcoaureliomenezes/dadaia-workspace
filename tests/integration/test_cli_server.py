"""dadaia server CLI — integration tests using a real initialized workspace."""

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
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_server_list_empty_registry(workspace: Path) -> None:
    result = _runner.invoke(app, ["server", "list"])
    assert result.exit_code == 0, result.output
    assert "No servers registered" in result.output


def test_server_register_creates_entry(workspace: Path) -> None:
    result = _runner.invoke(
        app, ["server", "register", "--port", "3000", "--project", "redacted-slug"]
    )
    assert result.exit_code == 0, result.output
    assert "3000" in result.output
    assert "redacted-slug" in result.output


def test_server_list_shows_registered_entry(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "redacted-slug"])
    result = _runner.invoke(app, ["server", "list"])
    assert result.exit_code == 0, result.output
    assert "redacted-slug" in result.output
    assert "3000" in result.output


def test_server_list_json_returns_valid_array(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "redacted-slug"])
    result = _runner.invoke(app, ["server", "list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["port"] == 3000
    assert data[0]["project"] == "redacted-slug"
    assert "status" in data[0]


def test_server_register_conflict_exits_nonzero(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "redacted-slug"])
    result = _runner.invoke(
        app, ["server", "register", "--port", "3000", "--project", "redacted-slug-wave6"]
    )
    assert result.exit_code != 0


def test_server_release_removes_entry(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "redacted-slug"])
    result = _runner.invoke(app, ["server", "release", "--port", "3000"])
    assert result.exit_code == 0, result.output
    list_result = _runner.invoke(app, ["server", "list"])
    assert "redacted-slug" not in list_result.output


def test_server_release_nonexistent_exits_nonzero(workspace: Path) -> None:
    result = _runner.invoke(app, ["server", "release", "--port", "9999"])
    assert result.exit_code != 0


def test_server_next_returns_json(workspace: Path) -> None:
    result = _runner.invoke(app, ["server", "next", "--project", "redacted-slug", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["port"] == 3537
    assert data["url"] == "http://localhost:3537"
    assert data["is_base_port"] is True


def test_server_next_idempotent_when_already_registered(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3537", "--project", "redacted-slug"])
    result = _runner.invoke(app, ["server", "next", "--project", "redacted-slug", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["port"] == 3537


def test_server_show_no_entry_prints_tip(workspace: Path) -> None:
    result = _runner.invoke(app, ["server", "show", "--project", "redacted-slug"])
    assert result.exit_code == 0, result.output
    assert "No servers registered" in result.output
    assert "dadaia server next" in result.output


def test_server_show_json_returns_entries(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "redacted-slug"])
    result = _runner.invoke(app, ["server", "show", "--project", "redacted-slug", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["port"] == 3000


def test_server_clean_dry_run_reports_stale_without_removing(workspace: Path) -> None:
    registry_path = workspace / ".dadaia" / "states" / "server_registry.json"
    data = json.loads(registry_path.read_text())
    data["entries"].append(
        {
            "port": 3000,
            "project": "redacted-slug",
            "url": "http://localhost:3000",
            "status": "active",
            "pid": None,
            "reserved_at": "2020-01-01T00:00:00Z",
            "expires_at": "2020-01-01T08:00:00Z",
            "description": None,
        }
    )
    registry_path.write_text(json.dumps(data))
    result = _runner.invoke(app, ["server", "clean", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "3000" in result.output
    data_after = json.loads(registry_path.read_text())
    assert len(data_after["entries"]) == 1


def test_server_clean_removes_expired_entries(workspace: Path) -> None:
    registry_path = workspace / ".dadaia" / "states" / "server_registry.json"
    data = json.loads(registry_path.read_text())
    data["entries"].append(
        {
            "port": 3000,
            "project": "redacted-slug",
            "url": "http://localhost:3000",
            "status": "active",
            "pid": None,
            "reserved_at": "2020-01-01T00:00:00Z",
            "expires_at": "2020-01-01T08:00:00Z",
            "description": None,
        }
    )
    registry_path.write_text(json.dumps(data))
    result = _runner.invoke(app, ["server", "clean"])
    assert result.exit_code == 0, result.output
    data_after = json.loads(registry_path.read_text())
    assert data_after["entries"] == []


def test_server_uninitialized_workspace_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["server", "list"])
    assert result.exit_code != 0
