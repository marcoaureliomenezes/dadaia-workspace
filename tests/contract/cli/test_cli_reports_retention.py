from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(workspace)


def _old_report(workspace: Path) -> Path:
    report = workspace / ".dadaia" / "reports" / "ctx" / "qa" / "old.html"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("<html>old</html>", encoding="utf-8")
    ts = dt.datetime(2026, 6, 1, tzinfo=dt.UTC).timestamp()
    os.utime(report, (ts, ts))
    return report


def test_reports_cleanup_dry_run_json_is_non_mutating(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    report = _old_report(tmp_path)

    result = _runner.invoke(app, ["reports", "cleanup", "--dry-run", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["dry_run"] is True
    assert payload["candidate_count"] == 1
    assert payload["deleted_count"] == 0
    assert report.exists()


def test_reports_cleanup_deletes_expired_report(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    report = _old_report(tmp_path)

    result = _runner.invoke(app, ["reports", "cleanup", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["dry_run"] is False
    assert payload["deleted_count"] == 1
    assert not report.exists()


def test_reports_mark_unmark_and_list_important(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    _old_report(tmp_path)

    marked = _runner.invoke(
        app,
        ["reports", "mark-important", "ctx/qa/old.html", "--reason", "keep"],
    )
    assert marked.exit_code == 0, marked.output

    listed = _runner.invoke(app, ["reports", "important", "--json"])
    assert listed.exit_code == 0, listed.output
    payload = json.loads(listed.output)
    assert payload["important"][".dadaia/reports/ctx/qa/old.html"]["reason"] == "keep"

    unmarked = _runner.invoke(app, ["reports", "unmark-important", "ctx/qa/old.html"])
    assert unmarked.exit_code == 0, unmarked.output
    relisted = _runner.invoke(app, ["reports", "important", "--json"])
    assert json.loads(relisted.output)["important"] == {}


def test_reports_mark_important_rejects_parent_traversal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["reports", "mark-important", "../escape.html"])

    assert result.exit_code == 2
    assert "parent traversal" in result.output


def test_reports_cleanup_rejects_invalid_duration(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["reports", "cleanup", "--older-than", "bad", "--json"])

    assert result.exit_code == 2
    assert "duration must use h or d suffix" in result.output


def test_reports_cleanup_rejects_non_positive_duration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    zero = _runner.invoke(app, ["reports", "cleanup", "--older-than", "0h"])
    negative = _runner.invoke(app, ["reports", "cleanup", "--older-than", "-1h"])

    assert zero.exit_code == 2
    assert "greater than zero" in zero.output
    assert negative.exit_code == 2
    assert "greater than zero" in negative.output


def test_reports_status_json_exposes_retention_counters(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    _old_report(tmp_path)

    result = _runner.invoke(app, ["reports", "status", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["report_count"] == 1
    assert payload["stale_report_count"] == 1
    assert payload["important_report_count"] == 0
    assert payload["malformed_state"] is False
