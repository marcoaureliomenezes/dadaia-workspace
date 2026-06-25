"""OrchestrationService — read-only catalog/run-status surface + honest no-op execution.

Workflow *execution* moved to the lifecycle engine (WS-3, release
``multiharness-engine-v0116``); the reference-only ``AgentDispatcher`` layer was retired.
This service no longer takes a dispatcher and dispatches nothing. These tests pin the
read-side surface (list/show/status/runs) and the honest "moved to lifecycle" no-op.
"""

import pytest

from dadaia_workspace.core.exceptions import RunNotFoundError, WorkflowNotFoundError
from dadaia_workspace.core.models.run_state import (
    RunManifest,
    RunStatus,
    StageState,
    StageStatus,
)
from dadaia_workspace.core.models.workflow import (
    StageExpectedOutput,
    WorkflowDefinition,
    WorkflowInput,
    WorkflowStage,
)
from dadaia_workspace.features.orchestration.service import (
    EXECUTION_MOVED_MESSAGE,
    OrchestrationOutcome,
    OrchestrationService,
)
from tests.fakes import FakeRunStateStore, FakeWorkflowStore


def _wf() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="demo",
        description="demo workflow",
        version="0.1.0",
        schema_version="1",
        inputs=(WorkflowInput(name="context", type="string", required=True),),
        stages=(
            WorkflowStage(
                id="discover",
                agent="product-engineer",
                expected_output=StageExpectedOutput(path="out/discover.md"),
            ),
        ),
    )


def _service() -> tuple[OrchestrationService, FakeRunStateStore]:
    runs = FakeRunStateStore()
    service = OrchestrationService(
        workflow_store=FakeWorkflowStore([_wf()]),
        run_state_store=runs,
    )
    return service, runs


# ---------- read-only surface (KEEP) ----------


def test_list_workflows_returns_catalog() -> None:
    service, _ = _service()
    workflows = service.list_workflows()
    assert [w.name for w in workflows] == ["demo"]


def test_show_workflow_returns_definition() -> None:
    service, _ = _service()
    wf = service.show_workflow("demo")
    assert wf.name == "demo"
    assert wf.stages[0].id == "discover"


def test_show_unknown_workflow_raises() -> None:
    service, _ = _service()
    with pytest.raises(WorkflowNotFoundError):
        service.show_workflow("ghost")


def test_get_run_status_unknown_run_raises() -> None:
    service, _ = _service()
    with pytest.raises(RunNotFoundError):
        service.get_run_status("nope")


def test_list_runs_reflects_store() -> None:
    service, runs = _service()
    assert service.list_runs() == ()
    runs.create_run(
        RunManifest(
            run_id="r1",
            workflow_name="demo",
            workflow_version="0.1.0",
            context="ctx",
            runtime="cli",
            status=RunStatus.RUNNING,
            started_at="2026-06-24T00:00:00Z",
            finished_at=None,
            stages=(
                StageState(id="discover", agent="product-engineer", status=StageStatus.PENDING),
            ),
            inputs={},
        )
    )
    assert {r.run_id for r in service.list_runs()} == {"r1"}


# ---------- execution retired — honest no-op ----------


def test_start_run_does_not_dispatch_and_returns_moved_message() -> None:
    service, runs = _service()
    outcome = service.start_run("demo")
    assert isinstance(outcome, OrchestrationOutcome)
    assert outcome.dispatched is False
    assert outcome.message == EXECUTION_MOVED_MESSAGE
    assert "dadaia lifecycle" in outcome.message
    # No run state is created — nothing was executed.
    assert service.list_runs() == ()
    assert runs.manifests == {}


def test_start_run_unknown_workflow_still_raises() -> None:
    service, _ = _service()
    with pytest.raises(WorkflowNotFoundError):
        service.start_run("ghost")


def test_resume_run_does_not_dispatch_and_returns_moved_message() -> None:
    service, _ = _service()
    outcome = service.resume_run("any-run-id")
    assert outcome.dispatched is False
    assert outcome.message == EXECUTION_MOVED_MESSAGE


def test_service_constructible_without_dispatcher() -> None:
    """The dispatcher param is gone — constructing with only the two stores must work."""
    service = OrchestrationService(
        workflow_store=FakeWorkflowStore([_wf()]),
        run_state_store=FakeRunStateStore(),
    )
    assert service.list_workflows()[0].name == "demo"
