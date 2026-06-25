"""Integration smoke tests for the ``dadaia lifecycle slop`` metric command (WS-6)."""

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


def _plant_stray_dir_tree(workspace: Path) -> None:
    tree = workspace / ".dadaia" / "tmp" / "agent" / "20260101" / "stray_venv"
    tree.mkdir(parents=True, exist_ok=True)
    (tree / "pyvenv.cfg").write_bytes(b"x" * 200)
    (tree / "lib").mkdir(parents=True, exist_ok=True)
    (tree / "lib" / "mod.py").write_bytes(b"x" * 312)
    old = (dt.datetime.now(tz=dt.UTC) - dt.timedelta(days=30)).timestamp()
    for path in tree.rglob("*"):
        if path.is_file():
            os.utime(path, (old, old))


def test_lifecycle_slop_json_returns_valid_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    _plant_stray_dir_tree(workspace)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "slop", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "OK"
    assert isinstance(payload["total_entries"], int)
    assert isinstance(payload["reclaimable_bytes"], int)
    assert isinstance(payload["entries"], list)
    assert isinstance(payload["top_offenders"], list)
    # The planted directory tree must appear as ONE directory entry (not per-file).
    venv_entries = [
        entry
        for entry in payload["entries"]
        if isinstance(entry, dict) and str(entry.get("path", "")).endswith("/stray_venv")
    ]
    assert len(venv_entries) == 1
    assert venv_entries[0]["is_dir"] is True
    assert venv_entries[0]["size_bytes"] == 512


def test_lifecycle_slop_text_output_is_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    _plant_stray_dir_tree(workspace)
    planted = workspace / ".dadaia" / "tmp" / "agent" / "20260101" / "stray_venv" / "pyvenv.cfg"
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "slop"])

    assert result.exit_code == 0, result.output
    assert result.output.startswith("OK entries=")
    assert planted.exists(), "the metric must never delete anything"
