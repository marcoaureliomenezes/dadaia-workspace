"""FR2 (v0.1.68) — a terminal APPROVED review must not declare a phantom consumer.

RED-first executed-path proof for
``implement-review-completed-run-leaves-unconsumed-required-payload`` (SPEC
AC2(repro)): ``dadaia lifecycle implement-review`` on the fake harness reaches
APPROVED on its first round, then ``WorkflowHandoffDoctor.run()`` over the SAME run
store must report ``ok is True`` — no ``unconsumed_required`` finding. On current
(pre-FR2) code ``run_implement_review_loop`` declares
``declared_consumers=(implement_step.label,)`` on EVERY review round, including the
terminal APPROVED one — but a terminal run never runs another implement attempt, so
that declared consumer can never run and the doctor's unconsumed-required gate fires.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.workflow_handoff import WorkflowStepConsumptionState
from dadaia_workspace.features.lifecycle.workflow_handoff_doctor import (
    WorkflowHandoffFindingKind,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_RELEASE = "v0.1.68"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_terminal_implement_review_leaves_no_unconsumed_required(workspace: Path) -> None:
    """AC2(repro) RED half — T-68-03.

    Drives ``implement-review`` to APPROVED on the fake harness (the default driving
    fake returns an APPROVED in-scope handoff on round 0), then runs the read-only
    ``WorkflowHandoffDoctor`` over the exact same run store. CONFIRM RED: on current
    code the terminal review payload's over-declared ``implement`` consumer is never
    fulfilled, so the doctor reports ``ok=False`` with an ``unconsumed_required``
    finding pointing at the review payload.
    """
    run_id = "fr2-terminal-repro"
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--run-id",
            run_id,
            "--harness",
            "fake",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["completed"] is True
    assert payload["final_verdict"] == "APPROVED"

    # FR2 (AC2.1): the terminal APPROVED review payload declares NO consumer — the
    # producer already knows the verdict at produce time, so it never over-declares an
    # implement consumer that can structurally never run after the loop completes.
    run = container.build_lifecycle_run_store(workspace).load(run_id)
    assert run is not None
    review_record = run.workflow_steps.find("review_qa", 0)
    assert review_record is not None
    assert review_record.declared_consumers == (), (
        "a terminal APPROVED review round must declare zero consumers — the prior "
        "unconditional (implement_step.label,) declaration is exactly the defect "
        "this task fixes"
    )
    assert review_record.consumption_state() is WorkflowStepConsumptionState.PRODUCED

    doctor = container.build_workflow_handoff_doctor(workspace)
    report = doctor.run()

    assert report.ok is True, (
        "a terminal APPROVED implement-review run must pass handoffs doctor with no "
        f"unconsumed_required finding; findings={[f.to_dict() for f in report.findings]!r}"
    )
    assert not any(
        f.kind is WorkflowHandoffFindingKind.UNCONSUMED_REQUIRED for f in report.findings
    )
