"""dadaia import CLI integration journey."""

import io
import json
import tarfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()
pytestmark = [pytest.mark.integration, pytest.mark.slow]


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


def test_import_extracts_archive(archive: Path, tmp_path: Path) -> None:
    """Import extracts workspace state from an archive without activation side effects."""
    dest = tmp_path / "imported"
    result = _runner.invoke(
        app,
        ["import", str(archive), "--workspace", str(dest), "--skip-mnt", "--skip-activate"],
    )
    assert result.exit_code == 0, result.output
    assert (dest / ".dadaia" / "states" / "spec_contexts.json").exists()
