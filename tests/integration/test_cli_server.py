"""dadaia server CLI — integration tests using a real initialized workspace.

Merged per plan-integration.md (14 -> 3): (1) register/list/list --json/show;
(2) conflict + release + nonexistent-release + next/next-idempotent;
(3) clean dry-run/apply + uninitialized-workspace exit.
"""

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


def test_server_register_list_json_and_show(workspace: Path) -> None:
    empty = _runner.invoke(app, ["server", "list"])
    assert empty.exit_code == 0, empty.output
    assert "No servers registered" in empty.output

    register_result = _runner.invoke(
        app, ["server", "register", "--port", "3000", "--project", "my-frontend"]
    )
    assert register_result.exit_code == 0, register_result.output
    assert "3000" in register_result.output
    assert "my-frontend" in register_result.output

    list_result = _runner.invoke(app, ["server", "list"])
    assert list_result.exit_code == 0, list_result.output
    assert "my-frontend" in list_result.output
    assert "3000" in list_result.output

    list_json_result = _runner.invoke(app, ["server", "list", "--json"])
    assert list_json_result.exit_code == 0, list_json_result.output
    data = json.loads(list_json_result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["port"] == 3000
    assert data[0]["project"] == "my-frontend"
    assert "status" in data[0]

    show_result = _runner.invoke(app, ["server", "show", "--project", "my-frontend", "--json"])
    assert show_result.exit_code == 0, show_result.output
    show_data = json.loads(show_result.stdout)
    assert len(show_data) == 1
    assert show_data[0]["port"] == 3000

    no_entry_result = _runner.invoke(app, ["server", "show", "--project", "someone-else"])
    assert no_entry_result.exit_code == 0, no_entry_result.output
    assert "No servers registered" in no_entry_result.output
    assert "dadaia server next" in no_entry_result.output


def test_server_conflict_release_next_idempotent_clean_and_uninitialized_exit(
    workspace: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "my-frontend"])

    conflict_result = _runner.invoke(
        app, ["server", "register", "--port", "3000", "--project", "my-frontend-wave6"]
    )
    assert conflict_result.exit_code != 0

    release_result = _runner.invoke(app, ["server", "release", "--port", "3000"])
    assert release_result.exit_code == 0, release_result.output
    list_result = _runner.invoke(app, ["server", "list"])
    assert "my-frontend" not in list_result.output

    nonexistent_release_result = _runner.invoke(app, ["server", "release", "--port", "9999"])
    assert nonexistent_release_result.exit_code != 0

    next_result = _runner.invoke(app, ["server", "next", "--project", "my-service", "--json"])
    assert next_result.exit_code == 0, next_result.output
    next_data = json.loads(next_result.stdout)
    assert next_data["port"] == 3073
    assert next_data["url"] == "http://localhost:3073"
    assert next_data["is_base_port"] is True

    _runner.invoke(app, ["server", "register", "--port", "3073", "--project", "my-service"])
    next_idempotent_result = _runner.invoke(
        app, ["server", "next", "--project", "my-service", "--json"]
    )
    assert next_idempotent_result.exit_code == 0, next_idempotent_result.output
    next_idempotent_data = json.loads(next_idempotent_result.stdout)
    assert next_idempotent_data["port"] == 3073

    # clean dry-run/apply + uninitialized-workspace exit — same workspace/CLI flow.
    registry_path = workspace / ".dadaia" / "states" / "server_registry.json"

    def _plant_expired_entry() -> None:
        data = json.loads(registry_path.read_text())
        data["entries"].append(
            {
                "port": 3000,
                "project": "my-frontend",
                "url": "http://localhost:3000",
                "status": "active",
                "pid": None,
                "reserved_at": "2020-01-01T00:00:00Z",
                "expires_at": "2020-01-01T08:00:00Z",
                "description": None,
            }
        )
        registry_path.write_text(json.dumps(data))

    _plant_expired_entry()
    dry_run_result = _runner.invoke(app, ["server", "clean", "--dry-run"])
    assert dry_run_result.exit_code == 0, dry_run_result.output
    assert "3000" in dry_run_result.output
    data_after_dry_run = json.loads(registry_path.read_text())
    assert len(data_after_dry_run["entries"]) == 2

    apply_result = _runner.invoke(app, ["server", "clean"])
    assert apply_result.exit_code == 0, apply_result.output
    data_after_apply = json.loads(registry_path.read_text())
    assert [entry["port"] for entry in data_after_apply["entries"]] == [3073]

    # A genuinely separate root (not nested under the initialized `workspace`), so
    # upward .dadaia resolution never finds the initialized tree.
    uninitialized_ws = tmp_path_factory.mktemp("uninitialized")
    monkeypatch.chdir(uninitialized_ws)
    uninitialized_result = _runner.invoke(app, ["server", "list"])
    assert uninitialized_result.exit_code != 0
