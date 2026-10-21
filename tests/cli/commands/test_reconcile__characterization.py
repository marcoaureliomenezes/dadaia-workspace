"""Characterization net for the public ``dadaia reconcile`` seam."""

from __future__ import annotations

import json
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
from tests.helpers.oslib import make_executable, write_text


def test_reconcile_reports_every_step_and_persists_the_v2_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES[:1])
    venv_bin = tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True)
    launcher = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    write_text(launcher, "")
    make_executable(launcher)
    registry = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    registry.write_bytes(b'{"schema_version":"1","contexts":[]}')
    monkeypatch.chdir(tmp_path)
    version = distribution_version()

    result = CliRunner().invoke(
        app,
        ["reconcile", "--expect-version", version, "--json"],
        terminal_width=200,
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "actual_version": version,
        "error": None,
        "expected_version": version,
        "ok": True,
        "rollback_required": False,
        "steps": [
            "provider-version",
            "state-schema-v2",
            "public-stage",
            "public-install",
            "public-doctor",
            "context-invariants",
            "capability-canary",
        ],
    }
    expected_registry = b'{\n  "schema_version": "3",\n  "contexts": []\n}'
    assert registry.read_bytes() == expected_registry


def test_failed_reconcile_with_rollback_prints_error_then_one_agent_fix_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace import container
    from dadaia_workspace.core import platform
    from dadaia_workspace.core.cli_line import cli_words
    from dadaia_workspace.features.reconcile.service import ReconcileResult

    failed = ReconcileResult(
        ok=False,
        expected_version="1",
        actual_version="2",
        steps=(),
        error="projection failed",
        rollback_required=True,
    )
    monkeypatch.setattr(container, "reconcile_workspace", lambda *_a, **_k: failed)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}")

    result = CliRunner().invoke(app, ["reconcile", "--expect-version", "1"], terminal_width=200)

    install = platform.inline(*cli_words(None, "public", "install"))
    assert result.exit_code == 1
    assert result.stderr.splitlines() == [
        "Error: projection failed",
        f"fix: Agent action: reinstall the previous exact provider version, then run {install}",
    ]
