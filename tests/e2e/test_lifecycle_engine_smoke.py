"""End-to-end smoke for the lifecycle foundation in a disposable workspace."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
    GateRequirement,
    GateVerdict,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)
from dadaia_workspace.features.lifecycle.gates import HandoffGateValidator
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_REPO_ROOT = Path(__file__).parent.parent.parent
_HASH = "a" * 64


class _FakeRuntime:
    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="fake worker approved",
            artifact_refs=(".dadaia/handoff/dadaia-workspace/fake-worker.handoff.json",),
            structured_output={
                "verdict": "APPROVED",
                "changed_paths": ".dadaia/handoff/dadaia-workspace/fake-worker.handoff.json",
                "task_group": request.task_id or "",
            },
        )


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
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


@pytest.mark.slow(reason="initializes a full disposable workspace and runs CLI gates")
def test_temp_workspace_lifecycle_engine_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    status = _runner.invoke(app, ["lifecycle", "status", "--json"])
    assert status.exit_code == 0, status.output
    assert _payload(status.output)["status"] == "OK"

    preflight = _runner.invoke(app, ["lifecycle", "preflight", "--json"])
    assert preflight.exit_code == 3
    assert _payload(preflight.output)["status"] == "BLOCKED"

    baseline_root_entries = {path.name for path in workspace.iterdir()}
    report = _runner.invoke(
        app,
        [
            "lifecycle",
            "report",
            "--context",
            "dadaia-workspace",
            "--release-id",
            "v0.1.15",
            "--run-id",
            "smoke-run",
            "--json",
        ],
    )
    assert report.exit_code == 0, report.output
    report_payload = _payload(report.output)
    for key in ("report", "handoff", "baseline_snapshot", "final_snapshot"):
        path = _artifact_path(report_payload, key)
        assert path.startswith(".dadaia/")
        assert (workspace / path).is_file()
    assert not (workspace / "repos").exists()

    hygiene_status = _runner.invoke(app, ["lifecycle", "hygiene", "status", "--json"])
    assert hygiene_status.exit_code == 0, hygiene_status.output
    hygiene_status_payload = _payload(hygiene_status.output)
    assert hygiene_status_payload["status"] == "OK"
    counters = hygiene_status_payload["counters"]
    assert isinstance(counters, dict)
    assert isinstance(counters["unknown_top_level_dirs"], list)
    assert {path.name for path in workspace.iterdir()} == baseline_root_entries

    hygiene_dry_run = _runner.invoke(app, ["lifecycle", "hygiene", "clean", "--json"])
    assert hygiene_dry_run.exit_code == 0, hygiene_dry_run.output
    assert _payload(hygiene_dry_run.output)["dry_run"] is True

    hygiene_apply = _runner.invoke(
        app,
        ["lifecycle", "hygiene", "clean", "--apply", "--json"],
    )
    assert hygiene_apply.exit_code == 0, hygiene_apply.output
    assert _payload(hygiene_apply.output)["dry_run"] is False

    request = AgentRunRequest(
        role="qa-engineer",
        prompt="fake smoke",
        runtime=AgentRuntimeKind.FAKE,
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="smoke-task",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )
    run = LifecycleRun(
        run_id="smoke-run",
        context="dadaia-workspace",
        release_id="v0.1.15",
        command="review qa",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="implementation",
        idempotency_key="smoke-resume",
    )
    decision = LifecycleAgentRunner(runtime=_FakeRuntime()).run(
        run,
        AgentRunnerInput(
            request=request,
            target_phase=LifecyclePhase.QA_REVIEW,
            requirements=(
                GateRequirement(
                    evidence_kind=GateEvidenceKind.HANDOFF,
                    required_agent="qa-engineer",
                    required_verdict=GateVerdict.APPROVED,
                    release_id="v0.1.15",
                    task_group="smoke-task",
                ),
            ),
        ),
    )
    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.QA_REVIEW

    gate = HandoffGateValidator().validate(
        {
            "schema_version": "handoff-v1.1",
            "agent": "qa-engineer",
            "context": "dadaia-workspace",
            "release_id": "v0.1.15",
            "produced_at": "2026-06-18T12:00:00Z",
            "scope": "smoke-task",
            "metrics": {"commit_sha": "abc123", "task_group": "smoke-task"},
            "artifact": {"type": "report", "content_hash": _HASH},
            "verdict": "APPROVED",
        },
        GateRequirement(
            evidence_kind=GateEvidenceKind.HANDOFF,
            required_agent="qa-engineer",
            required_verdict=GateVerdict.APPROVED,
            release_id="v0.1.15",
            commit_sha="abc123",
            task_group="smoke-task",
        ),
        context="dadaia-workspace",
        release_id="v0.1.15",
        source=".dadaia/handoff/dadaia-workspace/smoke.handoff.json",
        artifact_hash=_HASH,
        max_age_seconds=600,
        age_seconds=10,
    )
    assert gate.accepted is True

    specs_doctor = _runner.invoke(
        app,
        ["specs", "doctor", "--specs-dir", str(_REPO_ROOT / "specs"), "--json"],
    )
    payload = _payload(specs_doctor.output)
    issues = payload["issues"]
    assert isinstance(issues, list)
    # v0.1.47 W1-9 added SPEC-DOC-037: the constitution must not enumerate AgentRuntimeKind
    # members. The LIVE constitution still enumerates them (FAKE/CODEX_EXEC/CLAUDE_SDK/
    # PI_HEADLESS + removed OPENCODE_RUN) until the W2 lean-rewrite lands, so exactly this one
    # tracked error is EXPECTED on the live tree per the release SPEC (§W1-9: "test against
    # synthetic fixtures, NOT the live file — the live constitution still enumerates until W2;
    # that's expected"). It self-clears once W2 lands. Every OTHER error is a real regression.
    real_errors = [i for i in issues if i["severity"] == "error" and i["code"] != "SPEC-DOC-037"]
    assert real_errors == [], specs_doctor.output
