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
    AgentRuntimeKind,
    BlockedState,
    GateEvidenceKind,
    GateVerdict,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
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
from dadaia_workspace.features.lifecycle.pipeline import RuntimeFactory
from dadaia_workspace.features.lifecycle.prompt_builder import (
    FragmentBundle,
    LifecyclePromptBuilder,
    PromptPrefix,
    PromptScope,
    build_fragment_suffix,
)
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine


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
        role="project-manager",
        fragment_id="release_definition.release_scope",
        shared_fragment_ids=("shared.grill_questionnaire",),
    ),
    ReleaseStep(
        label="spec_create",
        role="product-engineer",
        fragment_id="release_definition.spec_create",
        shared_fragment_ids=("shared.output_handoff",),
    ),
    ReleaseStep(
        label="spec_arch_review",
        role="software-architect",
        fragment_id="release_definition.spec_review_architecture",
        is_review=True,
    ),
    ReleaseStep(
        label="spec_qa_review",
        role="qa-engineer",
        fragment_id="release_definition.spec_review_qa",
        is_review=True,
    ),
    ReleaseStep(
        label="plan_create",
        role="product-engineer",
        fragment_id="release_definition.plan_create",
    ),
    ReleaseStep(
        label="plan_review",
        role="qa-engineer, software-architect",
        fragment_id="release_definition.plan_review",
        is_review=True,
    ),
    ReleaseStep(
        label="tasks_create",
        role="product-engineer",
        fragment_id="release_definition.tasks_create",
    ),
    ReleaseStep(
        label="tasks_implementability_review",
        role="software-engineer",
        fragment_id="release_definition.tasks_review_implementability",
        is_review=True,
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

        audit = self._select_context(step, fragment)
        run = record_injected_context(run, audit)

        suffix = build_fragment_suffix(
            self._fragment_bundle(step, fragment, shared),
            selected_context=self._render_selection(audit),
        )
        kind = step.runtime_kind or self._default_kind
        runtime = self._runtime_factory(kind)
        scope = self._scope(step, run.run_id, suffix)
        built = self._prompt_builder.build(
            scope, runtime=runtime.runtime_kind(), prefix=self._prefix
        )

        # Python owns the gate. Every model step — create or review — runs the worker and
        # reads its structured verdict through the typed gate (APPROVED + in-scope
        # artifact evidence => pass; REJECTED or missing evidence => BlockedState). The
        # release stays in RELEASE_DEFINITION across all model steps; only the terminal
        # Python commit gate transitions the phase. A blocked step stops the sequence —
        # advancement is never on model say-so.
        runner = LifecycleAgentRunner(runtime=runtime, state_machine=self._state_machine)
        blocked = runner.evaluate_gate(
            run,
            AgentRunnerInput(
                request=built.request, target_phase=run.phase, current_step=step.label
            ),
        )
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
        """Record a model step's outcome on the run, keeping phase = RELEASE_DEFINITION."""
        status = LifecycleRunStatus.BLOCKED if blocked is not None else LifecycleRunStatus.RUNNING
        phase = LifecyclePhase.BLOCKED if blocked is not None else run.phase
        return LifecycleRun(
            run_id=run.run_id,
            context=run.context,
            release_id=run.release_id,
            command=run.command,
            phase=phase,
            status=status,
            current_step=step_label,
            expected_artifacts=run.expected_artifacts,
            idempotency_key=run.idempotency_key,
            blocked=blocked,
            injected_context=run.injected_context,
        )

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
        if run.blocked is not None:
            return run, ReleaseStepResult(
                label=step.label, accepted=False, is_gate=True, blocked=run.blocked
            )
        advanced = LifecycleRun(
            run_id=run.run_id,
            context=run.context,
            release_id=run.release_id,
            command=run.command,
            phase=LifecyclePhase.IMPLEMENTATION,
            status=LifecycleRunStatus.COMPLETED,
            current_step=step.label,
            expected_artifacts=run.expected_artifacts,
            idempotency_key=run.idempotency_key,
            blocked=None,
            injected_context=run.injected_context,
        )
        return advanced, ReleaseStepResult(label=step.label, accepted=True, is_gate=True)

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
        )


__all__ = [
    "ReleaseDefinitionResult",
    "ReleaseDefinitionWorkflow",
    "ReleaseStep",
    "ReleaseStepResult",
]
