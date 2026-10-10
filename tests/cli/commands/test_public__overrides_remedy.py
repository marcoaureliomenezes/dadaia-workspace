"""An overlay carrying ``overrides`` is refused with one runnable remedy that clears it (AC1.6, AC4.5)."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli import main as cli_main
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.capabilities import distribution_version
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.fakes import FakePythonEnvironmentManager

_COMMAND = "public install --template max-quality"


def _refused_workspace(tmp_path: Path) -> None:
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
                "overrides": {"dd-software-engineer": {"effort": "medium"}},
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.medium
@pytest.mark.slow(reason="runs the public install, init and reconcile seams")
def test_overrides_refusal_prints_one_remedy_that_clears_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _refused_workspace(tmp_path)
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


@pytest.mark.medium
def test_stale_stage_before_the_refusal_still_prints_the_refusal_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _refused_workspace(tmp_path)
    staged = tmp_path / ".dadaia/agentic/schemas/agent-model-policy-v1.schema.json"
    staged.write_text(staged.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    refused = runner.invoke(app, ["public", "doctor"], terminal_width=200)

    remedies = [line for line in refused.output.splitlines() if "fix:" in line]
    assert len(remedies) == 1
    assert _COMMAND in remedies[0]
    argv = shlex.split(remedies[0].split("fix:", 1)[1], posix=not PLATFORM.windows)[1:]
    assert runner.invoke(app, argv).exit_code == 0
    assert runner.invoke(app, ["public", "doctor"], terminal_width=200).exit_code == 0


@pytest.mark.medium
@pytest.mark.parametrize(
    "verb",
    [
        pytest.param(["public", "install"], id="public-install"),
        pytest.param(["init", "{ws}", "--harness", "claude"], id="init-rerun"),
        pytest.param(["reconcile", "--expect-version", "{version}"], id="reconcile"),
    ],
)
def test_refusal_reaches_the_user_through_the_cli_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    verb: list[str],
) -> None:
    _refused_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    argv = [a.format(ws=tmp_path, version=distribution_version()) for a in verb]
    monkeypatch.setattr(sys, "argv", ["dadaia", *argv])

    with pytest.raises(SystemExit) as raised:
        cli_main._safe_app()

    err = capsys.readouterr().err
    assert raised.value.code == 1
    assert "unexpected" not in err
    assert "overrides" in err
    assert "fix:" in err
    assert _COMMAND in err
