"""dadaia academy CLI — one journey fn: modules -> create -> list shows -> delete.

Merged per plan-integration.md (8 -> 1). Deleted (unit-ownable exit-nonzero greps):
create-invalid-module, delete-nonexistent, update-nonexistent, and the empty-list
wording assert.
"""

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


def test_academy_journey_modules_create_list_delete(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path, monkeypatch)

    mods_result = _runner.invoke(app, ["academy", "modules"])
    assert mods_result.exit_code == 0, mods_result.output

    create_result = _runner.invoke(app, ["academy", "create", "course-a", "--module", "1"])
    assert create_result.exit_code == 0, create_result.output

    list_result = _runner.invoke(app, ["academy", "list"])
    assert list_result.exit_code == 0, list_result.output
    assert "course-a" in list_result.output

    delete_result = _runner.invoke(app, ["academy", "delete", "course-a"])
    assert delete_result.exit_code == 0, delete_result.output
