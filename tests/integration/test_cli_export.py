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


def test_export_list_only_does_not_create_archive(workspace: Path) -> None:
    result = _runner.invoke(app, ["export", "--list", "--exclude-mnt"])
    assert result.exit_code == 0, result.output
    archives = (
        list((workspace / ".dadaia" / "dist").glob("*.tar.gz"))
        if (workspace / ".dadaia" / "dist").exists()
        else []
    )
    assert archives == []


def test_export_creates_archive(workspace: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    result = _runner.invoke(app, ["export", "--output", str(out), "--exclude-mnt"])
    assert result.exit_code == 0, result.output
    archives = list(out.glob("workspace-*.tar.gz"))
    assert len(archives) == 1


def test_export_exclude_mnt_skips_mnt_dir(workspace: Path, tmp_path: Path) -> None:
    (workspace / "mnt" / "redacted-infra").mkdir(parents=True)
    (workspace / "mnt" / "redacted-infra" / "marker.txt").write_text("hi")

    out = tmp_path / "out"
    out.mkdir()
    result = _runner.invoke(app, ["export", "--output", str(out), "--exclude-mnt"])
    assert result.exit_code == 0, result.output

    import tarfile

    archive = next(out.glob("workspace-*.tar.gz"))
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert not any("mnt/" in n for n in names)
