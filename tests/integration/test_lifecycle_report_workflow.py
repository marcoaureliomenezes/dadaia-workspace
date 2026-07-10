"""Integration proof for the lifecycle report workflow command."""

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


def _payload(output: str) -> dict[str, object]:
    payload = json.loads(output)
    assert isinstance(payload, dict)
    return payload


def _artifact_path(payload: dict[str, object], key: str) -> str:
    artifact = payload[key]
    assert isinstance(artifact, dict)
    path = artifact["path"]
    assert isinstance(path, str)
    return path


def test_lifecycle_report_writes_artifacts_dry_run_default_then_apply_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default run: writes report+handoff+snapshots, dry-run cleanup (candidate kept).
    --apply-cleanup: same artifact shape, but the stale candidate is actually deleted."""
    workspace = _init_workspace(tmp_path)
    stale = _write_old(workspace / ".dadaia" / "tmp" / "agent" / "old.txt")
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "report",
            "--context",
            "dadaia-workspace",
            "--release-id",
            "v0.1.15",
            "--run-id",
            "run-report",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert stale.exists()
    payload = _payload(result.output)
    assert payload["status"] == "OK"
    assert payload["cleanup_dry_run"] is True
    assert payload["validation_valid"] is True
    assert payload["validation_hash_status"] == "match"
    for key in ("report", "handoff", "baseline_snapshot", "final_snapshot"):
        path = _artifact_path(payload, key)
        assert path.startswith(".dadaia/")
        assert (workspace / path).is_file()

    # --apply-cleanup deletes the same stale candidate; artifacts still land.
    apply_result = _runner.invoke(
        app,
        [
            "lifecycle",
            "report",
            "--context",
            "dadaia-workspace",
            "--release-id",
            "v0.1.15",
            "--run-id",
            "run-report-apply",
            "--apply-cleanup",
            "--json",
        ],
    )

    assert apply_result.exit_code == 0, apply_result.output
    apply_payload = _payload(apply_result.output)
    assert apply_payload["cleanup_dry_run"] is False
    assert not stale.exists()
    for key in ("report", "handoff", "baseline_snapshot", "final_snapshot"):
        assert (workspace / _artifact_path(apply_payload, key)).is_file()


def test_lifecycle_report_escapes_cli_controlled_html_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "report",
            "--context",
            "dadaia-workspace",
            "--release-id",
            'v0.1.15"><script>alert(1)</script>',
            "--run-id",
            "run-script-alert-1--script-",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = _payload(result.output)
    report_html = (workspace / _artifact_path(payload, "report")).read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in report_html
    assert "v0.1.15&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in report_html
