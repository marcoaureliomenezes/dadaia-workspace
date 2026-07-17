"""Bug implementation-review-approves-unexecuted-validation (Hermes real game cycle).

The pipeline closed a release whose final payload listed every pytest command as
"planned / not run" — and the generated environment could not even run pytest. Closure
is a promotion decision: when an executed-test gate is wired, the `close` step now
COMPLETES only on an EXECUTED, GREEN test run (Python-owned evidence, never a worker
self-report). A workspace with no declared tests (gate yields None) is unaffected.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline, implementation_ladder
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.3.1"


class _ApprovingRuntime:
    def __init__(self) -> None:
        self.received: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received.append(request)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="step complete",
            artifact_refs=(f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json",),
            structured_output={"verdict": "APPROVED"},
        )


def _pipeline(tmp_path: Path, gate) -> LifecyclePipeline:
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-17T12:00:00Z",
    )
    return LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ApprovingRuntime(),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        executed_test_gate=gate,
    )


def test_close_blocks_when_executed_tests_are_red(tmp_path: Path) -> None:
    pipe = _pipeline(tmp_path, lambda: (False, "1 failed, 3 passed"))

    result = pipe.run("close-red", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is False
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "close"
    assert "executed test validation" in result.blocked.reason
    assert "1 failed" in str(result.blocked.detail)
    reloaded = JsonLifecycleRunStore(tmp_path).load("close-red")
    assert reloaded is not None and reloaded.status is LifecycleRunStatus.BLOCKED


def test_close_completes_on_green_executed_tests(tmp_path: Path) -> None:
    pipe = _pipeline(tmp_path, lambda: (True, "12 passed"))
    result = pipe.run("close-green", implementation_ladder(AgentRuntimeKind.FAKE))
    assert result.completed is True


def test_close_unaffected_when_no_tests_are_declared(tmp_path: Path) -> None:
    pipe = _pipeline(tmp_path, lambda: (None, "no test paths declared"))
    result = pipe.run("close-none", implementation_ladder(AgentRuntimeKind.FAKE))
    assert result.completed is True
