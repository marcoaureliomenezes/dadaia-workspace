"""Contract tests for dadaia public CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands.public import app

pytestmark = pytest.mark.contract


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def mock_svc() -> MagicMock:
    svc = MagicMock()
    svc.list_all.return_value = {
        "agents": ["code-reviewer.md", "researcher.md"],
        "skills": ["dadaia-handoff-emitter"],
        "rules": ["workspace-protocol.md"],
    }
    svc.install.return_value = ["[ok] .claude/rules/workspace-protocol.md"]
    return svc


def _patch_svc(svc: MagicMock):
    return patch(
        "dadaia_workspace.cli.commands.public.container.build_public_service", return_value=svc
    )


def _patch_workspace(tmp_path: Path):
    return patch(
        "dadaia_workspace.cli.commands.public.resolve_workspace_root", return_value=tmp_path
    )


class TestListCommand:
    def test_list_table_json_and_invalid_format(
        self, runner: CliRunner, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            table_result = runner.invoke(app, ["list"])
        assert table_result.exit_code == 0
        assert "agents" in table_result.output
        assert "skills" in table_result.output
        assert "rules" in table_result.output

        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            json_result = runner.invoke(app, ["list", "--format", "json"])
        assert json_result.exit_code == 0
        data = json.loads(json_result.output)
        assert "agents" in data
        assert "code-reviewer.md" in data["agents"]
        assert "skills" in data

        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            invalid_result = runner.invoke(app, ["list", "--format", "csv"])
        assert invalid_result.exit_code != 0


class TestInstallOnlyFlag:
    def test_install_only_flag_pass_invalid_and_none(
        self, runner: CliRunner, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            result = runner.invoke(app, ["install", "--only", "rules"])
        assert result.exit_code == 0
        mock_svc.install.assert_called_once()
        _call_kwargs = mock_svc.install.call_args.kwargs
        assert _call_kwargs.get("only") == "rules"

        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            invalid_result = runner.invoke(app, ["install", "--only", "invalid-type"])
        assert invalid_result.exit_code != 0

        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            none_result = runner.invoke(app, ["install"])
        assert none_result.exit_code == 0
        _call_kwargs = mock_svc.install.call_args.kwargs
        assert _call_kwargs.get("only") is None
