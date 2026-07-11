"""Lifecycle agent runner that validates runtime output before transitions."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    BlockedState,
    GateEvidence,
    GateRequirement,
    GateVerdict,
    InjectedContext,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.core.scope_match import out_of_scope_paths
from dadaia_workspace.features.lifecycle.context_selector import SelectionAudit
from dadaia_workspace.features.lifecycle.state_machine import (
    LifecycleStateMachine,
    TransitionDecision,
    TransitionInput,
)


def record_injected_context(
    lifecycle_run: LifecycleRun,
    audit: SelectionAudit,
) -> LifecycleRun:
    """Append a context-selection audit entry to the run record.

    Returns a new :class:`LifecycleRun` whose ``injected_context`` carries the
    fragment ids and resolved dynamic-context refs that were injected for a step,
    making context selection auditable (epic §8.8). The run record is the persisted
    audit seam — callers persist the returned run via the lifecycle run store.
    """
    entry = audit.to_injected_context()
    return replace_injected_context(lifecycle_run, (*lifecycle_run.injected_context, entry))


def record_prompt_composition(
    lifecycle_run: LifecycleRun,
    step: str,
    *,
    prefix_hash: str | None,
    model: str | None,
    runtime_kind: str | None,
    output_schema: str | None,
    gate_result: str | None,
) -> LifecycleRun:
    """Enrich the run's *step* audit entry with WS-9 prompt-composition fields.

    The WS-4 seam (:func:`record_injected_context`) records fragment ids + resolved
    refs before the worker runs; this completes the same entry once the step's prompt
    is built and its gate has decided, persisting the prefix hash, discrete model,
    runtime kind, output schema, and gate verdict. It updates the existing entry for
    *step* (the most recent one) in place rather than appending a duplicate, so the run
    record carries exactly one composition record per step.
    """
    entries = list(lifecycle_run.injected_context)
    target = next((i for i in reversed(range(len(entries))) if entries[i].step == step), None)
    enriched = InjectedContext(
        step=step,
        fragment_ids=entries[target].fragment_ids if target is not None else (),
        refs=entries[target].refs if target is not None else (),
        policies=entries[target].policies if target is not None else (),
        prefix_hash=prefix_hash,
        model=model,
        runtime_kind=runtime_kind,
        output_schema=output_schema,
        gate_result=gate_result,
    )
    if target is None:
        entries.append(enriched)
    else:
        entries[target] = enriched
    return replace_injected_context(lifecycle_run, tuple(entries))


def replace_injected_context(
    lifecycle_run: LifecycleRun,
    entries: tuple[InjectedContext, ...],
) -> LifecycleRun:
    """Return a copy of *lifecycle_run* with its ``injected_context`` replaced.

    Uses ``dataclasses.replace`` so every other field — including the additive
    ``workflow_policy`` governance snapshot (T-28-A-07) — is preserved verbatim. A manual
    reconstruction here previously dropped any new field, which would silently erase the
    run's resolved-policy snapshot.
    """
    return replace(lifecycle_run, injected_context=entries)


@dataclass(frozen=True)
class AgentRunnerInput:
    """Inputs required to advance a lifecycle run through an agent result."""

    request: AgentRunRequest
    target_phase: LifecyclePhase
    requirements: tuple[GateRequirement, ...] = ()
    resume_token: str | None = None
    current_step: str | None = None
    # Whether this is a REVIEW step (v0.1.31 / L1). The verdict gate
    # (``structured_output["verdict"] == "APPROVED"``) applies ONLY to review steps. A
    # create step (``is_review=False``) passes on a schema-valid payload — which is what
    # populates ``artifact_refs`` — + in-scope paths, regardless of the ``verdict`` field
    # (L2 / GRILL D-1/D-2). Threaded from each step's review signal at every call site.
    is_review: bool = False


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

    def evaluate_gate(
        self, lifecycle_run: LifecycleRun, data: AgentRunnerInput
    ) -> BlockedState | None:
        """Run the request and return the gate's :class:`BlockedState`, or ``None`` if it passes.

        This is the gate decision *without* a phase transition — used by multi-step
        workflows (WS-5) where several bounded worker steps run inside one phase before
        a single terminal step transitions the release. ``None`` means the gate passed;
        a non-``None`` :class:`BlockedState` carries the rejection/missing-evidence
        reason. The pass condition is **review-only** for the verdict (v0.1.31 / L1): a
        **review** step (``data.is_review``) passes only on an APPROVED verdict with
        in-scope artifact evidence; a **create** step passes on a schema-valid payload
        (populated ``artifact_refs``) + in-scope paths, regardless of the ``verdict``
        field. The pass/block logic is the same as :meth:`run` so reviews gate
        identically whether or not a transition follows.
        """
        result = self._runtime.run(data.request)
        return self._blocked_result(lifecycle_run, data, result)

    def evaluate_gate_with_result(
        self, lifecycle_run: LifecycleRun, data: AgentRunnerInput
    ) -> tuple[AgentRunResult, BlockedState | None]:
        """Run the request ONCE and return both the worker result and the gate decision.

        Used by the release-definition workflow (T-30-D-05) when the workflow-step handoff
        resolver is wired: the workflow needs the worker's ``structured_output`` to write
        the immutable step payload, AND the same single run's gate decision. Running the
        worker once and returning both avoids a double execution while keeping the gate
        logic identical to :meth:`evaluate_gate`.
        """
        result = self._runtime.run(data.request)
        return result, self._blocked_result(lifecycle_run, data, result)

    def run(self, lifecycle_run: LifecycleRun, data: AgentRunnerInput) -> TransitionDecision:
        decision, _result = self.run_with_result(lifecycle_run, data)
        return decision

    def run_with_result(
        self, lifecycle_run: LifecycleRun, data: AgentRunnerInput
    ) -> tuple[TransitionDecision, AgentRunResult]:
        """Run the worker ONCE and return both the phase transition AND the raw result.

        v0.1.78 T-B / FR-B: :meth:`run` is the pre-existing transition-only entry point,
        now a thin delegator so every existing caller is byte-identical. A caller that also
        needs the worker's ``AgentRunResult`` (e.g. :class:`LifecyclePipeline` to build a
        run-scoped handoff-ledger payload — the full-pipeline analogue of what
        ``run_implement_review_loop`` already gets from
        :meth:`evaluate_gate_with_result`) uses this instead of running the worker a second
        time.
        """
        result = self._runtime.run(data.request)
        blocked = self._blocked_result(lifecycle_run, data, result)
        if blocked is not None:
            decision = self._state_machine.transition(
                lifecycle_run,
                TransitionInput(
                    target_phase=LifecyclePhase.BLOCKED,
                    blocked_state=blocked,
                    current_step=data.current_step,
                ),
            )
            return decision, result

        decision = self._state_machine.transition(
            lifecycle_run,
            TransitionInput(
                target_phase=data.target_phase,
                evidence=self._evidence_from_result(data.request, result),
                requirements=data.requirements,
                resume_token=data.resume_token,
                current_step=data.current_step,
            ),
        )
        return decision, result

    def _blocked_result(
        self,
        lifecycle_run: LifecycleRun,
        data: AgentRunnerInput,
        result: AgentRunResult,
    ) -> BlockedState | None:
        if result.status is not AgentRunStatus.SUCCEEDED:
            return self._blocked(lifecycle_run, data, result.error or result.summary)
        # L1/L2 (v0.1.31): the verdict requirement is a REVIEW concept. A review step must
        # carry ``verdict == "APPROVED"``; a create step (``is_review=False``) is never
        # gated on a self-reported verdict — it passes on a schema-valid payload (which
        # populates ``artifact_refs``) + in-scope paths, regardless of the ``verdict``
        # field. The ``artifact_refs`` check below still BLOCKs a no-op create worker.
        if data.is_review and result.structured_output.get("verdict") != "APPROVED":
            return self._blocked(lifecycle_run, data, "agent result missing APPROVED verdict")
        if not result.artifact_refs:
            # FR1 (v0.1.68): the FR8 (v0.1.66) role-keyed disk-glob enrichment is RETIRED —
            # it could never be run-scoped (``.dadaia/handoff/<ctx>/*.handoff.json`` files
            # carry no run_id/step in their name or emitter contract, and the per-run
            # step-payload ledger is a different data plane holding no ``.handoff.json``
            # path), so it structurally surfaced an ARBITRARY historical handoff by the same
            # role from a previous task/run — actively misdirecting the operator. When the
            # worker produced no in-result artifact, there is, by construction, no current-run
            # handoff to surface: the detail carries an honest ``no_current_artifact`` marker
            # naming the run and step instead of a fabricated cross-run pointer. This NEVER
            # converts the block into a pass (FR2's no-op invariant is untouched: artifact_refs
            # is still empty, the gate still BLOCKs).
            detail: dict[str, str] = {
                "no_current_artifact": f"{lifecycle_run.run_id}:{data.current_step or lifecycle_run.current_step}"
            }
            return self._blocked(
                lifecycle_run, data, "agent result missing artifact evidence", detail=detail
            )
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
        return out_of_scope_paths(
            paths,
            allowed=request.allowed_paths,
            forbidden=request.forbidden_paths,
        )

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
