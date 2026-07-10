"""dadaia export CLI — happy path + flag combinations."""

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


def test_export_list_then_create_archive_excluding_mnt(workspace: Path, tmp_path: Path) -> None:
    """--list alone creates no archive; a real export creates exactly one tar.gz; and
    --exclude-mnt skips the mnt/ subtree inside it."""
    list_result = _runner.invoke(app, ["export", "--list", "--exclude-mnt"])
    assert list_result.exit_code == 0, list_result.output
    archives = (
        list((workspace / ".dadaia" / "dist").glob("*.tar.gz"))
        if (workspace / ".dadaia" / "dist").exists()
        else []
    )
    assert archives == []

    (workspace / "mnt" / "my-tool").mkdir(parents=True)
    (workspace / "mnt" / "my-tool" / "marker.txt").write_text("hi")

    out = tmp_path / "out"
    out.mkdir()
    result = _runner.invoke(app, ["export", "--output", str(out), "--exclude-mnt"])
    assert result.exit_code == 0, result.output
    created = list(out.glob("workspace-*.tar.gz"))
    assert len(created) == 1

    import tarfile

    with tarfile.open(created[0], "r:gz") as tar:
        names = tar.getnames()
    assert not any("mnt/" in n for n in names)
