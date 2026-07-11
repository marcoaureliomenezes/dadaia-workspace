"""v0.1.78 T-B / FR-B — full-pipeline success is ATOMIC with the persisted terminal state.

Bug ``full-pipeline-success-persists-running-empty-ledger``: ``LifecyclePipeline.run()``
(the full IMPLEMENTATION→QA→SECURITY→CODE ladder) returned ``PipelineResult(completed=True)``
without ever transitioning the persisted ``LifecycleRun.status`` to ``COMPLETED`` — the
run-store record was left at ``RUNNING`` with an empty ``workflow_steps`` ledger, even
though the CLI reported success. ``run_implement_review_loop`` already gets this right
(``pipeline.py`` terminal ``replace(run, status=COMPLETED)`` + save, and per-attempt
``handoff_resolver.produce`` payloads) — ``run()`` had neither.

Hermetic: real ``JsonLifecycleRunStore`` + real ``FilesystemRuntimeFileAdapter`` under
``tmp_path`` (mirrors ``test_implement_review_loop.py``'s pattern) so the assertion is on
the actual persisted-and-reloaded record, not an in-memory double.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline, implementation_ladder
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.78"


class _ApprovingRuntime:
    """Every step SUCCEEDS with an APPROVED verdict + an in-scope artifact ref."""

    def __init__(self, kind: AgentRuntimeKind) -> None:
        self._kind = kind
        self.received_requests: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return self._kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="step complete",
            artifact_refs=(f".dadaia/handoff/{_CONTEXT}/step.handoff.json",),
            structured_output={"verdict": "APPROVED"},
        )


def _build_pipeline(tmp_path: Path, runtime: _ApprovingRuntime) -> LifecyclePipeline:
    """Wire the full pipeline with a REAL handoff resolver — the production shape (T-B)."""
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-11T12:00:00Z",
    )
    return LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: runtime,  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
    )


def test_full_pipeline_success_persists_completed_status_with_nonempty_ledger(
    tmp_path: Path,
) -> None:
    """The CLI-reported success and the persisted terminal run record must AGREE.

    RED (pre-fix): ``result.completed is True`` while the reloaded run's ``status`` stayed
    ``RUNNING`` and ``workflow_steps`` stayed empty — the CLI told the operator the release
    advanced to CLOSURE while the durable record said otherwise (a re-run/resume/doctor
    reading the run store would see a stale lie). GREEN (post-fix): the reloaded record's
    ``status`` is ``COMPLETED`` and it carries a per-step handoff-ledger payload for every
    step that ran, exactly like ``run_implement_review_loop`` already does.
    """
    runtime = _ApprovingRuntime(AgentRuntimeKind.FAKE)
    pipe = _build_pipeline(tmp_path, runtime)
    run_id = "run-atomic"

    result = pipe.run(run_id, implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    assert result.final_phase is LifecyclePhase.CLOSURE

    # Reload from the REAL store (not the pipeline's in-memory returned object) — proves
    # the terminal state was actually persisted, not just constructed in memory.
    reloaded = JsonLifecycleRunStore(tmp_path).load(run_id)
    assert reloaded is not None
    assert reloaded.status is LifecycleRunStatus.COMPLETED, (
        "persisted run status must reach COMPLETED on full-pipeline success — "
        f"got {reloaded.status!r} (persisted state disagreeing with reported success "
        "is exactly bug `full-pipeline-success-persists-running-empty-ledger`)"
    )
    assert reloaded.phase is LifecyclePhase.CLOSURE
    assert len(reloaded.workflow_steps.records) == 4, (
        "every one of the 4 ladder steps must produce a run-scoped handoff-ledger payload "
        f"via the wired handoff_resolver — got {len(reloaded.workflow_steps.records)}"
    )
    produced_steps = {record.producer_step for record in reloaded.workflow_steps.records}
    assert produced_steps == {"implement", "review_qa", "review_security", "review_code"}


def test_full_pipeline_run_still_completes_with_no_handoff_resolver_wired(
    tmp_path: Path,
) -> None:
    """Back-compat: a fixture pipeline with NO handoff_resolver still completes + persists
    COMPLETED status (the ledger stays empty — additive-optional, never a hard requirement).
    """
    runtime = _ApprovingRuntime(AgentRuntimeKind.FAKE)
    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: runtime,  # type: ignore[arg-type,return-value]
    )
    run_id = "run-no-resolver"

    result = pipe.run(run_id, implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    reloaded = JsonLifecycleRunStore(tmp_path).load(run_id)
    assert reloaded is not None
    assert reloaded.status is LifecycleRunStatus.COMPLETED
    assert len(reloaded.workflow_steps.records) == 0
