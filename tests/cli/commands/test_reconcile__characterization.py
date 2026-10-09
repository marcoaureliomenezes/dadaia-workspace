"""Characterization net for the public ``dadaia reconcile`` seam owned by CP4."""

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
    launcher.write_text("", encoding="utf-8")
    launcher.chmod(0o755)
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
    assert registry.read_bytes() == b'{\n  "schema_version": "2",\n  "contexts": []\n}'
