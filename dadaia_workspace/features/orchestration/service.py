"""OrchestrationService — public surface consumed by the CLI."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.exceptions import RunNotFoundError
from dadaia_workspace.core.models.run_state import (
    EventKind,
    RunManifest,
    RunStatus,
    StageInvocation,
    StageState,
    StageStatus,
    make_run_id,
)
from dadaia_workspace.core.models.workflow import WorkflowDefinition
from dadaia_workspace.core.protocols.agent_dispatcher import AgentDispatcher
from dadaia_workspace.core.protocols.run_state_store import RunStateStore
from dadaia_workspace.core.protocols.workflow_store import WorkflowStore
from dadaia_workspace.features.orchestration.runner import (
    build_invocation,
    dispatch_stages,
    emit_event,
    group_ready,
    next_ready_stages,
    stage_by_id,
    update_stage_state,
    with_status,
)


def _now(clock: Callable[[], datetime] | None) -> str:
    return (clock() if clock else datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


class OrchestrationService:
    def __init__(
        self,
        workflow_store: WorkflowStore,
        run_state_store: RunStateStore,
        dispatcher: AgentDispatcher,
        workspace_root: Path,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._workflows = workflow_store
        self._runs = run_state_store
        self._dispatcher = dispatcher
        self._workspace_root = workspace_root
        self._clock = clock

    # ---------- read-side ----------

    def list_workflows(self) -> tuple[WorkflowDefinition, ...]:
        return self._workflows.list()

    def show_workflow(self, name: str) -> WorkflowDefinition:
        return self._workflows.get(name)

    def get_run_status(self, run_id: str) -> RunManifest:
        return self._runs.load_run(run_id)

    def list_runs(self) -> tuple[RunManifest, ...]:
        return self._runs.list_runs()

    # ---------- write-side ----------

    def start_run(
        self,
        workflow_name: str,
        *,
        context: str,
        runtime: str,
        inputs: dict[str, str] | None = None,
    ) -> tuple[RunManifest, tuple[StageInvocation, ...]]:
        workflow = self._workflows.get(workflow_name)
        run_id = make_run_id(self._clock() if self._clock else None)
        now = _now(self._clock)
        manifest = RunManifest(
            run_id=run_id,
            workflow_name=workflow.name,
            workflow_version=workflow.version,
            context=context,
            runtime=runtime,
            status=RunStatus.RUNNING,
            started_at=now,
            finished_at=None,
            stages=tuple(
                StageState(id=s.id, agent=s.agent, status=StageStatus.PENDING)
                for s in workflow.stages
            ),
            inputs=inputs or {},
        )
        self._runs.create_run(manifest)
        emit_event(
            self._runs,
            run_id,
            EventKind.RUN_STARTED,
            payload={"workflow": workflow.name, "runtime": runtime, "context": context},
            clock=self._clock,
        )
        invocations = self._advance(workflow, manifest)
        return self._runs.load_run(run_id), invocations

    def resume_run(self, run_id: str) -> tuple[RunManifest, tuple[StageInvocation, ...]]:
        manifest = self._runs.load_run(run_id)
        if manifest.status == RunStatus.COMPLETED:
            return manifest, ()

        workflow = self._workflows.get(manifest.workflow_name)

        if manifest.status == RunStatus.AWAITING_GATE:
            manifest = self._resolve_awaiting_gates(manifest, workflow)

        if manifest.status == RunStatus.FAILED:
            manifest = self._reset_failed_for_retry(manifest)

        invocations = self._advance(workflow, manifest)
        return self._runs.load_run(run_id), invocations

    # ---------- internals ----------

    def _advance(
        self, workflow: WorkflowDefinition, manifest: RunManifest
    ) -> tuple[StageInvocation, ...]:
        ready = next_ready_stages(workflow, manifest)
        if not ready:
            return self._maybe_complete(workflow, manifest)

        invocations: list[StageInvocation] = []
        for group in group_ready(ready):
            run_ts = manifest.started_at.replace(":", "").replace("-", "")
            batch_invocations = tuple(
                build_invocation(
                    workflow,
                    manifest,
                    stage,
                    runs_dir=str(self._workspace_root / ".dadaia" / "runs"),
                    run_ts=run_ts,
                )
                for stage in group
            )
            for stage, inv in zip(group, batch_invocations, strict=True):
                manifest = update_stage_state(
                    manifest,
                    stage.id,
                    status=StageStatus.RUNNING,
                    started_at=_now(self._clock),
                )
                emit_event(
                    self._runs,
                    manifest.run_id,
                    EventKind.STAGE_STARTED,
                    stage_id=stage.id,
                    payload={"agent": stage.agent, "invocation": inv.invocation_path},
                    clock=self._clock,
                )
            self._runs.update_manifest(manifest)
            dispatch_stages(self._dispatcher, batch_invocations)
            for stage, inv in zip(group, batch_invocations, strict=True):
                manifest = update_stage_state(
                    manifest,
                    stage.id,
                    status=StageStatus.AWAITING_GATE,
                    output_path=inv.expected_output_path,
                )
                emit_event(
                    self._runs,
                    manifest.run_id,
                    EventKind.GATE_PENDING,
                    stage_id=stage.id,
                    payload={"reason": "host-agent-execution"},
                    clock=self._clock,
                )
            invocations.extend(batch_invocations)

        manifest = with_status(manifest, RunStatus.AWAITING_GATE, finished_at=None)
        self._runs.update_manifest(manifest)
        return tuple(invocations)

    def _maybe_complete(
        self, workflow: WorkflowDefinition, manifest: RunManifest
    ) -> tuple[StageInvocation, ...]:
        _ = workflow
        if all(s.status == StageStatus.COMPLETED for s in manifest.stages):
            now = _now(self._clock)
            manifest = with_status(manifest, RunStatus.COMPLETED, finished_at=now)
            self._runs.update_manifest(manifest)
            emit_event(
                self._runs,
                manifest.run_id,
                EventKind.RUN_COMPLETED,
                clock=self._clock,
            )
            return ()
        if any(s.status == StageStatus.FAILED for s in manifest.stages):
            now = _now(self._clock)
            manifest = with_status(manifest, RunStatus.FAILED, finished_at=now)
            self._runs.update_manifest(manifest)
            emit_event(
                self._runs,
                manifest.run_id,
                EventKind.RUN_FAILED,
                clock=self._clock,
            )
            return ()
        # Some stages still pending but none ready ⇒ wait on operator.
        manifest = with_status(manifest, RunStatus.AWAITING_GATE, finished_at=None)
        self._runs.update_manifest(manifest)
        return ()

    def _resolve_awaiting_gates(
        self, manifest: RunManifest, workflow: WorkflowDefinition
    ) -> RunManifest:
        """Resolve awaiting-gate stages: validate must_include then mark COMPLETED or FAILED."""
        new_stages: list[StageState] = []
        any_resolved = False
        for s in manifest.stages:
            if s.status != StageStatus.AWAITING_GATE:
                new_stages.append(s)
                continue
            any_resolved = True
            wf_stage = stage_by_id(workflow, s.id)
            must_include = wf_stage.expected_output.must_include
            validation_error: str | None = None
            if must_include:
                if s.output_path is None:
                    validation_error = (
                        "must_include requirements present but no output_path recorded"
                    )
                else:
                    output_file = self._workspace_root / s.output_path
                    if not output_file.exists():
                        validation_error = f"output file not found: {s.output_path}"
                    else:
                        content = output_file.read_text(encoding="utf-8")
                        missing = [item for item in must_include if item not in content]
                        if missing:
                            validation_error = f"output missing required content: {missing!r}"
            if validation_error:
                new_stages.append(
                    StageState(
                        id=s.id,
                        agent=s.agent,
                        status=StageStatus.FAILED,
                        started_at=s.started_at,
                        finished_at=_now(self._clock),
                        output_path=s.output_path,
                        error=validation_error,
                    )
                )
                emit_event(
                    self._runs,
                    manifest.run_id,
                    EventKind.STAGE_FAILED,
                    stage_id=s.id,
                    payload={"error": validation_error},
                    clock=self._clock,
                )
            else:
                new_stages.append(
                    StageState(
                        id=s.id,
                        agent=s.agent,
                        status=StageStatus.COMPLETED,
                        started_at=s.started_at,
                        finished_at=_now(self._clock),
                        output_path=s.output_path,
                        error=None,
                    )
                )
                emit_event(
                    self._runs,
                    manifest.run_id,
                    EventKind.GATE_RESOLVED,
                    stage_id=s.id,
                    clock=self._clock,
                )
                emit_event(
                    self._runs,
                    manifest.run_id,
                    EventKind.STAGE_COMPLETED,
                    stage_id=s.id,
                    clock=self._clock,
                )
        if not any_resolved:
            return manifest
        manifest = RunManifest(
            run_id=manifest.run_id,
            workflow_name=manifest.workflow_name,
            workflow_version=manifest.workflow_version,
            context=manifest.context,
            runtime=manifest.runtime,
            status=RunStatus.RUNNING,
            started_at=manifest.started_at,
            finished_at=manifest.finished_at,
            stages=tuple(new_stages),
            inputs=manifest.inputs,
        )
        self._runs.update_manifest(manifest)
        return manifest

    def _reset_failed_for_retry(self, manifest: RunManifest) -> RunManifest:
        new_stages = tuple(
            StageState(
                id=s.id,
                agent=s.agent,
                status=StageStatus.PENDING,
                started_at=None,
                finished_at=None,
                output_path=None,
                error=None,
            )
            if s.status == StageStatus.FAILED
            else s
            for s in manifest.stages
        )
        manifest = RunManifest(
            run_id=manifest.run_id,
            workflow_name=manifest.workflow_name,
            workflow_version=manifest.workflow_version,
            context=manifest.context,
            runtime=manifest.runtime,
            status=RunStatus.RUNNING,
            started_at=manifest.started_at,
            finished_at=manifest.finished_at,
            stages=new_stages,
            inputs=manifest.inputs,
        )
        self._runs.update_manifest(manifest)
        return manifest


__all__ = ["OrchestrationService", "RunNotFoundError"]
