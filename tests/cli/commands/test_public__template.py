"""``public install --template <id>`` saves the template; an unknown id is refused
naming the valid ids; no flag keeps the saved one; ``--help`` lists the ids. Ids come from
``TEMPLATES``/``DEFAULT_TEMPLATE_ID``, never literals.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES

pytestmark = [pytest.mark.medium, pytest.mark.slow(reason="runs the init and public install seams")]


def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
    from tests.fakes import FakePythonEnvironmentManager

    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES[:1])
    monkeypatch.chdir(tmp_path)
    return tmp_path / ".dadaia" / "states" / "agent_model_policy.json"


def _applied(overlay: Path) -> str:
    return json.loads(overlay.read_text(encoding="utf-8"))["applied_template"]


def _non_default() -> str:
    from dadaia_workspace.core.model_registry import DEFAULT_TEMPLATE_ID, TEMPLATES

    return next(t for t in TEMPLATES if t != DEFAULT_TEMPLATE_ID)


def test_template_flag_exits_0_and_writes_the_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace.cli.main import app

    overlay = _workspace(tmp_path, monkeypatch)
    x = _non_default()

    result = CliRunner().invoke(app, ["public", "install", "--template", x])

    assert result.exit_code == 0, result.output
    assert _applied(overlay) == x


def test_unknown_template_exits_nonzero_naming_valid_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace.cli.main import app
    from dadaia_workspace.core.model_registry import TEMPLATES

    overlay = _workspace(tmp_path, monkeypatch)
    runner = CliRunner()
    assert runner.invoke(app, ["public", "install", "--template", _non_default()]).exit_code == 0
    before = overlay.read_bytes()

    result = runner.invoke(app, ["public", "install", "--template", "nope"], terminal_width=200)

    assert result.exit_code != 0
    assert all(t in result.output for t in TEMPLATES)
    assert overlay.read_bytes() == before


def test_no_flag_keeps_the_saved_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dadaia_workspace.cli.main import app

    overlay = _workspace(tmp_path, monkeypatch)
    x = _non_default()
    runner = CliRunner()
    assert runner.invoke(app, ["public", "install", "--template", x]).exit_code == 0

    result = runner.invoke(app, ["public", "install"])

    assert result.exit_code == 0, result.output
    assert _applied(overlay) == x


def test_help_lists_the_template_ids() -> None:
    from dadaia_workspace.cli.main import app
    from dadaia_workspace.core.model_registry import TEMPLATES

    result = CliRunner().invoke(app, ["public", "install", "--help"], terminal_width=200)

    assert result.exit_code == 0
    assert "--template" in result.output
    assert all(t in result.output for t in TEMPLATES)
