"""AC-5 (v0.1.62 T-62-20) — Layer-2 emitter round-trip at handoff-v1.2.

Emit through the real service path (``blocked_push_preflight`` +
``LifecycleReportWorkflow.run``) with recorded ``InjectedContext`` refs → the emitted
document carries ``handoff-v1.2`` + ``self_pull.refs`` equal to the refs (dedup), is
accepted by ``runtime_files`` (write-time payload validation), raises no
``malformed schema_version`` in ``gates.py``, and ``dadaia reports validate --strict``
exits 0. The zero-refs run falls back to an HONEST ``handoff-v1.1`` that also
validates (ADR-5 — never a fabricated ``self_pull``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.features.lifecycle.gates import HandoffGateValidator
from dadaia_workspace.features.lifecycle.service import LifecyclePreflightService
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_runner = CliRunner()


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    memory = tmp_path / "specs" / "memory"
    memory.mkdir(parents=True, exist_ok=True)
    (memory / "architecture.md").write_text("# arch\n", encoding="utf-8")
    return tmp_path


def _gate_schema_reasons(doc: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    HandoffGateValidator()._schema_version(doc, reasons)
    return reasons


def test_ac5_blocked_push_v12_roundtrip(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    refs = ("specs/memory/architecture.md", "specs/memory/architecture.md")
    result = LifecyclePreflightService().blocked_push_preflight(
        context="dadaia-workspace",
        release_id="v0.1.62",
        commit_sha="abc123",
        runtime_files=FilesystemRuntimeFileAdapter(workspace),
        run_id="push-run",
        injected_refs=refs,
    )
    handoff_path = workspace / result.handoff.path
    doc = json.loads(handoff_path.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "handoff-v1.2"
    assert doc["self_pull"] == {"refs": ["specs/memory/architecture.md"]}
    assert _gate_schema_reasons(doc) == []
    validation = container.build_reports_validation_service(workspace).validate_file(handoff_path)
    assert validation.valid is True

    monkeypatch.chdir(workspace)
    cli = _runner.invoke(app, ["reports", "validate", "--strict", str(handoff_path)])
    assert cli.exit_code == 0, cli.output


def test_ac5_report_workflow_v12_roundtrip(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = container.build_lifecycle_report_workflow(workspace).run(
        context="dadaia-workspace",
        release_id="v0.1.62",
        run_id="report-run",
        injected_refs=("specs/memory/architecture.md",),
    )
    handoff_path = workspace / result.handoff.path
    doc = json.loads(handoff_path.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "handoff-v1.2"
    assert doc["self_pull"] == {"refs": ["specs/memory/architecture.md"]}
    assert _gate_schema_reasons(doc) == []
    assert result.validation.valid is True

    monkeypatch.chdir(workspace)
    cli = _runner.invoke(app, ["reports", "validate", "--strict", str(handoff_path)])
    assert cli.exit_code == 0, cli.output


def test_ac5_zero_refs_falls_back_to_honest_v11(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-5: zero refs + unmapped 'lifecycle' agent → honest v1.1 that validates."""
    result = container.build_lifecycle_report_workflow(workspace).run(
        context="dadaia-workspace",
        release_id="v0.1.62",
        run_id="report-run-zero",
    )
    handoff_path = workspace / result.handoff.path
    doc = json.loads(handoff_path.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "handoff-v1.1"
    assert "self_pull" not in doc
    assert _gate_schema_reasons(doc) == []
    assert result.validation.valid is True

    monkeypatch.chdir(workspace)
    cli = _runner.invoke(app, ["reports", "validate", "--strict", str(handoff_path)])
    assert cli.exit_code == 0, cli.output
