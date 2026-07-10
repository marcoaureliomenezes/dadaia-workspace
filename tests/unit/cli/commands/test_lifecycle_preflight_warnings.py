"""`dadaia lifecycle preflight` surfaces advisory warnings without blocking (v0.1.76 T-4, FR7).

The service-level contract (``LifecyclePreflightResult.warnings``) is unit-tested against
``LifecyclePreflightService`` directly in ``test_preflight_service.py``. This test drives
the CLI command body to confirm an OK-with-warnings result is surfaced (never BLOCKED) in
both ``--json`` and human output.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.features.lifecycle.service import LifecyclePreflightResult
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


def test_preflight_ok_with_warnings_exits_zero_and_surfaces_warning_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    from dadaia_workspace import container
    from dadaia_workspace.cli.commands import lifecycle as lifecycle_cli
    from dadaia_workspace.features.lifecycle.service import LifecyclePreflightService

    warning_text = "[PRESENCE] another session ('sess-2') has a live presence on this context."

    monkeypatch.setattr(
        container,
        "build_lifecycle_preflight_input",
        lambda *a, **k: object(),
    )
    monkeypatch.setattr(
        LifecyclePreflightService,
        "preflight",
        lambda self, data: LifecyclePreflightResult(ok=True, warnings=(warning_text,)),
    )

    result = _runner.invoke(lifecycle_cli.app, ["preflight"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output
    assert warning_text in result.output

    json_result = _runner.invoke(lifecycle_cli.app, ["preflight", "--json"])
    assert json_result.exit_code == 0, json_result.output
    assert warning_text in json_result.output


def test_preflight_ok_without_warnings_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    from dadaia_workspace import container
    from dadaia_workspace.cli.commands import lifecycle as lifecycle_cli
    from dadaia_workspace.features.lifecycle.service import LifecyclePreflightService

    monkeypatch.setattr(
        container,
        "build_lifecycle_preflight_input",
        lambda *a, **k: object(),
    )
    monkeypatch.setattr(
        LifecyclePreflightService,
        "preflight",
        lambda self, data: LifecyclePreflightResult(ok=True),
    )

    result = _runner.invoke(lifecycle_cli.app, ["preflight"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "OK preflight passed"
