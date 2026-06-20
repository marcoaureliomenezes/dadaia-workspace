"""Lifecycle agent runner that validates runtime output before transitions."""

from __future__ import annotations

from dataclasses import dataclass

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    BlockedState,
    GateEvidence,
    GateRequirement,
    GateVerdict,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.features.lifecycle.state_machine import (
    LifecycleStateMachine,
    TransitionDecision,
    TransitionInput,
)


@dataclass(frozen=True)
class AgentRunnerInput:
    """Inputs required to advance a lifecycle run through an agent result."""

    request: AgentRunRequest
    target_phase: LifecyclePhase
    requirements: tuple[GateRequirement, ...] = ()
    resume_token: str | None = None
    current_step: str | None = None


class LifecycleAgentRunner:
    """Execute one bounded agent request and gate state transitions on evidence."""

    def __init__(
        self,
        *,
        runtime: AgentRuntimePort,
        state_machine: LifecycleStateMachine | None = None,
    ) -> None:
        self._runtime = runtime
        self._state_machine = state_machine or LifecycleStateMachine()

    def run(self, lifecycle_run: LifecycleRun, data: AgentRunnerInput) -> TransitionDecision:
        result = self._runtime.run(data.request)
        blocked = self._blocked_result(lifecycle_run, data, result)
        if blocked is not None:
            return self._state_machine.transition(
                lifecycle_run,
                TransitionInput(
                    target_phase=LifecyclePhase.BLOCKED,
                    blocked_state=blocked,
                    current_step=data.current_step,
                ),
            )

        return self._state_machine.transition(
            lifecycle_run,
            TransitionInput(
                target_phase=data.target_phase,
                evidence=self._evidence_from_result(data.request, result),
                requirements=data.requirements,
                resume_token=data.resume_token,
                current_step=data.current_step,
            ),
        )

    def _blocked_result(
        self,
        lifecycle_run: LifecycleRun,
        data: AgentRunnerInput,
        result: AgentRunResult,
    ) -> BlockedState | None:
        if result.status is not AgentRunStatus.SUCCEEDED:
            return self._blocked(lifecycle_run, data, result.error or result.summary)
        if result.structured_output.get("verdict") != "APPROVED":
            return self._blocked(lifecycle_run, data, "agent result missing APPROVED verdict")
        if not result.artifact_refs:
            return self._blocked(lifecycle_run, data, "agent result missing artifact evidence")
        out_of_scope = self._out_of_scope_paths(
            data.request,
            (*result.artifact_refs, *self._changed_paths(result)),
        )
        if out_of_scope:
            return self._blocked(
                lifecycle_run,
                data,
                "agent result contains out-of-scope paths",
                detail={"out_of_scope": ",".join(out_of_scope)},
            )
        return None

    def _blocked(
        self,
        lifecycle_run: LifecycleRun,
        data: AgentRunnerInput,
        reason: str,
        *,
        detail: dict[str, str] | None = None,
    ) -> BlockedState:
        return BlockedState(
            reason=reason,
            blocked_at_step=data.current_step or lifecycle_run.current_step,
            resume_token=lifecycle_run.idempotency_key,
            detail=detail or {},
        )

    @staticmethod
    def _out_of_scope_paths(
        request: AgentRunRequest,
        paths: tuple[str, ...],
    ) -> tuple[str, ...]:
        out_of_scope: list[str] = []
        for path in paths:
            if any(_matches_path(path, forbidden) for forbidden in request.forbidden_paths):
                out_of_scope.append(path)
                continue
            if request.allowed_paths and not any(
                _matches_path(path, allowed) for allowed in request.allowed_paths
            ):
                out_of_scope.append(path)
        return tuple(out_of_scope)

    @staticmethod
    def _changed_paths(result: AgentRunResult) -> tuple[str, ...]:
        changed_paths = result.structured_output.get("changed_paths")
        if changed_paths is None or not changed_paths.strip():
            return ()
        return tuple(path.strip() for path in changed_paths.split(",") if path.strip())

    @staticmethod
    def _verdict_from_result(result: AgentRunResult) -> GateVerdict | None:
        verdict = result.structured_output.get("verdict")
        if verdict == GateVerdict.APPROVED.value:
            return GateVerdict.APPROVED
        if verdict == GateVerdict.REJECTED.value:
            return GateVerdict.REJECTED
        return None

    @staticmethod
    def _evidence_from_result(
        request: AgentRunRequest,
        result: AgentRunResult,
    ) -> tuple[GateEvidence, ...]:
        commit_sha = result.structured_output.get("commit_sha")
        task_group = result.structured_output.get("task_group") or request.task_id
        verdict = LifecycleAgentRunner._verdict_from_result(result)
        return tuple(
            GateEvidence(
                evidence_kind=kind,
                source=source,
                context=request.context,
                release_id=request.release_id,
                agent=request.role,
                verdict=verdict,
                commit_sha=commit_sha,
                task_group=task_group,
                metrics={"summary": result.summary},
            )
            for kind, source in zip(request.required_evidence, result.artifact_refs, strict=False)
        )


def _matches_path(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    if pattern.endswith("/*"):
        prefix = pattern[:-1]
        return path.startswith(prefix) and "/" not in path[len(prefix) :]
    return path == pattern or path.startswith(f"{pattern}/")
