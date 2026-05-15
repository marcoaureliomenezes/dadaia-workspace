"""dadaia import CLI — happy path + dry-run + skip flags."""

import io
import json
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.import_ import ImportResult

_runner = CliRunner()


def _archive(tmp_path: Path) -> Path:
    archive = tmp_path / "ws.tar.gz"
    manifest = {
        "version": "1",
        "exported_at": "2026-01-01T00:00:00Z",
        "workspace_root": "/old/ws",
        "dadaia_version": "0.1.0",
        "contexts": [],
        "includes": [".dadaia/states"],
        "mnt_included": False,
        "reports_included": False,
    }
    with tarfile.open(archive, "w:gz") as tar:
        payload = json.dumps(manifest).encode()
        info = tarfile.TarInfo("export-manifest.json")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
        contexts = json.dumps({"version": "1", "contexts": []}).encode()
        info2 = tarfile.TarInfo(".dadaia/states/spec_contexts.json")
        info2.size = len(contexts)
        tar.addfile(info2, io.BytesIO(contexts))
    return archive


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    return _archive(tmp_path)


def test_import_dry_run_does_not_create_workspace(archive: Path, tmp_path: Path) -> None:
    dest = tmp_path / "fresh"
    result = _runner.invoke(
        app,
        ["import", str(archive), "--workspace", str(dest), "--dry-run", "--skip-activate"],
    )
    assert result.exit_code == 0, result.output
    assert not (dest / ".dadaia" / "states").exists()


def test_import_extracts_archive(archive: Path, tmp_path: Path) -> None:
    dest = tmp_path / "imported"
    result = _runner.invoke(
        app,
        ["import", str(archive), "--workspace", str(dest), "--skip-mnt", "--skip-activate"],
    )
    assert result.exit_code == 0, result.output
    assert (dest / ".dadaia" / "states" / "spec_contexts.json").exists()


def test_import_rejects_archive_without_manifest(tmp_path: Path) -> None:
    bad = tmp_path / "bad.tar.gz"
    with tarfile.open(bad, "w:gz") as tar:
        payload = b"hi"
        info = tarfile.TarInfo("hello.txt")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    dest = tmp_path / "out"
    result = _runner.invoke(app, ["import", str(bad), "--workspace", str(dest), "--skip-activate"])
    assert result.exit_code != 0


def test_import_shows_contexts_restored(archive: Path, tmp_path: Path) -> None:
    dest = tmp_path / "restored"
    fake_result = ImportResult(
        workspace_root=dest,
        contexts_restored=("ctx-alpha",),
        errors=(),
    )
    with patch(
        "dadaia_workspace.features.import_.service.ImportService.run", return_value=fake_result
    ):
        result = _runner.invoke(
            app,
            ["import", str(archive), "--workspace", str(dest), "--skip-activate"],
        )
    assert result.exit_code == 0, result.output
    assert "ctx-alpha" in result.output or "restored" in result.output.lower()


def test_import_shows_activation_errors(archive: Path, tmp_path: Path) -> None:
    dest = tmp_path / "with-errors"
    fake_result = ImportResult(
        workspace_root=dest,
        contexts_restored=(),
        errors=("ctx-beta: git clone failed",),
    )
    with patch(
        "dadaia_workspace.features.import_.service.ImportService.run", return_value=fake_result
    ):
        result = _runner.invoke(
            app,
            ["import", str(archive), "--workspace", str(dest), "--skip-activate"],
        )
    assert result.exit_code == 0, result.output
    assert "ctx-beta" in result.output or "error" in result.output.lower()
