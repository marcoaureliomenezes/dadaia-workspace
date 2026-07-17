"""Bug completed-workflow-rerun-not-refused (Hermes 0.3.2 confirmation run).

A COMPLETED lifecycle run id is immutable history: EVERY workflow engine must refuse a
fresh invocation over it with one clean CompletedRunRerunError line (non-zero exit, no
traceback) — the pipeline used to silently re-execute the whole ladder, and the fragment
workflows only blocked by accident of identical re-authored content. Blocked runs stay
restartable; only COMPLETED refuses.
"""

from __future__ import annotations

import json
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


def _invoke(args: list[str]):
    return _runner.invoke(app, args)


def test_backlog_definition_completed_rerun_refused(workspace: Path) -> None:
    args = [
        "lifecycle",
        "backlog-definition",
        "--release-id",
        "v0.0.1",
        "--run-id",
        "rr-backlog",
        "--harness",
        "fake",
        "--json",
    ]
    first = _invoke(args)
    assert first.exit_code == 0, first.output
    assert json.loads(first.output)["completed"] is True

    second = _invoke(args)
    assert second.exit_code != 0, second.output
    # In-process CliRunner surfaces the exception object; the real console entry point
    # (_safe_app) renders any DadaiaError as ONE clean stderr line, never a traceback.
    rendered = second.output or str(second.exception)
    assert "already COMPLETED" in rendered
    from dadaia_workspace.core.exceptions import DadaiaError

    assert second.exception is None or isinstance(second.exception, DadaiaError)


def test_release_definition_completed_rerun_refused(workspace: Path) -> None:
    args = [
        "lifecycle",
        "release-definition",
        "--release-id",
        "v0.0.1",
        "--run-id",
        "rr-release",
        "--harness",
        "fake",
        "--json",
    ]
    first = _invoke(args)
    assert first.exit_code == 0, first.output

    second = _invoke(args)
    assert second.exit_code != 0, second.output
    # In-process CliRunner surfaces the exception object; the real console entry point
    # (_safe_app) renders any DadaiaError as ONE clean stderr line, never a traceback.
    rendered = second.output or str(second.exception)
    assert "already COMPLETED" in rendered
    from dadaia_workspace.core.exceptions import DadaiaError

    assert second.exception is None or isinstance(second.exception, DadaiaError)


def test_implementation_reviews_completed_rerun_refused(workspace: Path) -> None:
    args = [
        "lifecycle",
        "implementation-reviews",
        "--skip-preflight",
        "--release-id",
        "v0.0.1",
        "--run-id",
        "rr-impl",
        "--harness",
        "fake",
        "--json",
    ]
    first = _invoke(args)
    assert first.exit_code == 0, first.output
    assert json.loads(first.output)["completed"] is True

    second = _invoke(args)
    assert second.exit_code != 0, second.output
    # In-process CliRunner surfaces the exception object; the real console entry point
    # (_safe_app) renders any DadaiaError as ONE clean stderr line, never a traceback.
    rendered = second.output or str(second.exception)
    assert "already COMPLETED" in rendered
    from dadaia_workspace.core.exceptions import DadaiaError

    assert second.exception is None or isinstance(second.exception, DadaiaError)
