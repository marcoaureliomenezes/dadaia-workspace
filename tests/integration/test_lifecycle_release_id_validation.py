"""Bug lifecycle-accepts-noncanonical-release-id-then-generates-invalid-memory-slug.

Every lifecycle verb now validates --release-id against the canonical pattern
(vMAJOR.MINOR.PATCH with an optional -suffix) BEFORE any run/write — a noncanonical id
used to sail through definition and then break closure with an invalid memory slug.
"""

from __future__ import annotations

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
    monkeypatch.setenv("DADAIA_CONTEXT", "dadaia-workspace")
    return tmp_path


@pytest.mark.parametrize("bad_id", ["valgame-v0.1.0", "tic-tac-toe-v1", "release1"])
def test_noncanonical_release_id_is_refused_before_any_run(workspace: Path, bad_id: str) -> None:
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog-definition",
            "--release-id",
            bad_id,
            "--run-id",
            f"rid-{bad_id}",
            "--harness",
            "fake",
            "--json",
        ],
    )
    assert result.exit_code != 0, result.output
    rendered = result.output or str(result.exception)
    assert "vMAJOR.MINOR.PATCH" in rendered or "canonical" in rendered.lower()


def test_canonical_release_id_with_suffix_is_accepted(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog-definition",
            "--release-id",
            "v0.1.0-rc1",
            "--run-id",
            "rid-ok",
            "--harness",
            "fake",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
