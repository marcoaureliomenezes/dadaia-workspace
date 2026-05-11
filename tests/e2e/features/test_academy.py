"""E2E tests for Academy CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from tests.fakes import FakePublicAssetManager, FakePythonEnvironmentManager

runner = CliRunner()


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    svc = WorkspaceService(
        public_assets=FakePublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    )
    svc.init(root, skip_assets=True)
    return root


def test_academy_modules(workspace_root: Path) -> None:
    result = runner.invoke(app, ["--help"], catch_exceptions=False)
    # Just verify the CLI imports cleanly
    assert result.exit_code == 0
