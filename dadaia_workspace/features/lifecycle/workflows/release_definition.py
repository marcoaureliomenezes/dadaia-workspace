"""Release-definition workflow body — the SPEC §6.1 sequence on fragments + gates (WS-5).

This is the keystone of the v0.1.24 two-layer redesign: the release-definition
workflow runs as a Python-owned procedure rather than a single generic
``"Run the {label} step"`` prompt. Python owns step **order** and gate **decisions**;
each model step's prompt is assembled from:

- the step's **fragment bundle** — its own fragment body plus the shared fragments it
  cites — loaded via :class:`FragmentLoader`;
- the **dynamically selected context** — each fragment's declared ``dynamic_inputs``
  resolved by :class:`ContextSelector`, bounded by the fragment's ``max_context_policy``;
- the fragment's **output schema**; and
- the discrete **(harness, model)** chosen for the step (threaded through the injected
  runtime factory — the workflow is harness-agnostic).

The stable, release-level context is carried once in a cacheable :class:`PromptPrefix`
and reused verbatim across steps; the fragment material is the variable suffix (see
:func:`build_fragment_suffix`). There is **no generic suffix** for this workflow.

**Python owns the gates.** Each review step's structured verdict (APPROVED / REJECTED)
is read by Python via the typed gate in :class:`LifecycleAgentRunner`: a REJECTED or a
missing-evidence review BLOCKS advancement (the run carries a ``BlockedState`` and the
sequence stops); it never advances on model say-so. The terminal
``definition_commit_gate`` is a Python step with **no model** — it advances the release
to IMPLEMENTATION only when every prior gate passed.

Every step records its injected context (fragment ids + resolved dynamic refs +
policies) into the run record through the :func:`record_injected_context` seam (T-24-08),
so the composition of each prompt is auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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
from dadaia_workspace.core.models.workflow_execution import (
    ResolvedModelConfig,
    WorkflowPolicySnapshot,
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
from dadaia_workspace.features.lifecycle.fragments.loader import (
    Fragment,
    FragmentLoader,
)
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


@dataclass(frozen=True)
class ReleaseStep:
    """One step of the §6.1 release-definition sequence.

    A model step names its fragment id (``workflow.step``), the shared fragment ids it
    cites, the runtime kind it runs on, and whether it is a **review** (a gate whose
    verdict can REJECT and thereby BLOCK advancement). The terminal Python gate carries
    ``fragment_id=None`` and ``runtime_kind=None`` — it runs no model.
    """

    label: str
    role: str
    fragment_id: str | None
    shared_fragment_ids: tuple[str, ...] = ()
    is_review: bool = False
    runtime_kind: AgentRuntimeKind | None = None
    # Workflow-step handoff data plane edges (v0.1.30 Item 5 / T-30-D-05). ``produces`` is
    # the named payload schema this step writes (None ⇒ no ledger payload); ``consumes`` is
    # the tuple of upstream producer-step labels this step resolves by exact (run id,
    # producer step, attempt) BEFORE running (A19/A20/A25). The resolver records the
    # consumption (A22); a missing/malformed required upstream BLOCKS the step before its
    # prompt runs. These edges are inert unless a resolver is wired (back-compat).
    produces: str | None = None
    consumes: tuple[str, ...] = ()
    # Governance-resolved concrete model for this step (v0.1.56 / FR1). ``apply_resolved_policy``
    # threads the resolved snapshot model here; ``_scope`` forwards it to the request so the
    # adapter runs the policy-selected model. Additive-optional, mirroring ``PipelineStep``.
    resolved_model: ResolvedModelConfig | None = None
    model_profile: str | None = None


@dataclass(frozen=True)
class ReleaseStepResult:
    """Typed outcome of one release-definition step."""

    label: str
    accepted: bool
    is_gate: bool
    fragment_id: str | None = None
    prompt_text: str | None = None
    runtime_kind: AgentRuntimeKind | None = None
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class ReleaseDefinitionResult:
    """Typed outcome of the whole release-definition sequence."""

    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[ReleaseStepResult, ...] = field(default_factory=tuple)
    blocked: BlockedState | None = None


#: The §6.1 release-definition sequence. ``runtime_kind=None`` on a model step means the
#: workflow's default harness is used; the terminal gate carries no fragment and no model.
#: Fragment ids match the shipped ``release_definition/*`` bundle; ``spec_arch_review``
#: maps to ``release_definition.spec_review_architecture``.
_SEQUENCE: tuple[ReleaseStep, ...] = (
    ReleaseStep(
        label="release_scope",
        role="product-engineer",
        fragment_id="release_definition.release_scope",
        shared_fragment_ids=(
            "shared.grill_questionnaire",
            "shared.output_handoff",
            "shared.anti_slop",
        ),
        produces="release-scope-handoff-v1",
    ),
    ReleaseStep(
        label="spec_create",
        role="product-engineer",
        fragment_id="release_definition.spec_create",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.anti_slop",
            "shared.memory_selection",
        ),
        produces="generic-step-handoff-v1",
        consumes=("release_scope",),
    ),
    ReleaseStep(
        label="spec_arch_review",
        role="software-architect",
        fragment_id="release_definition.spec_review_architecture",
        shared_fragment_ids=(
            "shared.anti_slop",
            "shared.output_handoff",
            "shared.memory_selection",
        ),
        is_review=True,
        produces="spec-review-handoff-v1",
        consumes=("spec_create",),
    ),
    ReleaseStep(
        label="spec_qa_review",
        role="qa-engineer",
        fragment_id="release_definition.spec_review_qa",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.memory_selection",
        ),
        is_review=True,
        produces="spec-review-handoff-v1",
        consumes=("spec_create",),
    ),
    ReleaseStep(
        label="plan_create",
        role="product-engineer",
        fragment_id="release_definition.plan_create",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.anti_slop",
            "shared.memory_selection",
        ),
        produces="generic-step-handoff-v1",
        consumes=("spec_create",),
    ),
    ReleaseStep(
        label="plan_review",
        role="qa-engineer, software-architect",
        fragment_id="release_definition.plan_review",
        shared_fragment_ids=(
            "shared.anti_slop",
            "shared.output_handoff",
            "shared.memory_selection",
        ),
        is_review=True,
        produces="plan-review-handoff-v1",
        consumes=("plan_create",),
    ),
    ReleaseStep(
        label="tasks_create",
        role="product-engineer",
        fragment_id="release_definition.tasks_create",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.anti_slop",
            "shared.memory_selection",
        ),
        produces="generic-step-handoff-v1",
        consumes=("plan_create",),
    ),
    ReleaseStep(
        label="tasks_implementability_review",
        role="software-engineer",
        fragment_id="release_definition.tasks_review_implementability",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.memory_selection",
        ),
        is_review=True,
        produces="tasks-review-handoff-v1",
        consumes=("tasks_create",),
    ),
    ReleaseStep(
        label="definition_commit_gate",
        role="python",
        fragment_id=None,
    ),
)


class ReleaseDefinitionWorkflow:
    """Run the §6.1 release-definition sequence with fragment prompts + Python gates."""

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
        policy_snapshot: WorkflowPolicySnapshot | None = None,
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
        # The resolved governance snapshot (v0.1.56 / FR1 / LAW 7). When present it is frozen
        # onto the run BEFORE the first step (mirroring ``LifecyclePipeline`` /
        # ``LifecyclePhaseWorkflow``); an overlay mutated after start cannot change the
        # in-flight run because the run carries this immutable snapshot. The replace-based
        # step helpers preserve it across every step transition.
        self._policy_snapshot = policy_snapshot
        # When wired, the resolver drives the run-scoped workflow-step handoff data plane
        # (v0.1.30 Item 5 / T-30-D-05): each step resolves its declared upstream payloads
        # by exact (run id, producer step, attempt) and writes its own produced payload.
        # When None the workflow behaves exactly as before (back-compat) — the
        # produces/consumes edges are inert.
        self._handoff_resolver = handoff_resolver

    # -- public entrypoint ----------------------------------------------

    def run(
        self, run_id: str, sequence: tuple[ReleaseStep, ...] = _SEQUENCE
    ) -> ReleaseDefinitionResult:
        """Execute the sequence; stop at the first blocked gate; advance on success."""
        if not sequence:
            raise ValueError("release-definition workflow requires at least one step")
        # Fold each fragment's declared static_inputs into the cacheable prefix once: they
        # are stable across every step, so they live in the byte-identical prefix (not the
        # per-step suffix) and the provider prompt cache reads them at a fraction of cost.
        self._prefix = self._prefix_with_static_inputs(sequence)
        run = LifecycleRun(
            run_id=run_id,
            context=self._context,
            release_id=self._release_id,
            command="release_definition",
            phase=LifecyclePhase.RELEASE_DEFINITION,
            status=LifecycleRunStatus.RUNNING,
            current_step=sequence[0].label,
            idempotency_key=run_id,
            workflow_policy=self._policy_snapshot,
        )
        self._run_store.save(run)

        results: list[ReleaseStepResult] = []
        for step in sequence:
            if step.fragment_id is None:
                run, step_result = self._run_commit_gate(run, step)
            else:
                run, step_result = self._run_model_step(run, step)
            self._run_store.save(run)
            results.append(step_result)
            if not step_result.accepted:
                return ReleaseDefinitionResult(
                    run_id=run_id,
                    completed=False,
                    final_phase=run.phase,
                    steps=tuple(results),
                    blocked=run.blocked,
                )
        return ReleaseDefinitionResult(
            run_id=run_id,
            completed=True,
            final_phase=run.phase,
            steps=tuple(results),
        )

    # -- model step ------------------------------------------------------

    def _run_model_step(
        self, run: LifecycleRun, step: ReleaseStep
    ) -> tuple[LifecycleRun, ReleaseStepResult]:
        assert step.fragment_id is not None
        fragment = self._loader.load_fragment(step.fragment_id)
        shared = tuple(self._loader.load_fragment(fid) for fid in step.shared_fragment_ids)

        # Resolve every declared upstream payload BEFORE the prompt runs (A19/A20/A25).
        # A missing or malformed required upstream BLOCKS the step here — the worker is
        # never run on incomplete inputs. The resolved digests are injected into the prompt
        # (compact, not raw JSON). When no resolver is wired this is a no-op.
        run, upstream_block, digests = self._resolve_upstream(run, step)
        if upstream_block is not None:
            run = self._with_step_outcome(run, step.label, upstream_block)
            self._run_store.save(run)
            return run, ReleaseStepResult(
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

        # Python owns the gate, which is REVIEW-ONLY for the verdict (v0.1.31 / L1). A
        # review step (``step.is_review``) runs the worker and reads its structured verdict
        # (APPROVED + in-scope artifact evidence => pass; REJECTED or missing evidence =>
        # BlockedState); a create step passes on a schema-valid payload + in-scope paths,
        # regardless of the ``verdict`` field. The release stays in RELEASE_DEFINITION
        # across all model steps; only the terminal Python commit gate transitions the
        # phase. A blocked step stops the sequence — advancement is never on model say-so.
        # The worker runs ONCE; its structured output is reused to write the step's
        # produced payload (T-30-D-05).
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
        # Record consumption of every upstream the step declared (A22) and write this
        # step's produced payload (A18/A21) — only on a passing step, only when wired.
        if blocked is None:
            run = self._record_consumptions(run, step)
            run = self._produce_payload(run, step, worker_result)
        run = self._with_step_outcome(run, step.label, blocked)
        # WS-9: complete this step's audit entry with the full prompt composition so the
        # run record is queryable — prefix hash (cacheable-prefix invariant), the discrete
        # model, the runtime kind, the output schema, and the Python gate verdict.
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
        result = ReleaseStepResult(
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
        """Record a model step's outcome on the run, keeping phase = RELEASE_DEFINITION.

        Uses :func:`dataclasses.replace` so every additive-optional field — notably the
        ``workflow_steps`` ledger (T-30-D-05) and the ``workflow_policy`` snapshot — is
        preserved across the step transition rather than silently reset.
        """
        from dataclasses import replace

        status = LifecycleRunStatus.BLOCKED if blocked is not None else LifecycleRunStatus.RUNNING
        phase = LifecyclePhase.BLOCKED if blocked is not None else run.phase
        return replace(
            run,
            phase=phase,
            status=status,
            current_step=step_label,
            blocked=blocked,
        )

    # -- workflow-step handoff data plane (T-30-D-05) -------------------------

    def _resolve_upstream(
        self, run: LifecycleRun, step: ReleaseStep
    ) -> tuple[LifecycleRun, BlockedState | None, tuple[str, ...]]:
        """Resolve every declared upstream payload by exact (run, producer step, attempt).

        Returns the (possibly unchanged) run, a :class:`BlockedState` when a required
        upstream is missing/malformed (A20), and the compact digests to inject. A no-op
        when no resolver is wired or the step declares no ``consumes`` edges.
        """
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

    def _record_consumptions(self, run: LifecycleRun, step: ReleaseStep) -> LifecycleRun:
        """Record this step's consumption of each declared upstream payload (A22)."""
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
        self, run: LifecycleRun, step: ReleaseStep, worker_result: AgentRunResult
    ) -> LifecycleRun:
        """Write this step's immutable produced payload + ledger entry (A18/A21).

        The payload body is derived from the worker's structured output (verdict / summary)
        so the data-plane envelope is byte-faithful to what the step emitted. ``declared_consumers``
        are the downstream steps that declare a ``consumes`` edge on this producer — the set
        whose consumption flips the payload to ``consumed_all`` / cleanup-eligible.
        """
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
    def _payload_from_result(step: ReleaseStep, worker_result: AgentRunResult) -> dict[str, object]:
        verdict = worker_result.structured_output.get("verdict")
        payload: dict[str, object] = {"summary": worker_result.summary or step.label}
        if step.is_review and isinstance(verdict, str):
            payload["verdict"] = verdict
            reason = worker_result.structured_output.get("verdict_reason")
            if isinstance(reason, str):
                payload["verdict_reason"] = reason
        return payload

    # -- terminal Python gate (no model) --------------------------------

    def _run_commit_gate(
        self, run: LifecycleRun, step: ReleaseStep
    ) -> tuple[LifecycleRun, ReleaseStepResult]:
        """Advance to IMPLEMENTATION iff no prior gate blocked the run (Python-owned).

        This step runs no model. The sequence only reaches it when every prior step
        passed (the loop stops at the first block), so reaching it means all gates
        passed and the release advances; defensively, if the run is already blocked the
        gate refuses to advance.
        """
        from dataclasses import replace

        if run.blocked is not None:
            return run, ReleaseStepResult(
                label=step.label, accepted=False, is_gate=True, blocked=run.blocked
            )
        # Graph-completeness check (T-30-D-05): when the resolver is wired, every declared
        # consumes edge in the sequence must have been satisfied — i.e. every producer the
        # sequence declares actually produced a ledger payload, and every consumer recorded
        # its consumption. A gap means a prompt-to-prompt edge silently went unfilled; the
        # gate BLOCKS rather than advancing on an incomplete graph.
        graph_block = self._graph_completeness_block(run, step)
        if graph_block is not None:
            blocked_run = self._with_step_outcome(run, step.label, graph_block)
            return blocked_run, ReleaseStepResult(
                label=step.label, accepted=False, is_gate=True, blocked=graph_block
            )
        advanced = replace(
            run,
            phase=LifecyclePhase.IMPLEMENTATION,
            status=LifecycleRunStatus.COMPLETED,
            current_step=step.label,
            blocked=None,
        )
        return advanced, ReleaseStepResult(label=step.label, accepted=True, is_gate=True)

    def _graph_completeness_block(
        self, run: LifecycleRun, step: ReleaseStep
    ) -> BlockedState | None:
        """Return a BlockedState if the workflow-step handoff graph is incomplete.

        For every model step in the sequence: a ``produces`` step must have a ledger
        record; for every ``consumes`` edge the consumer must have recorded a consumption
        of that producer. No-op when no resolver is wired.
        """
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

    def _prefix_with_static_inputs(self, sequence: tuple[ReleaseStep, ...]) -> PromptPrefix | None:
        """Return the prefix augmented with every fragment's resolved static_inputs.

        Static inputs (e.g. ``specs/constitution.md``, ``specs/memory/architecture.md``)
        are stable across the whole release, so they belong in the cacheable prefix. We
        gather the de-duplicated declared static inputs across all model-step fragments,
        resolve each via the context selector (graceful skip when absent), and re-derive a
        single prefix carrying them as stable sections. When there are no resolvable static
        inputs the original prefix is returned unchanged — the byte-identity guard for runs
        with no static inputs is preserved exactly.
        """
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

    def _collect_static_inputs(self, sequence: tuple[ReleaseStep, ...]) -> tuple[StaticInput, ...]:
        """Resolve the de-duplicated static_inputs declared across the sequence's fragments.

        Each entry is resolved at most once (first declaration order wins). A declared
        static input absent from this context is included with ``present=False`` so the
        skip is recorded/auditable; only present ones reach the prefix.
        """
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
        self,
        step: ReleaseStep,
        fragment: Fragment,
        shared: tuple[Fragment, ...],
    ) -> FragmentBundle:
        return FragmentBundle(
            fragment_id=fragment.id,
            role=step.role,
            body=fragment.body,
            output_schema=fragment.output_schema,
            shared_bodies=tuple(frag.body for frag in shared),
            shared_ids=tuple(frag.id for frag in shared),
        )

    def _select_context(self, step: ReleaseStep, fragment: Fragment) -> SelectionAudit:
        """Resolve the fragment's dynamic inputs, bounded by its max_context_policy."""
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

    def _scope(self, step: ReleaseStep, run_id: str, suffix: str) -> PromptScope:
        return PromptScope(
            role=step.role,
            context=self._context,
            release_id=self._release_id,
            task_id=f"{run_id}:{step.label}",
            prompt=suffix,
            allowed_paths=(f".dadaia/handoff/{self._context}/**",),
            required_evidence=(GateEvidenceKind.HANDOFF,),
            model_profile=step.model_profile,
            resolved_model=step.resolved_model,
            persona=resolve_persona_for_role(step.role),
        )


__all__ = [
    "ReleaseDefinitionResult",
    "ReleaseDefinitionWorkflow",
    "ReleaseStep",
    "ReleaseStepResult",
]
