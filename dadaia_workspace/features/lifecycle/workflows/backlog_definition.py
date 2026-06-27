"""Backlog-definition workflow body — the epic §4 sequence on fragments + Python gates (R2).

Mirrors :mod:`release_definition` field-for-field: a ``_SEQUENCE`` of frozen step
dataclasses + a workflow class whose ``run()`` folds each model fragment's ``static_inputs``
into a cacheable :class:`PromptPrefix`, selects dynamic context per fragment, builds the
suffix via :func:`build_fragment_suffix`, runs the worker on the injected
:class:`RuntimeFactory`, reads the Python-owned typed gate, and advances only on success.

What is different from release-definition is the **Python-disposing** steps that this
workflow owns directly — the linchpin of the epic. Python decides these gates with the R1
machinery, never on model say-so:

* **1b ``subject_bind``** — binds every proposed subject through the R1 canonical-subject
  registry; HALTs on any UNRESOLVED/AMBIGUOUS subject (no silent NEW).
* **2 ``existing_backlog_review``** — runs the R1 ``classify`` over the bound intents vs every
  existing item's bound intents (model OFFLINE by default; the downgrade seam adjudicates a
  same-anchor differing-change pair, fail-closed — T-26-06).
* **3 ``reconcile_decision``** — blocks a NEW item unless every existing item is ``UNRELATED``.
* **4 ``conflict_resolution_grill``** — a model grill, but **conditional**: it runs only when
  step 2 reported a ``DIVERGENT_CONFLICT``; otherwise it is recorded skipped (not blocked).
* **6 ``backlog_review_gate``** — re-runs ``classify`` over the authored result against the rest
  of the backlog; blocks on any ``DUPLICATE``/``DIVERGENT_CONFLICT`` in the result.

The model steps (1 ``intake_grill``, 4 ``conflict_resolution_grill`` when it runs, 5
``backlog_author``) run a worker through the injected runtime and read the same typed gate
as release-definition. A blocked step stops the sequence with a ``BlockedState``; the terminal
success advances the run to RELEASE_DEFINITION (the next lifecycle phase).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from dadaia_workspace.core.models.backlog import SubjectKind
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
from dadaia_workspace.features.backlog.classifier import (
    BoundItem,
    Classification,
    Downgrade,
    Verdict,
    classify,
    no_downgrade,
)
from dadaia_workspace.features.backlog.subject_registry import BindStatus, Registry
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
from dadaia_workspace.features.lifecycle.pipeline import RuntimeFactory
from dadaia_workspace.features.lifecycle.prompt_builder import (
    FragmentBundle,
    LifecyclePromptBuilder,
    PromptPrefix,
    PromptScope,
    build_fragment_suffix,
)
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine

__all__ = [
    "AuthoredItem",
    "BacklogDefinitionResult",
    "BacklogDefinitionWorkflow",
    "BacklogDemand",
    "BacklogStep",
    "BacklogStepKind",
    "BacklogStepResult",
    "ProposedIntent",
    "_SEQUENCE",
]


class BacklogStepKind(StrEnum):
    """What kind of step this is — selects the model-vs-Python handler."""

    MODEL = "model"
    SUBJECT_BIND = "subject_bind"
    EXISTING_REVIEW = "existing_backlog_review"
    RECONCILE = "reconcile_decision"
    CONFLICT_GRILL = "conflict_resolution_grill"
    REVIEW_GATE = "backlog_review_gate"


@dataclass(frozen=True)
class ProposedIntent:
    """One proposed ``(subject -> change)`` from step 1, pre-binding (a raw ref)."""

    kind: SubjectKind
    ref: str
    change: str


@dataclass(frozen=True)
class AuthoredItem:
    """The step-5 authoring output (the backlog item the workflow would write)."""

    slug: str
    is_new: bool
    bound: BoundItem
    #: The rest of the backlog the review gate re-validates the result against.
    rest_of_backlog: tuple[BoundItem, ...] = ()


@dataclass(frozen=True)
class BacklogDemand:
    """The structured demand threaded through the §4 sequence (Python-step inputs).

    Carries the model-produced structured outputs the Python gates dispose on: the proposed
    intents (step 1 output → step 1b binds), every existing item's bound intents (the
    ``backlog_index`` → step 2 classifies), and the authored result (step 5 output → step 6
    re-validates).
    """

    proposed_intents: tuple[ProposedIntent, ...]
    existing: tuple[BoundItem, ...] = ()
    authored: AuthoredItem | None = None


@dataclass(frozen=True)
class BacklogStep:
    """One step of the §4 backlog-definition sequence."""

    label: str
    role: str
    kind: BacklogStepKind
    fragment_id: str | None = None
    shared_fragment_ids: tuple[str, ...] = ()
    runtime_kind: AgentRuntimeKind | None = None


@dataclass(frozen=True)
class BacklogStepResult:
    """Typed outcome of one backlog-definition step."""

    label: str
    accepted: bool
    kind: BacklogStepKind
    fragment_id: str | None = None
    prompt_text: str | None = None
    runtime_kind: AgentRuntimeKind | None = None
    skipped: bool = False
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class BacklogDefinitionResult:
    """Typed outcome of the whole backlog-definition sequence."""

    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[BacklogStepResult, ...] = field(default_factory=tuple)
    overlap: tuple[Classification, ...] = field(default_factory=tuple)
    blocked: BlockedState | None = None


#: The §4 seven-step sequence. Model steps name a fragment id; the conditional grill names a
#: fragment but is skipped unless step 2 found a DIVERGENT_CONFLICT. Pure Python steps carry
#: ``fragment_id=None``.
_SEQUENCE: tuple[BacklogStep, ...] = (
    BacklogStep(
        label="intake_grill",
        role="project-manager",
        kind=BacklogStepKind.MODEL,
        fragment_id="backlog_definition.intake_grill",
        shared_fragment_ids=("shared.grill_questionnaire",),
    ),
    BacklogStep(label="subject_bind", role="python", kind=BacklogStepKind.SUBJECT_BIND),
    BacklogStep(
        label="existing_backlog_review", role="python", kind=BacklogStepKind.EXISTING_REVIEW
    ),
    BacklogStep(label="reconcile_decision", role="python", kind=BacklogStepKind.RECONCILE),
    BacklogStep(
        label="conflict_resolution_grill",
        role="project-manager",
        kind=BacklogStepKind.CONFLICT_GRILL,
        fragment_id="backlog_definition.conflict_resolution_grill",
        shared_fragment_ids=("shared.grill_questionnaire",),
    ),
    BacklogStep(
        label="backlog_author",
        role="product-engineer",
        kind=BacklogStepKind.MODEL,
        fragment_id="backlog_definition.backlog_authoring",
        shared_fragment_ids=("shared.output_handoff",),
    ),
    BacklogStep(label="backlog_review_gate", role="python", kind=BacklogStepKind.REVIEW_GATE),
)


class BacklogDefinitionWorkflow:
    """Run the epic §4 backlog-definition sequence with fragment prompts + Python gates."""

    def __init__(
        self,
        *,
        context: str,
        release_id: str,
        run_store: LifecycleRunStore,
        runtime_factory: RuntimeFactory,
        context_selector: ContextSelector,
        registry: Registry,
        default_runtime_kind: AgentRuntimeKind = AgentRuntimeKind.FAKE,
        downgrade: Downgrade = no_downgrade,
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
        self._registry = registry
        self._default_kind = default_runtime_kind
        self._downgrade = downgrade
        self._loader = fragment_loader or FragmentLoader()
        self._prefix = prefix
        self._prompt_builder = prompt_builder or LifecyclePromptBuilder()
        self._state_machine = state_machine or LifecycleStateMachine()

    # -- public entrypoint ----------------------------------------------

    def run(
        self,
        run_id: str,
        demand: BacklogDemand,
        *,
        sequence: tuple[BacklogStep, ...] = _SEQUENCE,
    ) -> BacklogDefinitionResult:
        """Execute the §4 sequence; stop at the first blocked gate; advance on success."""
        if not sequence:
            raise ValueError("backlog-definition workflow requires at least one step")
        self._prefix = self._prefix_with_static_inputs(sequence)
        run = LifecycleRun(
            run_id=run_id,
            context=self._context,
            release_id=self._release_id,
            command="backlog_definition",
            phase=LifecyclePhase.BACKLOG_DEFINITION,
            status=LifecycleRunStatus.RUNNING,
            current_step=sequence[0].label,
            idempotency_key=run_id,
        )
        self._run_store.save(run)

        # Mutable per-run state threaded between Python steps.
        bound_new: BoundItem | None = None
        overlap: list[Classification] = []
        results: list[BacklogStepResult] = []

        for step in sequence:
            if step.kind is BacklogStepKind.SUBJECT_BIND:
                bound_new, run, sr = self._run_subject_bind(run, step, demand)
            elif step.kind is BacklogStepKind.EXISTING_REVIEW:
                overlap_list, run, sr = self._run_existing_review(run, step, demand, bound_new)
                overlap = overlap_list
            elif step.kind is BacklogStepKind.RECONCILE:
                run, sr = self._run_reconcile(run, step, demand, overlap)
            elif step.kind is BacklogStepKind.CONFLICT_GRILL:
                run, sr = self._run_conflict_grill(run, step, overlap)
            elif step.kind is BacklogStepKind.REVIEW_GATE:
                run, sr = self._run_review_gate(run, step, demand)
            else:
                run, sr = self._run_model_step(run, step)
            self._run_store.save(run)
            results.append(sr)
            if not sr.accepted:
                return BacklogDefinitionResult(
                    run_id=run_id,
                    completed=False,
                    final_phase=run.phase,
                    steps=tuple(results),
                    overlap=tuple(overlap),
                    blocked=run.blocked,
                )

        advanced = self._advance(run)
        self._run_store.save(advanced)
        return BacklogDefinitionResult(
            run_id=run_id,
            completed=True,
            final_phase=advanced.phase,
            steps=tuple(results),
            overlap=tuple(overlap),
        )

    # -- Python step 1b: subject_bind -----------------------------------

    def _run_subject_bind(
        self, run: LifecycleRun, step: BacklogStep, demand: BacklogDemand
    ) -> tuple[BoundItem | None, LifecycleRun, BacklogStepResult]:
        anchor_changes: dict[str, str] = {}
        for proposed in demand.proposed_intents:
            result = self._registry.bind(proposed.ref, proposed.kind)
            if result.status is not BindStatus.RESOLVED or result.anchor is None:
                blocked = BlockedState(
                    reason=(
                        f"subject_bind HALT: {result.message or proposed.ref} "
                        f"(status={result.status.value})"
                    ),
                    blocked_at_step=step.label,
                    resume_token=run.idempotency_key,
                )
                return (
                    None,
                    self._with_block(run, step.label, blocked),
                    self._blocked_sr(step, blocked),
                )
            anchor_changes[result.anchor.id] = proposed.change
        bound = BoundItem(
            slug=demand.authored.slug if demand.authored else "new", anchor_changes=anchor_changes
        )
        return bound, self._still_running(run, step.label), self._ok_sr(step)

    # -- Python step 2: existing_backlog_review -------------------------

    def _run_existing_review(
        self,
        run: LifecycleRun,
        step: BacklogStep,
        demand: BacklogDemand,
        bound_new: BoundItem | None,
    ) -> tuple[list[Classification], LifecycleRun, BacklogStepResult]:
        if bound_new is None:  # defensive: bind step must have produced a bound item.
            blocked = BlockedState(
                reason="existing_backlog_review: no bound intents from subject_bind",
                blocked_at_step=step.label,
                resume_token=run.idempotency_key,
            )
            return [], self._with_block(run, step.label, blocked), self._blocked_sr(step, blocked)
        overlap = classify(bound_new, demand.existing, downgrade=self._downgrade)
        return overlap, self._still_running(run, step.label), self._ok_sr(step)

    # -- Python step 3: reconcile_decision ------------------------------

    def _run_reconcile(
        self,
        run: LifecycleRun,
        step: BacklogStep,
        demand: BacklogDemand,
        overlap: list[Classification],
    ) -> tuple[LifecycleRun, BacklogStepResult]:
        wants_new = demand.authored is None or demand.authored.is_new
        non_unrelated = [c for c in overlap if c.verdict is not Verdict.UNRELATED]
        if wants_new and non_unrelated:
            classes = ", ".join(f"{c.other_slug}:{c.verdict.value}" for c in non_unrelated)
            blocked = BlockedState(
                reason=(
                    "reconcile_decision blocks NEW: a non-UNRELATED class exists "
                    f"({classes}); fold into the existing item instead of filing a new file"
                ),
                blocked_at_step=step.label,
                resume_token=run.idempotency_key,
            )
            return self._with_block(run, step.label, blocked), self._blocked_sr(step, blocked)
        return self._still_running(run, step.label), self._ok_sr(step)

    # -- Python+model step 4: conflict_resolution_grill (conditional) ---

    def _run_conflict_grill(
        self, run: LifecycleRun, step: BacklogStep, overlap: list[Classification]
    ) -> tuple[LifecycleRun, BacklogStepResult]:
        has_conflict = any(c.verdict is Verdict.DIVERGENT_CONFLICT for c in overlap)
        if not has_conflict:
            # Clean overlap report → skip the grill (recorded skipped, not blocked).
            return self._still_running(run, step.label), BacklogStepResult(
                label=step.label, accepted=True, kind=step.kind, skipped=True
            )
        return self._run_model_step(run, step)

    # -- Python step 6: backlog_review_gate -----------------------------

    def _run_review_gate(
        self, run: LifecycleRun, step: BacklogStep, demand: BacklogDemand
    ) -> tuple[LifecycleRun, BacklogStepResult]:
        if demand.authored is None:
            blocked = BlockedState(
                reason="backlog_review_gate: no authored result to validate",
                blocked_at_step=step.label,
                resume_token=run.idempotency_key,
            )
            return self._with_block(run, step.label, blocked), self._blocked_sr(step, blocked)
        verdicts = classify(demand.authored.bound, demand.authored.rest_of_backlog)
        dirty = [
            c for c in verdicts if c.verdict in {Verdict.DUPLICATE, Verdict.DIVERGENT_CONFLICT}
        ]
        if dirty:
            classes = ", ".join(f"{c.other_slug}:{c.verdict.value}" for c in dirty)
            blocked = BlockedState(
                reason=(
                    "backlog_review_gate: authored result introduces a "
                    f"DUPLICATE/DIVERGENT_CONFLICT ({classes})"
                ),
                blocked_at_step=step.label,
                resume_token=run.idempotency_key,
            )
            return self._with_block(run, step.label, blocked), self._blocked_sr(step, blocked)
        return self._still_running(run, step.label), self._ok_sr(step)

    # -- model step (mirrors release_definition) ------------------------

    def _run_model_step(
        self, run: LifecycleRun, step: BacklogStep
    ) -> tuple[LifecycleRun, BacklogStepResult]:
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
        runner = LifecycleAgentRunner(runtime=runtime, state_machine=self._state_machine)
        blocked = runner.evaluate_gate(
            run,
            AgentRunnerInput(
                request=built.request,
                target_phase=run.phase,
                current_step=step.label,
                # backlog_author is a CREATE step (BacklogStep is kind-based, no is_review
                # boolean): it must pass on a schema-valid payload, never a verdict (L1).
                is_review=False,
            ),
        )
        run = (
            self._with_block(run, step.label, blocked)
            if blocked
            else self._still_running(run, step.label)
        )
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
        return run, BacklogStepResult(
            label=step.label,
            accepted=blocked is None,
            kind=step.kind,
            fragment_id=step.fragment_id,
            prompt_text=built.prompt_text,
            runtime_kind=kind,
            blocked=blocked,
        )

    # -- run-record helpers ---------------------------------------------

    @staticmethod
    def _still_running(run: LifecycleRun, step_label: str) -> LifecycleRun:
        return LifecycleRun(
            run_id=run.run_id,
            context=run.context,
            release_id=run.release_id,
            command=run.command,
            phase=run.phase,
            status=LifecycleRunStatus.RUNNING,
            current_step=step_label,
            expected_artifacts=run.expected_artifacts,
            idempotency_key=run.idempotency_key,
            blocked=None,
            injected_context=run.injected_context,
        )

    @staticmethod
    def _with_block(run: LifecycleRun, step_label: str, blocked: BlockedState) -> LifecycleRun:
        return LifecycleRun(
            run_id=run.run_id,
            context=run.context,
            release_id=run.release_id,
            command=run.command,
            phase=LifecyclePhase.BLOCKED,
            status=LifecycleRunStatus.BLOCKED,
            current_step=step_label,
            expected_artifacts=run.expected_artifacts,
            idempotency_key=run.idempotency_key,
            blocked=blocked,
            injected_context=run.injected_context,
        )

    @staticmethod
    def _advance(run: LifecycleRun) -> LifecycleRun:
        return LifecycleRun(
            run_id=run.run_id,
            context=run.context,
            release_id=run.release_id,
            command=run.command,
            phase=LifecyclePhase.RELEASE_DEFINITION,
            status=LifecycleRunStatus.COMPLETED,
            current_step=run.current_step,
            expected_artifacts=run.expected_artifacts,
            idempotency_key=run.idempotency_key,
            blocked=None,
            injected_context=run.injected_context,
        )

    @staticmethod
    def _ok_sr(step: BacklogStep) -> BacklogStepResult:
        return BacklogStepResult(label=step.label, accepted=True, kind=step.kind)

    @staticmethod
    def _blocked_sr(step: BacklogStep, blocked: BlockedState) -> BacklogStepResult:
        return BacklogStepResult(label=step.label, accepted=False, kind=step.kind, blocked=blocked)

    # -- static-input injection (folded into the cacheable prefix) ------

    def _prefix_with_static_inputs(self, sequence: tuple[BacklogStep, ...]) -> PromptPrefix | None:
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

    def _collect_static_inputs(self, sequence: tuple[BacklogStep, ...]) -> tuple[StaticInput, ...]:
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

    # -- assembly helpers -----------------------------------------------

    def _fragment_bundle(
        self, step: BacklogStep, fragment: Fragment, shared: tuple[Fragment, ...]
    ) -> FragmentBundle:
        return FragmentBundle(
            fragment_id=fragment.id,
            role=step.role,
            body=fragment.body,
            output_schema=fragment.output_schema,
            shared_bodies=tuple(frag.body for frag in shared),
            shared_ids=tuple(frag.id for frag in shared),
        )

    def _select_context(self, step: BacklogStep, fragment: Fragment) -> SelectionAudit:
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

    def _scope(self, step: BacklogStep, run_id: str, suffix: str) -> PromptScope:
        return PromptScope(
            role=step.role,
            context=self._context,
            release_id=self._release_id,
            task_id=f"{run_id}:{step.label}",
            prompt=suffix,
            allowed_paths=(f".dadaia/handoff/{self._context}/**",),
            required_evidence=(GateEvidenceKind.HANDOFF,),
        )
