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


def test_ac5_v12_roundtrip_blocked_push_report_workflow_and_zero_refs_fallback(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three invocations sharing one workspace, each ``reports validate --strict`` clean:

    1. ``blocked_push_preflight`` with duplicate injected refs -> handoff-v1.2 with
       deduped self_pull.refs.
    2. ``LifecycleReportWorkflow.run`` with injected refs -> handoff-v1.2.
    3. ADR-5: zero refs + unmapped 'lifecycle' agent -> honest v1.1 fallback (never a
       fabricated self_pull) that still validates.
    """
    monkeypatch.chdir(workspace)

    # 1. blocked_push_preflight — duplicate refs dedup into self_pull.refs.
    refs = ("specs/memory/architecture.md", "specs/memory/architecture.md")
    result1 = LifecyclePreflightService().blocked_push_preflight(
        context="dadaia-workspace",
        release_id="v0.1.62",
        commit_sha="abc123",
        runtime_files=FilesystemRuntimeFileAdapter(workspace),
        run_id="push-run",
        injected_refs=refs,
    )
    handoff_path1 = workspace / result1.handoff.path
    doc1 = json.loads(handoff_path1.read_text(encoding="utf-8"))
    assert doc1["schema_version"] == "handoff-v1.2"
    assert doc1["self_pull"] == {"refs": ["specs/memory/architecture.md"]}
    assert _gate_schema_reasons(doc1) == []
    validation1 = container.build_reports_validation_service(workspace).validate_file(handoff_path1)
    assert validation1.valid is True
    cli1 = _runner.invoke(app, ["reports", "validate", "--strict", str(handoff_path1)])
    assert cli1.exit_code == 0, cli1.output

    # 2. LifecycleReportWorkflow.run — v1.2 with injected refs.
    result2 = container.build_lifecycle_report_workflow(workspace).run(
        context="dadaia-workspace",
        release_id="v0.1.62",
        run_id="report-run",
        injected_refs=("specs/memory/architecture.md",),
    )
    handoff_path2 = workspace / result2.handoff.path
    doc2 = json.loads(handoff_path2.read_text(encoding="utf-8"))
    assert doc2["schema_version"] == "handoff-v1.2"
    assert doc2["self_pull"] == {"refs": ["specs/memory/architecture.md"]}
    assert _gate_schema_reasons(doc2) == []
    assert result2.validation.valid is True
    cli2 = _runner.invoke(app, ["reports", "validate", "--strict", str(handoff_path2)])
    assert cli2.exit_code == 0, cli2.output

    # 3. ADR-5 zero-refs honest v1.1 fallback.
    result3 = container.build_lifecycle_report_workflow(workspace).run(
        context="dadaia-workspace",
        release_id="v0.1.62",
        run_id="report-run-zero",
    )
    handoff_path3 = workspace / result3.handoff.path
    doc3 = json.loads(handoff_path3.read_text(encoding="utf-8"))
    assert doc3["schema_version"] == "handoff-v1.1"
    assert "self_pull" not in doc3
    assert _gate_schema_reasons(doc3) == []
    assert result3.validation.valid is True
    cli3 = _runner.invoke(app, ["reports", "validate", "--strict", str(handoff_path3)])
    assert cli3.exit_code == 0, cli3.output
