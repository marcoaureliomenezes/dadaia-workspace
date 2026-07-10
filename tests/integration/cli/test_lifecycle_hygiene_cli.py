"""Integration tests for lifecycle status, preflight, and hygiene CLI behavior."""

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
_OLD = dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _write_old(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stale", encoding="utf-8")
    timestamp = _OLD.timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


def _json_output(output: str) -> dict[str, object]:
    payload = json.loads(output)
    assert isinstance(payload, dict)
    return payload


def test_lifecycle_status_and_hygiene_clean_dry_run_default_then_apply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """status counters + hygiene status counters + hygiene clean dry-run-default
    (candidates listed, file kept) + --apply deletes."""
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    status_result = _runner.invoke(app, ["lifecycle", "status", "--json"])
    assert status_result.exit_code == 0, status_result.output
    status_payload = _json_output(status_result.output)
    assert status_payload["status"] == "OK"
    status_counters = status_payload["counters"]
    assert isinstance(status_counters, dict)
    assert isinstance(status_counters["cleanup_candidate_count"], int)

    stale = _write_old(workspace / ".dadaia" / "tmp" / "agent" / "old.txt")

    hygiene_status_result = _runner.invoke(app, ["lifecycle", "hygiene", "status", "--json"])
    assert hygiene_status_result.exit_code == 0, hygiene_status_result.output
    assert stale.exists()
    hygiene_status_payload = _json_output(hygiene_status_result.output)
    hygiene_counters = hygiene_status_payload["counters"]
    assert isinstance(hygiene_counters, dict)
    assert hygiene_counters["cleanup_candidate_count"] >= 1

    # Default (no --dry-run/--apply flag) stays dry-run: candidates listed, file kept.
    default_result = _runner.invoke(app, ["lifecycle", "hygiene", "clean", "--json"])
    assert default_result.exit_code == 0, default_result.output
    assert stale.exists()
    default_payload = _json_output(default_result.output)
    assert default_payload["status"] == "OK"
    assert default_payload["dry_run"] is True
    default_candidate_count = default_payload["candidate_count"]
    assert isinstance(default_candidate_count, int)
    assert default_candidate_count >= 1
    assert default_payload["deleted_paths"] == []
    default_candidates = default_payload["candidates"]
    assert isinstance(default_candidates, list)
    assert any(
        candidate.get("path") == ".dadaia/tmp/agent/old.txt"
        for candidate in default_candidates
        if isinstance(candidate, dict)
    )

    apply_result = _runner.invoke(app, ["lifecycle", "hygiene", "clean", "--apply", "--json"])
    assert apply_result.exit_code == 0, apply_result.output
    assert not stale.exists()
    apply_payload = _json_output(apply_result.output)
    assert apply_payload["status"] == "OK"
    assert apply_payload["dry_run"] is False
    apply_candidate_count = apply_payload["candidate_count"]
    assert isinstance(apply_candidate_count, int)
    assert apply_candidate_count >= 1
    deleted_paths = apply_payload["deleted_paths"]
    assert isinstance(deleted_paths, list)
    assert ".dadaia/tmp/agent/old.txt" in deleted_paths
