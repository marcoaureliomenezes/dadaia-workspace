"""An overlay carrying ``overrides`` is refused with one runnable remedy that clears it (AC1.6, AC4.5)."""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.capabilities import distribution_version
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.fakes import FakePythonEnvironmentManager

_COMMAND = "public install --template max-quality"


@pytest.mark.medium
@pytest.mark.slow(reason="runs the public install, init and reconcile seams")
def test_overrides_refusal_prints_one_remedy_that_clears_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES[:1])
    venv_bin = tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True)
    launcher = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    launcher.write_text("", encoding="utf-8")
    launcher.chmod(0o755)
    overlay = tmp_path / ".dadaia" / "states" / "agent_model_policy.json"
    overlay.write_text(
        json.dumps(
            {
                "schema_version": "agent-model-policy-v1",
                "applied_template": "max-quality",
                "overrides": {"dd-software-engineer": {"model": "claude-opus-4-8"}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    refused = runner.invoke(app, ["public", "doctor"], terminal_width=200)

    assert refused.exit_code != 0
    remedies = [line for line in refused.output.splitlines() if "fix:" in line]
    assert len(remedies) == 1
    assert _COMMAND in remedies[0]

    argv = shlex.split(remedies[0].split("fix:", 1)[1], posix=not PLATFORM.windows)[1:]
    assert argv == ["public", "install", "--template", "max-quality"]
    assert runner.invoke(app, argv).exit_code == 0
    cleared = runner.invoke(app, ["public", "doctor"], terminal_width=200)
    assert cleared.exit_code == 0, cleared.output
    assert "[ok] model-resolution" in cleared.output.splitlines()[-1]

    assert runner.invoke(app, ["public", "install"]).exit_code == 0
    assert runner.invoke(app, ["init", str(tmp_path), "--harness", "claude"]).exit_code == 0
    reconciled = runner.invoke(app, ["reconcile", "--expect-version", distribution_version()])
    assert reconciled.exit_code == 0, reconciled.output
