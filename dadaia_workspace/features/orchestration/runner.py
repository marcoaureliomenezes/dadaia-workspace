"""WorkflowRunner — DAG execution helpers (status propagation, parallel grouping)."""

from collections.abc import Callable
from datetime import UTC, datetime

from dadaia_workspace.core.models.run_state import (
    EventKind,
    RunEvent,
    RunManifest,
    RunStatus,
    StageInvocation,
    StageState,
    StageStatus,
)
from dadaia_workspace.core.models.workflow import WorkflowDefinition, WorkflowStage
from dadaia_workspace.core.protocols.agent_dispatcher import AgentDispatcher
from dadaia_workspace.core.protocols.run_state_store import RunStateStore
from dadaia_workspace.features.orchestration.resolver import (
    render_output_path,
    resolve_stage_inputs,
)


def _now(clock: Callable[[], datetime] | None) -> str:
    return (clock() if clock else datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


def topo_order(workflow: WorkflowDefinition) -> tuple[str, ...]:
    indeg = {s.id: len(s.needs) for s in workflow.stages}
    edges: dict[str, list[str]] = {s.id: [] for s in workflow.stages}
    for s in workflow.stages:
        for dep in s.needs:
            edges[dep].append(s.id)
    queue = [sid for sid, d in indeg.items() if d == 0]
    order: list[str] = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for nxt in edges[node]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    return tuple(order)


def stage_by_id(workflow: WorkflowDefinition, stage_id: str) -> WorkflowStage:
    for s in workflow.stages:
        if s.id == stage_id:
            return s
    raise KeyError(stage_id)


def next_ready_stages(
    workflow: WorkflowDefinition, manifest: RunManifest
) -> tuple[WorkflowStage, ...]:
    """Return stages whose deps are all completed and whose state is pending."""
    completed = {s.id for s in manifest.stages if s.status == StageStatus.COMPLETED}
    pending_ids = {s.id for s in manifest.stages if s.status == StageStatus.PENDING}
    ready: list[WorkflowStage] = []
    for s in workflow.stages:
        if s.id not in pending_ids:
            continue
        if all(dep in completed for dep in s.needs):
            ready.append(s)
    return tuple(ready)


def group_ready(ready: tuple[WorkflowStage, ...]) -> list[tuple[WorkflowStage, ...]]:
    """Group consecutive parallel_group siblings; keep singletons as singletons."""
    grouped: list[tuple[WorkflowStage, ...]] = []
    by_group: dict[str, list[WorkflowStage]] = {}
    singletons: list[WorkflowStage] = []
    for s in ready:
        if s.parallel_group:
            by_group.setdefault(s.parallel_group, []).append(s)
        else:
            singletons.append(s)
    for s in singletons:
        grouped.append((s,))
    for group_members in by_group.values():
        grouped.append(tuple(group_members))
    return grouped


def build_invocation(
    workflow: WorkflowDefinition,
    manifest: RunManifest,
    stage: WorkflowStage,
    runs_dir: str,
    run_ts: str,
) -> StageInvocation:
    rendered = render_output_path(
        stage.expected_output.path,
        run_id=manifest.run_id,
        context=manifest.context,
        run_ts=run_ts,
    )
    inputs = resolve_stage_inputs(workflow, manifest, stage)
    invocation_path = f"{runs_dir}/{manifest.run_id}/{stage.id}/invocation.md"
    return StageInvocation(
        run_id=manifest.run_id,
        stage_id=stage.id,
        workflow_name=workflow.name,
        agent=stage.agent,
        inputs=inputs,
        expected_output_path=rendered,
        must_include=stage.expected_output.must_include,
        parallel_group=stage.parallel_group,
        invocation_path=invocation_path,
    )


def update_stage_state(
    manifest: RunManifest,
    stage_id: str,
    *,
    status: StageStatus,
    started_at: str | None = None,
    finished_at: str | None = None,
    output_path: str | None = None,
    error: str | None = None,
) -> RunManifest:
    new_stages = tuple(
        StageState(
            id=s.id,
            agent=s.agent,
            status=status if s.id == stage_id else s.status,
            started_at=started_at if s.id == stage_id and started_at else s.started_at,
            finished_at=(
                finished_at if s.id == stage_id and finished_at is not None else s.finished_at
            ),
            output_path=(
                output_path if s.id == stage_id and output_path is not None else s.output_path
            ),
            error=error if s.id == stage_id and error is not None else s.error,
        )
        for s in manifest.stages
    )
    return _replace_stages(manifest, new_stages)


def _replace_stages(manifest: RunManifest, stages: tuple[StageState, ...]) -> RunManifest:
    return RunManifest(
        run_id=manifest.run_id,
        workflow_name=manifest.workflow_name,
        workflow_version=manifest.workflow_version,
        context=manifest.context,
        runtime=manifest.runtime,
        status=manifest.status,
        started_at=manifest.started_at,
        finished_at=manifest.finished_at,
        stages=stages,
        inputs=manifest.inputs,
    )


def with_status(manifest: RunManifest, status: RunStatus, finished_at: str | None) -> RunManifest:
    return RunManifest(
        run_id=manifest.run_id,
        workflow_name=manifest.workflow_name,
        workflow_version=manifest.workflow_version,
        context=manifest.context,
        runtime=manifest.runtime,
        status=status,
        started_at=manifest.started_at,
        finished_at=finished_at,
        stages=manifest.stages,
        inputs=manifest.inputs,
    )


def dispatch_stages(
    dispatcher: AgentDispatcher,
    invocations: tuple[StageInvocation, ...],
) -> tuple[StageInvocation, ...]:
    """Dispatch a parallel batch (or single stage) via the runtime dispatcher.

    Returns the invocations that were actually written (one per dispatched stage)."""
    if len(invocations) == 1:
        dispatcher.dispatch(invocations[0])
    else:
        dispatcher.dispatch_parallel(invocations)
    return invocations


def emit_event(
    store: RunStateStore,
    run_id: str,
    kind: EventKind,
    *,
    stage_id: str | None = None,
    payload: dict[str, str] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> None:
    store.append_event(
        RunEvent(
            ts=_now(clock),
            run_id=run_id,
            kind=kind,
            stage_id=stage_id,
            payload=payload,
        )
    )
