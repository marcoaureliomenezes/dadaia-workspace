"""Integration smoke tests for the ``dadaia lifecycle clean`` retention SWEEP (D5).

The deleter is dry-run by default and only reclaims with ``--apply``. These exercise the
real CLI wiring against a tmp_path workspace — never the real workspace.
"""

from __future__ import annotations

import datetime as dt
import json
import os
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


def _plant_stale_dir_tree(workspace: Path) -> Path:
    tree = workspace / ".dadaia" / "tmp" / "agent" / "20260101" / "stray_venv"
    tree.mkdir(parents=True, exist_ok=True)
    (tree / "pyvenv.cfg").write_bytes(b"x" * 200)
    (tree / "lib").mkdir(parents=True, exist_ok=True)
    (tree / "lib" / "mod.py").write_bytes(b"x" * 312)
    old = (dt.datetime.now(tz=dt.UTC) - dt.timedelta(days=30)).timestamp()
    for path in tree.rglob("*"):
        if path.is_file():
            os.utime(path, (old, old))
    return tree


def test_lifecycle_clean_dry_run_keeps_tree_then_apply_reclaims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    tree = _plant_stale_dir_tree(workspace)
    monkeypatch.chdir(workspace)

    dry_run_result = _runner.invoke(app, ["lifecycle", "clean", "--json"])

    assert dry_run_result.exit_code == 0, dry_run_result.output
    dry_run_payload = json.loads(dry_run_result.output)
    assert dry_run_payload["status"] == "OK"
    assert dry_run_payload["applied"] is False
    assert tree.exists(), "default invocation must NOT delete"
    assert dry_run_payload["reclaimed_bytes"] >= 512
    assert any(str(p).endswith("/stray_venv") for p in dry_run_payload["reclaimed_paths"])

    apply_result = _runner.invoke(app, ["lifecycle", "clean", "--apply", "--json"])

    assert apply_result.exit_code == 0, apply_result.output
    apply_payload = json.loads(apply_result.output)
    assert apply_payload["applied"] is True
    assert not tree.exists(), "--apply must reclaim the stale directory tree"
    assert apply_payload["reclaimed_bytes"] >= 512
    assert any(str(p).endswith("/stray_venv") for p in apply_payload["reclaimed_paths"]), (
        apply_payload["reclaimed_paths"]
    )
