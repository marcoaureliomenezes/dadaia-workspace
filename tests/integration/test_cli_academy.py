"""dadaia academy CLI — happy path + error paths."""

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_ws(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_academy_list_empty_workspace(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path, monkeypatch)
    result = _runner.invoke(app, ["academy", "list"])
    assert result.exit_code == 0, result.output
    assert "No courses" in result.output


def test_academy_modules_lists_available_modules(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path, monkeypatch)
    result = _runner.invoke(app, ["academy", "modules"])
    assert result.exit_code == 0, result.output


def test_academy_create_valid_module(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path, monkeypatch)
    # First find a valid module number
    mods_result = _runner.invoke(app, ["academy", "modules"])
    assert mods_result.exit_code == 0
    # Module 1 should always exist
    result = _runner.invoke(app, ["academy", "create", "my-course", "--module", "1"])
    assert result.exit_code == 0, result.output
    assert "my-course" in result.output or "created" in result.output.lower()


def test_academy_create_invalid_module_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path, monkeypatch)
    result = _runner.invoke(app, ["academy", "create", "bad", "--module", "9999"])
    assert result.exit_code != 0


def test_academy_create_then_list_shows_course(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path, monkeypatch)
    _runner.invoke(app, ["academy", "create", "course-a", "--module", "1"])
    result = _runner.invoke(app, ["academy", "list"])
    assert result.exit_code == 0, result.output
    assert "course-a" in result.output


def test_academy_delete_existing_course(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path, monkeypatch)
    _runner.invoke(app, ["academy", "create", "to-delete", "--module", "1"])
    result = _runner.invoke(app, ["academy", "delete", "to-delete"])
    assert result.exit_code == 0, result.output
    assert "deleted" in result.output.lower() or "to-delete" in result.output


def test_academy_delete_nonexistent_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path, monkeypatch)
    result = _runner.invoke(app, ["academy", "delete", "ghost-course"])
    assert result.exit_code != 0


def test_academy_update_nonexistent_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path, monkeypatch)
    result = _runner.invoke(app, ["academy", "update", "ghost-course", "--module", "1"])
    assert result.exit_code != 0
