"""dadaia export CLI — happy path + flag combinations."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()

pytestmark = pytest.mark.slow


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_export_list_create_archive_excluding_mnt_and_import_round_trip(
    workspace: Path, tmp_path: Path
) -> None:
    """--list alone creates no archive; a real export creates exactly one tar.gz; and
    --exclude-mnt skips the mnt/ subtree inside it.

    Plus: the real generated archive round-trips through ``dadaia import`` — extracting
    workspace state into a fresh destination without activation side effects (stronger
    than a hand-crafted synthetic fixture, since it exercises the actual export shape).
    """
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

    # Import round-trip: the real generated archive extracts cleanly, no activation.
    import_dest = tmp_path / "imported"
    import_result = _runner.invoke(
        app,
        [
            "import",
            str(created[0]),
            "--workspace",
            str(import_dest),
            "--skip-mnt",
            "--skip-activate",
        ],
    )
    assert import_result.exit_code == 0, import_result.output
    assert (import_dest / ".dadaia" / "states").exists()

    # Bug test-suite-real-venv-and-ci-longpole: import's bootstrap phase shells out to
    # `dadaia init`, which escapes the in-process no-real-venv backstop and built a REAL
    # venv + pip install in the destination (~19 s unloaded, 242 s on a loaded host).
    # The conftest backstop now intercepts that subprocess and runs init in-process
    # (against the source under test, venv stubbed) — a real venv materialising here
    # means the interception regressed.
    imported_venv = import_dest / ".dadaia" / ".venv"
    real_venv_files = (
        sorted(p.name for p in imported_venv.iterdir()) if imported_venv.exists() else []
    )
    assert real_venv_files == [], (
        f"import bootstrap built a REAL venv in the destination (found {real_venv_files})"
    )
