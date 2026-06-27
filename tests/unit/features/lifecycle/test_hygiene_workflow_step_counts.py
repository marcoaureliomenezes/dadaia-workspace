"""Workflow-step payload hygiene counters (v0.1.30 Item 5 / T-30-D-07)."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_handoff import (
    RetentionMode,
    WorkflowStepConsumerRecord,
    WorkflowStepLedger,
    WorkflowStepRecord,
)
from dadaia_workspace.features.lifecycle.hygiene import LifecycleHygieneService
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia").mkdir()
    return tmp_path


def _record(
    run_id: str,
    step: str,
    *,
    consumers: tuple[str, ...] = (),
    consumed_by: tuple[str, ...] = (),
    retention: RetentionMode = RetentionMode.DELETE_AFTER_CONSUMED,
) -> WorkflowStepRecord:
    return WorkflowStepRecord(
        run_id=run_id,
        producer_step=step,
        attempt=0,
        output_schema="generic-step-handoff-v1",
        payload_ref=f".dadaia/runs/lifecycle/{run_id}/steps/{step}-attempt-0.step-payload.json",
        content_hash="a" * 64,
        produced_at="2026-06-27T12:00:00Z",
        retention_mode=retention,
        declared_consumers=consumers,
        consumptions=tuple(
            WorkflowStepConsumerRecord(consumer_step=c, consumer_attempt=0, consumed_at="t")
            for c in consumed_by
        ),
    )


def test_counts_produced_consumed_all_and_orphan(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    # one fully-consumed (cleanup-eligible) + one not-consumed; neither file exists on disk.
    run = LifecycleRun(
        run_id="r1",
        context="dadaia-workspace",
        release_id="v0.1.30",
        command="release_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.COMPLETED,
        current_step="x",
        workflow_steps=WorkflowStepLedger(
            records=(
                _record("r1", "release_scope", consumers=("spec",), consumed_by=("spec",)),
                _record("r1", "tasks", consumers=("review",)),
            )
        ),
    )
    store.save(run)

    counts = LifecycleHygieneService(workspace).workflow_step_payload_counts(store)

    assert counts.produced == 2
    assert counts.consumed_all == 1
    # Neither payload file was written to disk → both orphan.
    assert counts.orphan == 2


def test_counts_undeclared_and_malformed_on_disk(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    store.save(
        LifecycleRun(
            run_id="r2",
            context="dadaia-workspace",
            release_id="v0.1.30",
            command="release_definition",
            phase=LifecyclePhase.RELEASE_DEFINITION,
            status=LifecycleRunStatus.RUNNING,
            current_step="x",
        )
    )
    steps = workspace / ".dadaia" / "runs" / "lifecycle" / "r2" / "steps"
    steps.mkdir(parents=True)
    # An on-disk payload with no ledger record → undeclared.
    (steps / "ghost-attempt-0.step-payload.json").write_text("{}", encoding="utf-8")
    # A malformed payload → malformed.
    (steps / "bad-attempt-0.step-payload.json").write_text("{not json", encoding="utf-8")

    counts = LifecycleHygieneService(workspace).workflow_step_payload_counts(store)

    assert counts.malformed == 1
    assert counts.undeclared == 1  # the malformed one short-circuits before the undeclared check
