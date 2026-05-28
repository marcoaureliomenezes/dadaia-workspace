"""Unit tests for dadaia public CLI commands — T-WH-13."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands.public import app


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
    return patch("dadaia_workspace.cli.commands.public.container.build_public_service", return_value=svc)


def _patch_workspace(tmp_path: Path):
    return patch(
        "dadaia_workspace.cli.commands.public.resolve_workspace_root", return_value=tmp_path
    )


class TestListCommand:
    def test_list_table_output(self, runner: CliRunner, mock_svc: MagicMock, tmp_path: Path) -> None:
        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "agents" in result.output
        assert "skills" in result.output
        assert "rules" in result.output

    def test_list_json_output(self, runner: CliRunner, mock_svc: MagicMock, tmp_path: Path) -> None:
        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            result = runner.invoke(app, ["list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "agents" in data
        assert "code-reviewer.md" in data["agents"]
        assert "skills" in data

    def test_list_invalid_format_exits_nonzero(
        self, runner: CliRunner, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            result = runner.invoke(app, ["list", "--format", "csv"])
        assert result.exit_code != 0


class TestInstallOnlyFlag:
    def test_install_only_flag_passes_to_service(
        self, runner: CliRunner, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            result = runner.invoke(app, ["install", "--only", "rules"])
        assert result.exit_code == 0
        mock_svc.install.assert_called_once()
        _call_kwargs = mock_svc.install.call_args.kwargs
        assert _call_kwargs.get("only") == "rules"

    def test_install_only_invalid_category_exits_nonzero(
        self, runner: CliRunner, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            result = runner.invoke(app, ["install", "--only", "invalid-type"])
        assert result.exit_code != 0

    def test_install_without_only_passes_none(
        self, runner: CliRunner, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        with _patch_svc(mock_svc), _patch_workspace(tmp_path):
            result = runner.invoke(app, ["install"])
        assert result.exit_code == 0
        _call_kwargs = mock_svc.install.call_args.kwargs
        assert _call_kwargs.get("only") is None
