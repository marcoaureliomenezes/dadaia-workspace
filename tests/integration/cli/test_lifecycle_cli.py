"""Integration tests for the lifecycle CLI command group."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def test_lifecycle_help_exposes_required_command_group() -> None:
    result = _runner.invoke(app, ["lifecycle", "--help"])

    assert result.exit_code == 0, result.output
    for command in (
        "status",
        "preflight",
        "hygiene",
        "report",
        "resume",
        "backlog",
        "release",
        "implement",
        "review",
        "close",
    ):
        assert command in result.output


def test_lifecycle_hygiene_help_exposes_status_and_clean() -> None:
    result = _runner.invoke(app, ["lifecycle", "hygiene", "--help"])

    assert result.exit_code == 0, result.output
    assert "status" in result.output
    assert "clean" in result.output


def test_lifecycle_review_help_exposes_review_gates() -> None:
    result = _runner.invoke(app, ["lifecycle", "review", "--help"])

    assert result.exit_code == 0, result.output
    assert "qa" in result.output
    assert "security" in result.output
    assert "code" in result.output


def test_lifecycle_preflight_uses_blocked_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "preflight"])

    assert result.exit_code == 3
    assert "BLOCKED" in result.output


def test_lifecycle_status_uses_ok_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "status"])

    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_lifecycle_usage_error_uses_typer_exit_code() -> None:
    result = _runner.invoke(app, ["lifecycle", "resume"])

    assert result.exit_code == 2


def test_lifecycle_resume_missing_uses_internal_error_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "resume", "missing"])

    assert result.exit_code == 1
    assert "INTERNAL_ERROR" in result.output
