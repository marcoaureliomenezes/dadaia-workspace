"""An interrupted lifecycle run must be able to SAY what happened, when asked.

Bugs ``r9-r11-release-running-without-recovery`` and
``r9-r12-backlog-running-without-recovery`` (consumer-side validator, R9/R-11 and R-12;
R-05 hit the same wall earlier in the round). A killed driver or an orphaned worker leaves
a run persisted as ``running``: not finished, not failed, carrying no block and therefore
no remedy.

``refuse_blocked_restart`` already knows the recovery — but it only speaks when the
operator happens to re-run the identical command and trips the refusal. Whoever inspects
the run instead gets a state file that says ``running`` and nothing else, and there was no
verb at all to ask the product what to do. Knowledge that is only reachable by triggering
an error is not guidance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    BlockedState,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.contract

runner = CliRunner()


def _store(tmp_path: Path) -> JsonLifecycleRunStore:
    """A REAL initialized workspace — the CLI refuses an uninitialized one, correctly."""
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, skip_assets=True, harnesses=())
    return JsonLifecycleRunStore(tmp_path)


def _run(run_id: str, status: LifecycleRunStatus, step: str, **kw: object) -> LifecycleRun:
    return LifecycleRun(
        run_id=run_id,
        command="release_definition",
        context="ctx",
        release_id="v0.1.0",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=status,
        current_step=step,
        expected_artifacts=(),
        idempotency_key="idem",
        **kw,  # type: ignore[arg-type]
    )


def _invoke(tmp_path: Path, run_id: str, *extra: str):
    return runner.invoke(
        app, ["lifecycle", "status", "--workspace", str(tmp_path), "--run-id", run_id, *extra]
    )


def test_an_interrupted_running_run_reports_how_to_recover(tmp_path: Path) -> None:
    _store(tmp_path).save(_run("r-11", LifecycleRunStatus.RUNNING, "spec_create"))

    result = _invoke(tmp_path, "r-11")

    assert result.exit_code == 0, result.output
    assert "RUNNING" in result.output
    assert "interrupted" in result.output.lower(), (
        "a run stuck in running must say it was interrupted, not just print a status word"
    )
    assert "--resume-from spec_create" in result.output, (
        f"no recovery command offered; output was:\n{result.output}"
    )


def test_a_blocked_run_reports_its_recorded_remedy(tmp_path: Path) -> None:
    blocked = BlockedState(
        reason="plan_review: the PLAN declares no contract bindings",
        blocked_at_step="plan_review",
        resume_token="tok",
        operator_command="dadaia lifecycle release-definition --resume-from plan_create",
    )
    _store(tmp_path).save(_run("r-12", LifecycleRunStatus.BLOCKED, "plan_review", blocked=blocked))

    result = _invoke(tmp_path, "r-12")

    assert result.exit_code == 0, result.output
    assert "contract bindings" in result.output, "the recorded reason must be shown"
    assert "--resume-from plan_create" in result.output


def test_json_carries_status_step_and_recovery(tmp_path: Path) -> None:
    _store(tmp_path).save(_run("r-13", LifecycleRunStatus.RUNNING, "tasks_create"))

    result = _invoke(tmp_path, "r-13", "--json")

    payload = json.loads(result.output)
    assert payload["status"] == "running"
    assert payload["current_step"] == "tasks_create"
    assert payload["interrupted"] is True
    assert "--resume-from tasks_create" in payload["recovery"]


def test_an_unknown_run_id_is_a_loud_error_not_silence(tmp_path: Path) -> None:
    _store(tmp_path)
    result = _invoke(tmp_path, "nope")
    assert result.exit_code != 0
    assert "nope" in result.output
