"""Bug-report workflow body — intake→dedupe→bug_write on fragments + Python gates.

Wave-E (v0.1.30 Item 6 / T-30-E-03) real workflow body replacing the fail-loud
``_deferred.bug_report`` stub. Mirrors
:mod:`dadaia_workspace.features.lifecycle.workflows.release_definition` field-for-field:
Python owns step order and the gate decisions; each model step's prompt is assembled from
its fragment bundle + the dynamically selected context (bounded by ``max_context_policy``)
+ the output schema + the discrete ``(harness, model)`` chosen for the step.

The sequence is:

1. ``bug_intake`` (project-auditor) — normalizes a reported symptom into the bug-record
   fields (symptom / repro / expected-vs-actual / severity), redaction-clean. Produces
   ``bug-intake-handoff-v1``.
2. ``dedupe`` (product-engineer, **review**) — decides new-vs-duplicate against tracked
   bugs. Consumes ``bug_intake``; produces ``bug-dedupe-handoff-v1``. A REJECTED verdict
   (duplicate) BLOCKS the write — the duplicate is folded into the existing bug, not re-filed.
3. ``bug_write`` (product-engineer) — files exactly one **additive** bug record. Consumes
   ``dedupe``; produces ``bug-record-handoff-v1``.
4. ``bug_record_gate`` (python, no model) — the terminal Python gate; completes the run only
   when every prior step passed and the workflow-step handoff graph is complete.

**A29 — ADDITIVE-only.** The ``bug_write`` step's worker scope allows writes **only** under
the bug channel (``specs/bugs/**``), which is the ADDITIVE path class — no lease is taken
and the write is never gate-blocked. The non-writing steps emit only to the handoff dir.
The body itself touches no file other than the run-scoped step payloads it produces through
the handoff resolver.

Like release-definition, the body consumes the Wave-D run-scoped workflow-step handoff
ledger: each step resolves its declared upstream payloads by exact
``(run id, producer step, attempt)`` BEFORE its prompt runs (a missing/malformed required
upstream BLOCKS), and records its own produced payload. Every step records its injected
fragments + dynamic context via :func:`record_injected_context` (L4 auditability).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRuntimeKind,
    BlockedState,
    GateEvidenceKind,
    GateVerdict,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_handoff import RetentionMode
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStore
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
    record_injected_context,
    record_prompt_composition,
)
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    MaxContextPolicy,
    SelectionAudit,
    StaticInput,
)
from dadaia_workspace.features.lifecycle.fragments.loader import Fragment, FragmentLoader
from dadaia_workspace.features.lifecycle.personas.loader import resolve_persona_for_role
from dadaia_workspace.features.lifecycle.pipeline import RuntimeFactory
from dadaia_workspace.features.lifecycle.prompt_builder import (
    FragmentBundle,
    LifecyclePromptBuilder,
    PromptPrefix,
    PromptScope,
    build_fragment_suffix,
)
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine
from dadaia_workspace.features.lifecycle.workflow_handoffs import (
    MalformedHandoffError,
    RequiredHandoffMissingError,
    WorkflowHandoffResolver,
)

__all__ = [
    "BugReportResult",
    "BugReportStep",
    "BugReportStepResult",
    "BugReportWorkflow",
    "_SEQUENCE",
]

#: The label of the single step permitted to write the additive bug record (A29). Its
#: worker scope allows ONLY the ADDITIVE ``specs/bugs/`` path class — no lease, never blocked.
_BUG_WRITE_STEP = "bug_write"


@dataclass(frozen=True)
class BugReportStep:
    """One step of the bug-report sequence (mirrors ``release_definition.ReleaseStep``)."""

    label: str
    role: str
    fragment_id: str | None
    shared_fragment_ids: tuple[str, ...] = ()
    is_review: bool = False
    runtime_kind: AgentRuntimeKind | None = None
    produces: str | None = None
    consumes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BugReportStepResult:
    """Typed outcome of one bug-report step."""

    label: str
    accepted: bool
    is_gate: bool
    fragment_id: str | None = None
    prompt_text: str | None = None
    runtime_kind: AgentRuntimeKind | None = None
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class BugReportResult:
    """Typed outcome of the whole bug-report sequence."""

    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[BugReportStepResult, ...] = field(default_factory=tuple)
    blocked: BlockedState | None = None


#: The bug-report sequence. The terminal gate carries no fragment and no model.
_SEQUENCE: tuple[BugReportStep, ...] = (
    BugReportStep(
        label="bug_intake",
        role="project-auditor",
        fragment_id="bug_report.bug_intake",
        shared_fragment_ids=("shared.output_handoff",),
        produces="bug-intake-handoff-v1",
    ),
    BugReportStep(
        label="dedupe",
        role="product-engineer",
        fragment_id="bug_report.dedupe",
        shared_fragment_ids=("shared.output_handoff",),
        is_review=True,
        produces="bug-dedupe-handoff-v1",
        consumes=("bug_intake",),
    ),
    BugReportStep(
        label=_BUG_WRITE_STEP,
        role="product-engineer",
        fragment_id="bug_report.bug_write",
        produces="bug-record-handoff-v1",
        consumes=("dedupe",),
    ),
    BugReportStep(
        label="bug_record_gate",
        role="python",
        fragment_id=None,
    ),
)


class BugReportWorkflow:
    """Run the bug-report sequence with fragment prompts + Python gates."""

    def __init__(
        self,
        *,
        context: str,
        release_id: str,
        run_store: LifecycleRunStore,
        runtime_factory: RuntimeFactory,
        context_selector: ContextSelector,
        default_runtime_kind: AgentRuntimeKind = AgentRuntimeKind.FAKE,
        fragment_loader: FragmentLoader | None = None,
        prefix: PromptPrefix | None = None,
        prompt_builder: LifecyclePromptBuilder | None = None,
        state_machine: LifecycleStateMachine | None = None,
        handoff_resolver: WorkflowHandoffResolver | None = None,
    ) -> None:
        self._context = context
        self._release_id = release_id
        self._run_store = run_store
        self._runtime_factory = runtime_factory
        self._selector = context_selector
        self._default_kind = default_runtime_kind
        self._loader = fragment_loader or FragmentLoader()
        self._prefix = prefix
        self._prompt_builder = prompt_builder or LifecyclePromptBuilder()
        self._state_machine = state_machine or LifecycleStateMachine()
        self._handoff_resolver = handoff_resolver

    # -- public entrypoint ----------------------------------------------

    def run(self, run_id: str, sequence: tuple[BugReportStep, ...] = _SEQUENCE) -> BugReportResult:
        """Execute the sequence; stop at the first blocked gate; complete on success."""
        if not sequence:
            raise ValueError("bug_report workflow requires at least one step")
        self._prefix = self._prefix_with_static_inputs(sequence)
        run = LifecycleRun(
            run_id=run_id,
            context=self._context,
            release_id=self._release_id,
            command="bug_report",
            phase=LifecyclePhase.BACKLOG_DEFINITION,
            status=LifecycleRunStatus.RUNNING,
            current_step=sequence[0].label,
            idempotency_key=run_id,
        )
        self._run_store.save(run)

        results: list[BugReportStepResult] = []
        for step in sequence:
            if step.fragment_id is None:
                run, step_result = self._run_record_gate(run, step)
            else:
                run, step_result = self._run_model_step(run, step)
            self._run_store.save(run)
            results.append(step_result)
            if not step_result.accepted:
                return BugReportResult(
                    run_id=run_id,
                    completed=False,
                    final_phase=run.phase,
                    steps=tuple(results),
                    blocked=run.blocked,
                )
        return BugReportResult(
            run_id=run_id,
            completed=True,
            final_phase=run.phase,
            steps=tuple(results),
        )

    # -- model step ------------------------------------------------------

    def _run_model_step(
        self, run: LifecycleRun, step: BugReportStep
    ) -> tuple[LifecycleRun, BugReportStepResult]:
        assert step.fragment_id is not None
        fragment = self._loader.load_fragment(step.fragment_id)
        shared = tuple(self._loader.load_fragment(fid) for fid in step.shared_fragment_ids)

        run, upstream_block, digests = self._resolve_upstream(run, step)
        if upstream_block is not None:
            run = self._with_step_outcome(run, step.label, upstream_block)
            self._run_store.save(run)
            return run, BugReportStepResult(
                label=step.label,
                accepted=False,
                is_gate=step.is_review,
                fragment_id=step.fragment_id,
                runtime_kind=step.runtime_kind or self._default_kind,
                blocked=upstream_block,
            )

        audit = self._select_context(step, fragment)
        run = record_injected_context(run, audit)

        selected = self._render_selection(audit)
        if digests:
            selected = "\n\n".join(filter(None, (selected, *digests)))
        suffix = build_fragment_suffix(
            self._fragment_bundle(step, fragment, shared),
            selected_context=selected,
            is_review=step.is_review,
        )
        kind = step.runtime_kind or self._default_kind
        runtime = self._runtime_factory(kind)
        scope = self._scope(step, run.run_id, suffix)
        built = self._prompt_builder.build(
            scope, runtime=runtime.runtime_kind(), prefix=self._prefix
        )

        runner = LifecycleAgentRunner(runtime=runtime, state_machine=self._state_machine)
        worker_result, blocked = runner.evaluate_gate_with_result(
            run,
            AgentRunnerInput(
                request=built.request,
                target_phase=run.phase,
                current_step=step.label,
                is_review=step.is_review,
            ),
        )
        if blocked is None:
            run = self._record_consumptions(run, step)
            run = self._produce_payload(run, step, worker_result)
        run = self._with_step_outcome(run, step.label, blocked)
        run = record_prompt_composition(
            run,
            step.label,
            prefix_hash=built.prefix_hash,
            model=scope.model_profile,
            runtime_kind=kind.value,
            output_schema=fragment.output_schema,
            gate_result=(
                GateVerdict.REJECTED if blocked is not None else GateVerdict.APPROVED
            ).value,
        )
        result = BugReportStepResult(
            label=step.label,
            accepted=blocked is None,
            is_gate=step.is_review,
            fragment_id=step.fragment_id,
            prompt_text=built.prompt_text,
            runtime_kind=kind,
            blocked=blocked,
        )
        return run, result

    @staticmethod
    def _with_step_outcome(
        run: LifecycleRun, step_label: str, blocked: BlockedState | None
    ) -> LifecycleRun:
        status = LifecycleRunStatus.BLOCKED if blocked is not None else LifecycleRunStatus.RUNNING
        phase = LifecyclePhase.BLOCKED if blocked is not None else run.phase
        return replace(run, phase=phase, status=status, current_step=step_label, blocked=blocked)

    # -- workflow-step handoff data plane (consumes the Wave-D ledger) --------

    def _resolve_upstream(
        self, run: LifecycleRun, step: BugReportStep
    ) -> tuple[LifecycleRun, BlockedState | None, tuple[str, ...]]:
        if self._handoff_resolver is None or not step.consumes:
            return run, None, ()
        digests: list[str] = []
        for producer in step.consumes:
            try:
                resolved = self._handoff_resolver.resolve_required(
                    run, producer_step=producer, attempt=0
                )
            except (RequiredHandoffMissingError, MalformedHandoffError) as exc:
                blocked = BlockedState(
                    reason=f"required upstream handoff unavailable: {exc}",
                    blocked_at_step=step.label,
                    detail={"producer_step": producer, "consumer_step": step.label},
                )
                return run, blocked, ()
            digests.append(WorkflowHandoffResolver.render_digest(resolved))
        return run, None, tuple(digests)

    def _record_consumptions(self, run: LifecycleRun, step: BugReportStep) -> LifecycleRun:
        if self._handoff_resolver is None:
            return run
        for producer in step.consumes:
            run = self._handoff_resolver.record_consumption(
                run,
                producer_step=producer,
                producer_attempt=0,
                consumer_step=step.label,
                consumer_attempt=0,
            )
        return run

    def _produce_payload(
        self, run: LifecycleRun, step: BugReportStep, worker_result: AgentRunResult
    ) -> LifecycleRun:
        if self._handoff_resolver is None or step.produces is None:
            return run
        payload = self._payload_from_result(step, worker_result)
        consumers = tuple(s.label for s in _SEQUENCE if step.label in s.consumes)
        retention = (
            RetentionMode.PROMOTE_TO_EVIDENCE
            if step.is_review
            else RetentionMode.DELETE_AFTER_CONSUMED
        )
        run, _ = self._handoff_resolver.produce(
            run,
            producer_step=step.label,
            attempt=0,
            output_schema=step.produces,
            payload=payload,
            declared_consumers=consumers,
            retention_mode=retention,
        )
        return run

    @staticmethod
    def _payload_from_result(
        step: BugReportStep, worker_result: AgentRunResult
    ) -> dict[str, object]:
        verdict = worker_result.structured_output.get("verdict")
        payload: dict[str, object] = {"summary": worker_result.summary or step.label}
        if step.is_review and isinstance(verdict, str):
            payload["verdict"] = verdict
            reason = worker_result.structured_output.get("verdict_reason")
            if isinstance(reason, str):
                payload["verdict_reason"] = reason
        return payload

    # -- terminal Python gate (no model) --------------------------------

    def _run_record_gate(
        self, run: LifecycleRun, step: BugReportStep
    ) -> tuple[LifecycleRun, BugReportStepResult]:
        if run.blocked is not None:
            return run, BugReportStepResult(
                label=step.label, accepted=False, is_gate=True, blocked=run.blocked
            )
        graph_block = self._graph_completeness_block(run, step)
        if graph_block is not None:
            blocked_run = self._with_step_outcome(run, step.label, graph_block)
            return blocked_run, BugReportStepResult(
                label=step.label, accepted=False, is_gate=True, blocked=graph_block
            )
        completed = replace(
            run,
            status=LifecycleRunStatus.COMPLETED,
            current_step=step.label,
            blocked=None,
        )
        return completed, BugReportStepResult(label=step.label, accepted=True, is_gate=True)

    def _graph_completeness_block(
        self, run: LifecycleRun, step: BugReportStep
    ) -> BlockedState | None:
        if self._handoff_resolver is None:
            return None
        for s in _SEQUENCE:
            if s.fragment_id is None:
                continue
            if s.produces is not None and run.workflow_steps.find(s.label, 0) is None:
                return BlockedState(
                    reason=f"workflow-step graph incomplete: step {s.label!r} declared "
                    f"produces={s.produces!r} but wrote no ledger payload",
                    blocked_at_step=step.label,
                    detail={"missing_producer": s.label},
                )
            for producer in s.consumes:
                record = run.workflow_steps.find(producer, 0)
                if record is None:
                    return BlockedState(
                        reason=f"workflow-step graph incomplete: {s.label!r} consumes "
                        f"{producer!r} which has no ledger payload",
                        blocked_at_step=step.label,
                        detail={"consumer": s.label, "missing_producer": producer},
                    )
                acked = any(c.consumer_step == s.label for c in record.consumptions)
                if not acked:
                    return BlockedState(
                        reason=f"workflow-step graph incomplete: {s.label!r} never recorded "
                        f"consumption of {producer!r}",
                        blocked_at_step=step.label,
                        detail={"consumer": s.label, "unconsumed_producer": producer},
                    )
        return None

    # -- static-input injection (folded into the cacheable prefix) -------

    def _prefix_with_static_inputs(
        self, sequence: tuple[BugReportStep, ...]
    ) -> PromptPrefix | None:
        resolved = self._collect_static_inputs(sequence)
        present = [item for item in resolved if item.present]
        if not present:
            return self._prefix
        sections: dict[str, str] = {}
        if self._prefix is not None and self._prefix.text:
            sections["release-context"] = self._prefix.text
        for item in present:
            sections[f"static-input:{item.ref}"] = item.content
        return PromptPrefix.from_sections(sections)

    def _collect_static_inputs(
        self, sequence: tuple[BugReportStep, ...]
    ) -> tuple[StaticInput, ...]:
        seen: set[str] = set()
        out: list[StaticInput] = []
        for step in sequence:
            if step.fragment_id is None:
                continue
            fragment = self._loader.load_fragment(step.fragment_id)
            for declared in fragment.static_inputs:
                ref = declared.strip().lstrip("/")
                if ref in seen:
                    continue
                seen.add(ref)
                out.append(self._selector.resolve_static_input(declared))
        return tuple(out)

    # -- assembly helpers ------------------------------------------------

    def _fragment_bundle(
        self, step: BugReportStep, fragment: Fragment, shared: tuple[Fragment, ...]
    ) -> FragmentBundle:
        return FragmentBundle(
            fragment_id=fragment.id,
            role=step.role,
            body=fragment.body,
            output_schema=fragment.output_schema,
            shared_bodies=tuple(frag.body for frag in shared),
            shared_ids=tuple(frag.id for frag in shared),
        )

    def _select_context(self, step: BugReportStep, fragment: Fragment) -> SelectionAudit:
        policy = MaxContextPolicy.parse(fragment.max_context_policy)
        return self._selector.select_all(
            step.label,
            fragment.dynamic_inputs,
            policy,
            fragment_ids=(fragment.id, *step.shared_fragment_ids),
        )

    @staticmethod
    def _render_selection(audit: SelectionAudit) -> str:
        blocks = [
            f"### {result.name}\n{result.content}".rstrip()
            for result in audit.results
            if result.content.strip()
        ]
        return "\n\n".join(blocks)

    def _scope(self, step: BugReportStep, run_id: str, suffix: str) -> PromptScope:
        """Build the per-step worker scope.

        A29: the ``bug_write`` step allows writes ONLY under the ADDITIVE bug channel
        (``specs/bugs/**``) — no lease, never gate-blocked. Every other step is a
        non-writing analysis/review step and emits only to the handoff dir.
        """
        allowed: tuple[str, ...]
        if step.label == _BUG_WRITE_STEP:
            allowed = (f"repos/{self._context}/specs/bugs/**", "specs/bugs/**")
        else:
            allowed = (f".dadaia/handoff/{self._context}/**",)
        return PromptScope(
            role=step.role,
            context=self._context,
            release_id=self._release_id,
            task_id=f"{run_id}:{step.label}",
            prompt=suffix,
            allowed_paths=allowed,
            required_evidence=(GateEvidenceKind.HANDOFF,),
            persona=resolve_persona_for_role(step.role),
        )
