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


def test_lifecycle_status_json_reports_hygiene_counters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "status", "--json"])

    assert result.exit_code == 0, result.output
    payload = _json_output(result.output)
    assert payload["status"] == "OK"
    counters = payload["counters"]
    assert isinstance(counters, dict)
    assert isinstance(counters["cleanup_candidate_count"], int)


def test_lifecycle_preflight_json_returns_blocked_without_codex(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "preflight", "--json"])

    assert result.exit_code == 3
    payload = _json_output(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["message"] == "lifecycle preflight requires resolved runtime inputs"
    blocked = payload["blocked"]
    assert isinstance(blocked, dict)
    assert blocked["blocked_at_step"] == "preflight"


def test_lifecycle_hygiene_status_json_reports_counters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    stale = _write_old(workspace / ".dadaia" / "tmp" / "agent" / "old.txt")
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "hygiene", "status", "--json"])

    assert result.exit_code == 0, result.output
    assert stale.exists()
    payload = _json_output(result.output)
    counters = payload["counters"]
    assert isinstance(counters, dict)
    assert counters["cleanup_candidate_count"] >= 1


def test_lifecycle_hygiene_clean_dry_run_preserves_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    stale = _write_old(workspace / ".dadaia" / "tmp" / "agent" / "old.txt")
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "hygiene", "clean", "--dry-run", "--json"])

    assert result.exit_code == 0, result.output
    assert stale.exists()
    payload = _json_output(result.output)
    assert payload["status"] == "OK"
    assert payload["dry_run"] is True
    candidate_count = payload["candidate_count"]
    assert isinstance(candidate_count, int)
    assert candidate_count >= 1
    assert payload["deleted_paths"] == []
    candidates = payload["candidates"]
    assert isinstance(candidates, list)
    assert any(
        candidate.get("path") == ".dadaia/tmp/agent/old.txt"
        for candidate in candidates
        if isinstance(candidate, dict)
    )


def test_lifecycle_hygiene_clean_defaults_to_dry_run_without_mode_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    stale = _write_old(workspace / ".dadaia" / "tmp" / "agent" / "old.txt")
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "hygiene", "clean", "--json"])

    assert result.exit_code == 0, result.output
    assert stale.exists()
    payload = _json_output(result.output)
    assert payload["status"] == "OK"
    assert payload["dry_run"] is True
    assert payload["deleted_paths"] == []


def test_lifecycle_hygiene_clean_apply_deletes_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    stale = _write_old(workspace / ".dadaia" / "tmp" / "agent" / "old.txt")
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "hygiene", "clean", "--apply", "--json"])

    assert result.exit_code == 0, result.output
    assert not stale.exists()
    payload = _json_output(result.output)
    assert payload["status"] == "OK"
    assert payload["dry_run"] is False
    candidate_count = payload["candidate_count"]
    assert isinstance(candidate_count, int)
    assert candidate_count >= 1
    deleted_paths = payload["deleted_paths"]
    assert isinstance(deleted_paths, list)
    assert ".dadaia/tmp/agent/old.txt" in deleted_paths
