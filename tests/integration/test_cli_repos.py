"""dadaia repos CLI — list command."""

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


def test_repos_list_exits_cleanly(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["repos", "list"])
    assert result.exit_code == 0, result.output
