"""CLI coverage for the runnable bug_report lifecycle workflow."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_bug_report_workflow_is_runnable_from_lifecycle_cli(tmp_path: Path, monkeypatch) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "bug",
            "report",
            "--release-id",
            "v9.9.9",
            "--run-id",
            "bug-cli-smoke",
            "--summary",
            "Lifecycle bug-report command was not runnable.",
            "--repro",
            "dadaia lifecycle bug --help",
            "--expected",
            "A runnable bug-report workflow command exists.",
            "--actual",
            "Only the policy/catalog entry existed.",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "OK"
    assert payload["completed"] is True
    assert [step["label"] for step in payload["steps"]] == [
        "bug_intake",
        "dedupe",
        "bug_write",
        "bug_record_gate",
    ]
    written = sorted((workspace / "specs" / "bugs").glob("*.md"))
    assert len(written) == 1
    content = written[0].read_text(encoding="utf-8")
    assert "Lifecycle bug-report command was not runnable." in content
    assert "dadaia lifecycle bug --help" in content
    assert "A runnable bug-report workflow command exists." in content
    assert "Only the policy/catalog entry existed." in content
    assert "Fake bug-report workflow record" not in content
    assert "session_id: null" in content

    doctor = _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(workspace / "specs")])
    assert "TREE-7" not in doctor.output
