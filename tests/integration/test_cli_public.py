"""dadaia public CLI — stage / install / doctor commands."""

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_ws(tmp_path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    return tmp_path


def test_public_stage_runs_without_error(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "stage"])
    assert result.exit_code == 0, result.output


def test_public_stage_prints_staged_or_nothing(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "stage"])
    assert result.exit_code == 0, result.output
    # Either staged some assets or printed the "nothing" message
    assert "staged" in result.output.lower() or "No assets" in result.output


def test_public_install_runs_without_error(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "install"])
    assert result.exit_code == 0, result.output


def test_public_install_with_target_all(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "install", "--target", "all"])
    assert result.exit_code == 0, result.output


def test_public_install_force_flag(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "install", "--force"])
    assert result.exit_code == 0, result.output


def test_public_doctor_runs_without_error(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "doctor"])
    assert result.exit_code == 0, result.output


def test_public_doctor_outputs_ok_or_missing(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "doctor"])
    assert result.exit_code == 0, result.output
    # Output contains at least one status indicator
    output = result.output
    assert any(tag in output for tag in ("[ok]", "[missing]", "[drift]", "[unsupported]", "No"))
