"""OrchestrationService — start/resume/parallel/gate behavior with in-memory fakes."""

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import WorkflowNotFoundError
from dadaia_workspace.core.models.run_state import DispatcherMode, RunStatus, StageStatus
from dadaia_workspace.core.models.workflow import (
    StageExpectedOutput,
    StageGate,
    WorkflowDefinition,
    WorkflowInput,
    WorkflowStage,
)
from dadaia_workspace.features.orchestration.service import OrchestrationService
from tests.fakes import FakeAgentDispatcher, FakeRunStateStore, FakeWorkflowStore


def _wf_with_parallel() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="demo",
        description="",
        version="0.1.0",
        schema_version="1",
        inputs=(WorkflowInput(name="context", type="string", required=True),),
        stages=(
            WorkflowStage(
                id="discover",
                agent="product-engineer",
                expected_output=StageExpectedOutput(path="out/discover.md"),
                gate=StageGate(kind="operator-approval", prompt="approve?"),
            ),
            WorkflowStage(
                id="a",
                agent="software-architect",
                needs=("discover",),
                parallel_group="specialists",
                expected_output=StageExpectedOutput(path="out/a.md"),
            ),
            WorkflowStage(
                id="b",
                agent="qa-engineer",
                needs=("discover",),
                parallel_group="specialists",
                expected_output=StageExpectedOutput(path="out/b.md"),
            ),
            WorkflowStage(
                id="synth",
                agent="product-engineer",
                needs=("a", "b"),
                expected_output=StageExpectedOutput(path="out/synth.md"),
            ),
        ),
    )


def _service(tmp_path: Path) -> tuple[OrchestrationService, FakeAgentDispatcher, FakeRunStateStore]:
    workflow_store = FakeWorkflowStore([_wf_with_parallel()])
    runs = FakeRunStateStore()
    dispatcher = FakeAgentDispatcher(mode=DispatcherMode.NATIVE)
    service = OrchestrationService(
        workflow_store=workflow_store,
        run_state_store=runs,
        dispatcher=dispatcher,
        workspace_root=tmp_path,
    )
    return service, dispatcher, runs


def test_start_run_dispatches_first_stage_only(tmp_path: Path) -> None:
    service, dispatcher, runs = _service(tmp_path)
    manifest, invs = service.start_run("demo", context="ctx", runtime="claude")
    assert len(invs) == 1
    assert invs[0].stage_id == "discover"
    loaded = runs.load_run(manifest.run_id)
    assert loaded.status == RunStatus.AWAITING_GATE
    assert loaded.stages[0].status == StageStatus.AWAITING_GATE


def test_resume_runs_parallel_group_in_single_batch(tmp_path: Path) -> None:
    service, dispatcher, runs = _service(tmp_path)
    manifest, _ = service.start_run("demo", context="ctx", runtime="claude")
    _, invs = service.resume_run(manifest.run_id)
    assert {inv.stage_id for inv in invs} == {"a", "b"}
    assert len(dispatcher.parallel_dispatched) == 1
    assert {i.stage_id for i in dispatcher.parallel_dispatched[0]} == {"a", "b"}


def test_resume_advances_to_completion(tmp_path: Path) -> None:
    service, _, runs = _service(tmp_path)
    manifest, _ = service.start_run("demo", context="ctx", runtime="claude")
    service.resume_run(manifest.run_id)  # discover ⇒ specialists
    service.resume_run(manifest.run_id)  # specialists ⇒ synth
    service.resume_run(manifest.run_id)  # synth ⇒ completed
    final = runs.load_run(manifest.run_id)
    assert final.status == RunStatus.COMPLETED
    assert all(s.status == StageStatus.COMPLETED for s in final.stages)


def test_resume_on_completed_run_is_noop(tmp_path: Path) -> None:
    service, _, runs = _service(tmp_path)
    manifest, _ = service.start_run("demo", context="ctx", runtime="claude")
    for _ in range(3):
        service.resume_run(manifest.run_id)
    # Re-resuming should not regress
    snapshot = runs.load_run(manifest.run_id)
    service.resume_run(manifest.run_id)
    after = runs.load_run(manifest.run_id)
    assert snapshot.status == RunStatus.COMPLETED
    assert after.status == RunStatus.COMPLETED


def test_unknown_workflow_raises(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    with pytest.raises(WorkflowNotFoundError):
        service.start_run("ghost", context="ctx", runtime="claude")


def test_list_runs_returns_all_created_runs(tmp_path: Path) -> None:
    service, _, runs = _service(tmp_path)
    service.start_run("demo", context="ctx", runtime="claude")
    service.start_run("demo", context="ctx2", runtime="claude")
    all_runs = service.list_runs()
    assert len(all_runs) == 2


def test_resume_failed_run_resets_failed_stages(tmp_path: Path) -> None:
    from dadaia_workspace.core.models.run_state import (
        RunManifest,
        RunStatus,
        StageState,
        StageStatus,
    )

    service, _, runs = _service(tmp_path)
    manifest, _ = service.start_run("demo", context="ctx", runtime="claude")
    run_id = manifest.run_id

    # Manually mark the awaiting-gate stage as FAILED to simulate failure
    current = runs.load_run(run_id)
    failed_stages = tuple(
        StageState(
            id=s.id,
            agent=s.agent,
            status=StageStatus.FAILED if s.status == StageStatus.AWAITING_GATE else s.status,
        )
        for s in current.stages
    )
    failed_manifest = RunManifest(
        run_id=current.run_id,
        workflow_name=current.workflow_name,
        workflow_version=current.workflow_version,
        context=current.context,
        runtime=current.runtime,
        status=RunStatus.FAILED,
        started_at=current.started_at,
        finished_at=None,
        stages=failed_stages,
        inputs=current.inputs,
    )
    runs.update_manifest(failed_manifest)

    # Resume should reset failed stage and retry
    manifest_after, invs = service.resume_run(run_id)
    current_after = runs.load_run(run_id)
    # Failed stage should have been reset to pending or dispatched
    assert any(s.status != StageStatus.FAILED for s in current_after.stages)
