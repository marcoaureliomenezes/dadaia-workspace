"""Backlog-definition workflow body — the epic §4 sequence on fragments + Python gates (R2).

Shares the pure fragment-assembly helpers with the four handoff-ledger bodies via
:class:`~dadaia_workspace.features.lifecycle.workflows._fragment_gate._FragmentAssemblyMixin`
(v0.1.57 FR1) — the ``run()`` folds each model fragment's ``static_inputs`` into a cacheable
:class:`PromptPrefix`, selects dynamic context per fragment, builds the suffix via
:func:`build_fragment_suffix`, runs the worker on the injected :class:`RuntimeFactory`, reads
the Python-owned typed gate, and advances only on success.

What is different from the handoff-ledger bodies is the **Python-disposing** steps this
workflow owns directly (the linchpin of the epic) — so it is a *structural outlier* that mixes
in only the assembly helpers rather than joining the full ``FragmentGateWorkflow`` base
(Ruling C: it has no handoff-ledger data plane). Python decides these gates with the R1
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
``backlog_author``) run a worker through the injected runtime and read the same typed gate as
the handoff-ledger bodies. A blocked step stops the sequence with a ``BlockedState``; the
terminal success advances the run to RELEASE_DEFINITION (the next lifecycle phase).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRuntimeKind,
    BlockedState,
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
from dadaia_workspace.core.protocols.runtime_files import RuntimeFilePort
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
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector
from dadaia_workspace.features.lifecycle.fragments.loader import Fragment, FragmentLoader
from dadaia_workspace.features.lifecycle.pipeline import RuntimeFactory
from dadaia_workspace.features.lifecycle.prompt_builder import (
    LifecyclePromptBuilder,
    PromptPrefix,
    build_fragment_suffix,
    canonical_worker_output_ref,
)
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine
from dadaia_workspace.features.lifecycle.workflow_handoffs import (
    WorkflowHandoffResolver,
    durable_payload_from_result,
)
from dadaia_workspace.features.lifecycle.workflows._fragment_gate import _FragmentAssemblyMixin

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


def _parse_downgrade_verdict(raw: str | None) -> Verdict | None:
    """Map a model's verdict string to a *safe* downgrade ``Verdict`` (WS-3 wrapper).

    Returns a :class:`Verdict` **only** for a parsed ``OVERLAP``/``SUPERSEDES`` (the compatible
    -merge verdicts ``conflict_scan`` may emit). Anything else — ``DIVERGENT_CONFLICT``,
    ``UNRELATED``, ``DUPLICATE``, ``DEPENDS_ON``, garbage, empty, or ``None`` — maps to ``None``
    so the classifier keeps the fail-closed ``DIVERGENT_CONFLICT``. Deliberately stricter than
    the classifier clamp (T-43-6b): the consult can never upgrade an UNRELATED or mask a
    conflict, and the two guards are independent (defence-in-depth).
    """
    if not raw:
        return None
    normalized = raw.strip().lower()
    if normalized == Verdict.OVERLAP.value:
        return Verdict.OVERLAP
    if normalized == Verdict.SUPERSEDES.value:
        return Verdict.SUPERSEDES
    return None


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
    # Governance-resolved concrete model for this step (v0.1.56 / FR1). ``apply_resolved_policy``
    # threads the resolved snapshot model here; the shared mixin ``_scope`` forwards it to the
    # request so the adapter runs the policy-selected model. Additive-optional, mirroring
    # ``PipelineStep``.
    resolved_model: ResolvedModelConfig | None = None
    model_profile: str | None = None


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
        role="product-engineer",
        kind=BacklogStepKind.MODEL,
        fragment_id="backlog_definition.intake_grill",
        shared_fragment_ids=("shared.grill_questionnaire",),
    ),
    BacklogStep(label="subject_bind", role="python", kind=BacklogStepKind.SUBJECT_BIND),
    BacklogStep(
        label="existing_backlog_review",
        role="python",
        kind=BacklogStepKind.EXISTING_REVIEW,
        # Python owns the conflict boundary; this fragment is consulted ONLY on the
        # shared-anchor differing-change branch (via the `downgrade` seam) and may narrow
        # DIVERGENT_CONFLICT -> OVERLAP/SUPERSEDES on proven-compatible evidence — never
        # upgrade, never mask (T-43-6; classifier clamp T-43-6b is the boundary guard). The
        # citation also makes `conflict_scan` a non-orphan fragment (WS-5 orphan check).
        fragment_id="backlog_definition.conflict_scan",
    ),
    BacklogStep(label="reconcile_decision", role="python", kind=BacklogStepKind.RECONCILE),
    BacklogStep(
        label="conflict_resolution_grill",
        role="product-engineer",
        kind=BacklogStepKind.CONFLICT_GRILL,
        fragment_id="backlog_definition.conflict_resolution_grill",
        shared_fragment_ids=("shared.grill_questionnaire",),
    ),
    BacklogStep(
        label="backlog_author",
        role="product-engineer",
        kind=BacklogStepKind.MODEL,
        fragment_id="backlog_definition.backlog_authoring",
        # T-43-3 anti_slop citation done here (this file is software-engineer's for T-43-6;
        # wiring it inline avoids a write race with the release_definition.py T-43-3 work).
        shared_fragment_ids=("shared.anti_slop", "shared.output_handoff"),
    ),
    BacklogStep(label="backlog_review_gate", role="python", kind=BacklogStepKind.REVIEW_GATE),
)


class BacklogDefinitionWorkflow(_FragmentAssemblyMixin):
    """Run the epic §4 backlog-definition sequence with fragment prompts + Python gates.

    Mixes in :class:`_FragmentAssemblyMixin` for the pure fragment-assembly helpers (v0.1.57
    FR1) and keeps its own kind-based dispatch + Python-disposing steps. The converged mixin
    ``_scope`` now threads ``model_profile`` / ``resolved_model`` — before FR1 this body's
    ``_scope`` dropped both although ``BacklogStep`` carries them (grill Problem #8), so its
    worker ran on the wrong model.
    """

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
        policy_snapshot: WorkflowPolicySnapshot | None = None,
        artifact_root: Path | None = None,
        runtime_files: RuntimeFilePort | None = None,
        handoff_resolver: WorkflowHandoffResolver | None = None,
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
        # The resolved governance snapshot (v0.1.56 / FR1 / LAW 7), frozen onto the run BEFORE
        # the first step (mirroring ``LifecyclePipeline`` / ``LifecyclePhaseWorkflow``). The
        # replace-based run-record helpers preserve it across every Python-step transition.
        self._policy_snapshot = policy_snapshot
        # Bug gate-accepts-phantom-artifact-evidence: when wired, declared artifact refs
        # must EXIST under this root or the step BLOCKs.
        self._artifact_root = artifact_root
        self._runtime_files = runtime_files
        self._handoff_resolver = handoff_resolver

    # -- public entrypoint ----------------------------------------------

    def run(
        self,
        run_id: str,
        demand: BacklogDemand,
        *,
        sequence: tuple[BacklogStep, ...] = _SEQUENCE,
        operator_demand: str | None = None,
    ) -> BacklogDefinitionResult:
        """Execute the §4 sequence; stop at the first blocked gate; advance on success.

        *operator_demand* is the raw demand text the intake grill exists to interrogate
        (bug backlog-define-has-no-demand-input-channel); when set it is injected into
        every model step's prompt as an "## Operator demand" block.
        """
        if not sequence:
            raise ValueError("backlog-definition workflow requires at least one step")
        self._operator_demand = operator_demand
        self._prefix = self._prefix_with_static_inputs(sequence)
        if self._handoff_resolver is not None:
            self._handoff_resolver.reset_run_zone(
                run_id,
                worker_output_refs=tuple(
                    canonical_worker_output_ref(self._context, f"{run_id}:{step.label}")
                    for step in sequence
                    if step.fragment_id is not None
                ),
            )
        run = LifecycleRun(
            run_id=run_id,
            context=self._context,
            release_id=self._release_id,
            command="backlog_definition",
            phase=LifecyclePhase.BACKLOG_DEFINITION,
            status=LifecycleRunStatus.RUNNING,
            current_step=sequence[0].label,
            idempotency_key=run_id,
            workflow_policy=self._policy_snapshot,
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
        downgrade = self._resolve_downgrade(step, run.run_id)
        overlap = classify(bound_new, demand.existing, downgrade=downgrade)
        return overlap, self._still_running(run, step.label), self._ok_sr(step)

    # -- conflict_scan downgrade-only model consult (T-43-6, SPEC §3 WS-3) ---

    def _resolve_downgrade(self, step: BacklogStep, run_id: str) -> Downgrade:
        """Pick the ``downgrade`` seam ``classify`` consults on the differing-change branch.

        Precedence, fail-closed by default:

        * an explicitly injected ``downgrade`` (operator/test override) always wins;
        * else, the default offline/``FAKE`` path keeps :func:`no_downgrade` — no model call,
          a shared-anchor differing-change pair stays ``DIVERGENT_CONFLICT`` (existing
          behavior, existing tests unchanged);
        * else (a real model runtime is wired AND the step names ``conflict_scan``), return the
          model-backed consult. ``classify`` calls it ONLY on the differing-change branch, so
          the worker is consulted on exactly the shared-anchor differing-change pairs.
        """
        if self._downgrade is not no_downgrade:
            return self._downgrade
        if step.fragment_id is None or self._default_kind is AgentRuntimeKind.FAKE:
            return no_downgrade
        return self._conflict_scan_downgrade(step, run_id)

    def _conflict_scan_downgrade(self, step: BacklogStep, run_id: str) -> Downgrade:
        """Return a model-backed ``downgrade`` callable that consults ``conflict_scan``.

        The returned callable runs the worker on the ``conflict_scan`` fragment for the one
        differing shared anchor and maps **only** a parsed ``OVERLAP``/``SUPERSEDES`` verdict to
        a :class:`Verdict`; anything else or unparseable -> ``None`` (the WS-3 wrapper). Combined
        with the classifier clamp (T-43-6b) this is defence-in-depth: the consult can narrow a
        conflict's name but can never upgrade an ``UNRELATED`` or mask a conflict.
        """
        assert step.fragment_id is not None
        fragment = self._loader.load_fragment(step.fragment_id)
        shared = tuple(self._loader.load_fragment(fid) for fid in step.shared_fragment_ids)

        def _downgrade(new_change: str, existing_change: str) -> Verdict | None:
            result = self._run_consult_worker(
                step, fragment, shared, run_id, new_change, existing_change
            )
            return _parse_downgrade_verdict(result.structured_output.get("verdict"))

        return _downgrade

    def _run_consult_worker(
        self,
        step: BacklogStep,
        fragment: Fragment,
        shared: tuple[Fragment, ...],
        run_id: str,
        new_change: str,
        existing_change: str,
    ) -> AgentRunResult:
        """Build the ``conflict_scan`` prompt for one differing pair and run the worker once.

        Reuses the same context-selection + suffix + prompt-builder machinery as
        :meth:`_run_model_step`; it calls the runtime port directly (not the gate runner)
        because a downgrade adjudication extracts a content verdict, not an APPROVED/REJECTED
        gate decision — there is no artifact to gate on.
        """
        audit = self._select_context(step, (fragment, *shared))
        pair_context = (
            f"### conflict_pair\n- new change: {new_change}\n- existing change: {existing_change}"
        )
        rendered = self._render_selection(audit)
        selected = f"{rendered}\n\n{pair_context}" if rendered else pair_context
        suffix = build_fragment_suffix(
            self._fragment_bundle(step, fragment, shared),
            selected_context=selected,
            is_review=False,
        )
        kind = step.runtime_kind or self._default_kind
        runtime = self._runtime_factory(kind)
        scope = self._scope(step, run_id, suffix)
        built = self._prompt_builder.build(
            scope, runtime=runtime.runtime_kind(), prefix=self._prefix
        )
        return runtime.run(built.request)

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

    # -- model step (mirrors the handoff-ledger bodies) -----------------

    def _run_model_step(
        self, run: LifecycleRun, step: BacklogStep
    ) -> tuple[LifecycleRun, BacklogStepResult]:
        assert step.fragment_id is not None
        fragment = self._loader.load_fragment(step.fragment_id)
        shared = tuple(self._loader.load_fragment(fid) for fid in step.shared_fragment_ids)

        audit = self._select_context(step, (fragment, *shared))
        run = record_injected_context(run, audit)

        selected = self._render_selection(audit)
        # Bug backlog-define-has-no-demand-input-channel: the raw operator demand IS the
        # workflow's subject — every model step reasons over it.
        demand_text = getattr(self, "_operator_demand", None)
        if demand_text:
            selected = "\n\n".join(filter(None, (f"## Operator demand\n\n{demand_text}", selected)))
        suffix = build_fragment_suffix(
            self._fragment_bundle(step, fragment, shared),
            selected_context=selected,
            # backlog_author is a CREATE step (BacklogStep is kind-based, no is_review
            # field) — it emits an artifact, never a self-verdict (D-2 / A4).
            is_review=False,
        )
        kind = step.runtime_kind or self._default_kind
        runtime = self._runtime_factory(kind)
        scope = self._scope(step, run.run_id, suffix)
        if step.label == "backlog_author":
            # The author step writes the ADDITIVE specs/backlog item, so include that
            # real deliverable in the step-aware scope.
            scope = replace(
                scope,
                allowed_paths=(
                    *scope.allowed_paths,
                    f"repos/{self._context}/specs/backlog/**",
                    "specs/backlog/**",
                ),
            )
        built = self._prompt_builder.build(
            scope, runtime=runtime.runtime_kind(), prefix=self._prefix
        )
        runner = LifecycleAgentRunner(
            runtime=runtime,
            state_machine=self._state_machine,
            artifact_root=self._artifact_root,
            runtime_files=self._runtime_files,
        )
        worker_result, blocked = runner.evaluate_gate_with_result(
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
        if blocked is None and self._handoff_resolver is not None:
            payload = durable_payload_from_result(
                worker_result, fallback_summary=step.label, is_review=False
            )
            run, _ = self._handoff_resolver.produce(
                run,
                producer_step=step.label,
                attempt=0,
                output_schema=fragment.output_schema,
                payload=payload,
                retention_mode=(
                    RetentionMode.PROMOTE_TO_EVIDENCE
                    if step.label == "backlog_author"
                    else RetentionMode.DELETE_AFTER_CONSUMED
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
        # ``replace`` (not a manual reconstruction) preserves every additive-optional field —
        # notably the ``workflow_policy`` snapshot (FR1) — across the Python-step transition.
        from dataclasses import replace

        return replace(
            run,
            phase=run.phase,
            status=LifecycleRunStatus.RUNNING,
            current_step=step_label,
            blocked=None,
        )

    @staticmethod
    def _with_block(run: LifecycleRun, step_label: str, blocked: BlockedState) -> LifecycleRun:
        from dataclasses import replace

        return replace(
            run,
            phase=LifecyclePhase.BLOCKED,
            status=LifecycleRunStatus.BLOCKED,
            current_step=step_label,
            blocked=blocked,
        )

    @staticmethod
    def _advance(run: LifecycleRun) -> LifecycleRun:
        from dataclasses import replace

        return replace(
            run,
            phase=LifecyclePhase.RELEASE_DEFINITION,
            status=LifecycleRunStatus.COMPLETED,
            current_step=run.current_step,
            blocked=None,
        )

    @staticmethod
    def _ok_sr(step: BacklogStep) -> BacklogStepResult:
        return BacklogStepResult(label=step.label, accepted=True, kind=step.kind)

    @staticmethod
    def _blocked_sr(step: BacklogStep, blocked: BlockedState) -> BacklogStepResult:
        return BacklogStepResult(label=step.label, accepted=False, kind=step.kind, blocked=blocked)
