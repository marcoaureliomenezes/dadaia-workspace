"""Backlog-definition workflow body — a real post-authoring gate over minimal model calls.

Shares the pure fragment-assembly helpers with the four handoff-ledger bodies via
:class:`~dadaia_workspace.features.lifecycle.workflows._fragment_gate._FragmentAssemblyMixin`
(v0.1.57 FR1) — the ``run()`` folds each model fragment's ``static_inputs`` into a cacheable
:class:`PromptPrefix`, selects dynamic context per fragment, builds the suffix via
:func:`build_fragment_suffix`, runs the worker on the injected :class:`RuntimeFactory`, reads
the Python-owned typed gate, and advances only on success.

**Default path — ONE model call.** ``backlog_author`` (role product-engineer) receives the
operator demand + the ``backlog_index`` dynamic context and writes exactly one backlog item
(NEW file or an in-place EDIT). ``backlog_review_gate`` (Python, no worker) then does the real
work of validating that write: it re-loads ``specs/backlog/*.md`` from disk, binds every
resolved item's ``intents[]`` through the R1 canonical-subject registry, diffs the authored
slug(s) against a pre-authoring snapshot, and runs the R1 set-intersection ``classify()`` over
the authored item against the rest of the real backlog. This single gate folds what the four
former pre-authoring Python steps (``subject_bind`` / ``existing_backlog_review`` /
``reconcile_decision`` / the conditional ``conflict_resolution_grill``) used to decide on an
always-empty CLI-supplied :class:`BacklogDemand`, so those checks now run on the one thing that
matters: what the author actually wrote to disk (bug backlog-definition-empty-demand-wiring).

**Opt-in grill.** ``intake_grill`` stays in :data:`_SEQUENCE` (``optional=True``) but only
executes when the caller passes ``grill=True`` to :meth:`BacklogDefinitionWorkflow.run`;
otherwise it is recorded ``skipped`` and costs zero model calls. When it does run, its produced
payload is not decorative: :meth:`BacklogDefinitionWorkflow._intake_grill_digest` resolves it
from the run-scoped handoff ledger (the same ledger every model step already writes to via
``WorkflowHandoffResolver.produce``) and renders a compact digest
(:meth:`WorkflowHandoffResolver.render_digest`) that is injected into ``backlog_author``'s
prompt — a *local* digest pass, not a join onto the full ``consumes``/``produces`` graph
machinery of :mod:`_fragment_gate` (Ruling C: backlog has no handoff-ledger data plane).

**Resume.** :meth:`BacklogDefinitionWorkflow.run` accepts ``resume_from`` and re-executes an
existing run from the named step onward without re-running completed model steps or wiping
their ledger payloads — the definition-sequence analogue of
:meth:`~dadaia_workspace.features.lifecycle.workflows._fragment_gate.FragmentGateWorkflow._run_sequence`'s
resume semantics, implemented locally and kept simple (Ruling C — backlog keeps its own loop).
A resumed step whose prior attempt blocked receives a one-shot digest of that
:class:`~dadaia_workspace.core.models.lifecycle.BlockedState` in its prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.models.lifecycle import (
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
from dadaia_workspace.core.models.workflow_handoff import RetentionMode, WorkflowStepLedger
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStore
from dadaia_workspace.core.protocols.runtime_files import RuntimeFilePort
from dadaia_workspace.features.backlog.classifier import (
    BoundItem,
    Classification,
    Verdict,
    classify,
)
from dadaia_workspace.features.backlog.preview import bound_anchor_changes, load_backlog_items
from dadaia_workspace.features.backlog.subject_registry import Registry
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
    record_injected_context,
    record_prompt_composition,
)
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector
from dadaia_workspace.features.lifecycle.fragments.loader import FragmentLoader
from dadaia_workspace.features.lifecycle.pipeline import RuntimeFactory
from dadaia_workspace.features.lifecycle.prompt_builder import (
    LifecyclePromptBuilder,
    PromptPrefix,
    build_fragment_suffix,
    canonical_worker_output_ref,
)
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine
from dadaia_workspace.features.lifecycle.workflow_handoffs import (
    MalformedHandoffError,
    RequiredHandoffMissingError,
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


class BacklogStepKind(StrEnum):
    """What kind of step this is — selects the model-vs-Python handler."""

    MODEL = "model"
    REVIEW_GATE = "backlog_review_gate"


@dataclass(frozen=True)
class ProposedIntent:
    """One proposed ``(subject -> change)`` — kept for back-compat call sites.

    No longer consumed by the workflow's control flow (the post-authoring gate reads the
    authored file from disk instead); retained so existing imports/constructions elsewhere
    keep working.
    """

    kind: SubjectKind
    ref: str
    change: str


@dataclass(frozen=True)
class AuthoredItem:
    """A caller-supplied authored-item description — kept for back-compat call sites.

    No longer consumed by the workflow's control flow (see :class:`ProposedIntent`).
    """

    slug: str
    is_new: bool
    bound: BoundItem
    rest_of_backlog: tuple[BoundItem, ...] = ()


@dataclass(frozen=True)
class BacklogDemand:
    """A caller-supplied demand description — kept for back-compat call sites.

    Historically threaded the model-produced structured outputs the Python gates disposed
    on. The post-authoring gate now reads real disk state instead, so every field here is
    optional and unused by the control flow; the type stays for import back-compat.
    """

    proposed_intents: tuple[ProposedIntent, ...] = ()
    existing: tuple[BoundItem, ...] = ()
    authored: AuthoredItem | None = None


@dataclass(frozen=True)
class BacklogStep:
    """One step of the backlog-definition sequence."""

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
    #: True for a step that only runs when the caller opts in (``run(..., grill=True)``);
    #: otherwise it is recorded ``skipped`` and never reaches the runtime.
    optional: bool = False


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
    #: The post-authoring gate's classify() verdicts for the authored item(s) against the
    #: rest of the real backlog (populated by ``backlog_review_gate``; empty when the gate
    #: never ran).
    overlap: tuple[Classification, ...] = field(default_factory=tuple)
    blocked: BlockedState | None = None


#: The declarative backlog-definition sequence. ``intake_grill`` is present but ``optional`` —
#: it is skipped by default and only executes when the caller passes ``grill=True``.
#: ``backlog_author`` is the one model step the default path always runs. ``backlog_review_gate``
#: is a pure Python step (no fragment) that validates the real file ``backlog_author`` wrote.
_SEQUENCE: tuple[BacklogStep, ...] = (
    BacklogStep(
        label="intake_grill",
        role="product-engineer",
        kind=BacklogStepKind.MODEL,
        fragment_id="backlog_definition.intake_grill",
        shared_fragment_ids=("shared.grill_questionnaire",),
        optional=True,
    ),
    BacklogStep(
        label="backlog_author",
        role="product-engineer",
        kind=BacklogStepKind.MODEL,
        fragment_id="backlog_definition.backlog_authoring",
        shared_fragment_ids=("shared.anti_slop",),
    ),
    BacklogStep(label="backlog_review_gate", role="python", kind=BacklogStepKind.REVIEW_GATE),
)


class BacklogDefinitionWorkflow(_FragmentAssemblyMixin):
    """Run the backlog-definition sequence: minimal model calls, a real post-authoring gate.

    Mixes in :class:`_FragmentAssemblyMixin` for the pure fragment-assembly helpers (v0.1.57
    FR1) and keeps its own kind-based dispatch + Python-disposing gate. The converged mixin
    ``_scope`` threads ``model_profile`` / ``resolved_model`` so its worker requests run on the
    policy-selected model.
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
        # One-shot resume digest, keyed by step label — mirrors
        # ``FragmentGateWorkflow._resume_feedback`` (bug
        # resumed-definition-step-blind-to-rejecting-review-feedback), implemented locally
        # per Ruling C (backlog keeps its own loop, no full base join).
        self._resume_feedback: dict[str, str] = {}

    # -- public entrypoint ----------------------------------------------

    def run(
        self,
        run_id: str,
        demand: BacklogDemand | None = None,
        *,
        grill: bool = False,
        sequence: tuple[BacklogStep, ...] = _SEQUENCE,
        operator_demand: str | None = None,
        resume_from: str | None = None,
    ) -> BacklogDefinitionResult:
        """Execute the sequence; stop at the first blocked gate; advance on success.

        *demand* is accepted for call-site back-compat (see :class:`BacklogDemand`) but no
        longer drives the gates — the post-authoring gate reads the real
        ``specs/backlog/*.md`` state instead. *grill* opts into running ``intake_grill``
        (default: skipped, zero extra model calls). *operator_demand* is the raw demand text
        injected into every executed model step's prompt as an "## Operator demand" block
        (bug backlog-define-has-no-demand-input-channel). *resume_from* re-executes an
        existing run from the named step onward without re-running completed model steps or
        discarding their ledger payloads.
        """
        if not sequence:
            raise ValueError("backlog-definition workflow requires at least one step")
        del demand  # accepted for back-compat only; the real gate reads disk state.
        self._operator_demand = operator_demand
        self._prefix = self._prefix_with_static_inputs(sequence)

        if resume_from is None:
            run, remaining = self._start_run(run_id, sequence)
        else:
            run, remaining = self._resume_run(run_id, sequence, resume_from)

        # The pre-authoring snapshot of every real backlog item's bound intents (captured
        # ONCE, before any step in THIS call runs). ``backlog_review_gate`` diffs the
        # post-authoring snapshot against this to find what ``backlog_author`` actually wrote.
        before = self._backlog_snapshot()

        overlap: list[Classification] = []
        results: list[BacklogStepResult] = []
        for step in remaining:
            if step.kind is BacklogStepKind.REVIEW_GATE:
                overlap_list, run, sr = self._run_review_gate(run, step, before)
                overlap = overlap_list
            elif step.optional and not grill:
                run, sr = (
                    self._still_running(run, step.label),
                    BacklogStepResult(
                        label=step.label, accepted=True, kind=step.kind, skipped=True
                    ),
                )
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

    # -- run start / resume ----------------------------------------------

    def _start_run(
        self, run_id: str, sequence: tuple[BacklogStep, ...]
    ) -> tuple[LifecycleRun, tuple[BacklogStep, ...]]:
        if self._handoff_resolver is not None:
            self._handoff_resolver.reset_run_zone(
                run_id,
                worker_output_refs=tuple(
                    canonical_worker_output_ref(self._context, f"{run_id}:{step.label}")
                    for step in sequence
                    if step.fragment_id is not None
                ),
                context=self._context,
                release_id=None,
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
        return run, sequence

    def _resume_run(
        self, run_id: str, sequence: tuple[BacklogStep, ...], resume_from: str
    ) -> tuple[LifecycleRun, tuple[BacklogStep, ...]]:
        labels = tuple(step.label for step in sequence)
        if resume_from not in labels:
            raise ValueError(
                f"resume_from step {resume_from!r} is not in the backlog-definition "
                f"sequence {labels}"
            )
        prior = self._run_store.load(run_id)
        if prior is None:
            raise ValueError(f"cannot resume run {run_id!r} from {resume_from!r}: no persisted run")
        index = labels.index(resume_from)
        resumed_labels = set(labels[index:])
        if prior.blocked is not None:
            self._resume_feedback[resume_from] = self._render_prior_block_digest(prior.blocked)
        if self._handoff_resolver is not None:
            self._handoff_resolver.reset_run_zone(
                run_id,
                producer_steps=resumed_labels,
                worker_output_refs=tuple(
                    canonical_worker_output_ref(self._context, f"{run_id}:{step.label}")
                    for step in sequence[index:]
                    if step.fragment_id is not None
                ),
                context=self._context,
                release_id=None,
            )
        kept = tuple(
            record
            for record in prior.workflow_steps.records
            if record.producer_step not in resumed_labels
        )
        run = replace(
            prior,
            phase=LifecyclePhase.BACKLOG_DEFINITION,
            status=LifecycleRunStatus.RUNNING,
            current_step=resume_from,
            blocked=None,
            workflow_steps=WorkflowStepLedger(records=kept),
        )
        return run, sequence[index:]

    @staticmethod
    def _render_prior_block_digest(blocked: BlockedState) -> str:
        lines = [
            "## Prior rejection feedback (resumed run)",
            f"The previous run of this workflow blocked at step "
            f"'{blocked.blocked_at_step}': {blocked.reason}",
        ]
        for key, value in sorted(blocked.detail.items()):
            lines.append(f"- {key}: {value}")
        lines.append("Revise the artifact so every point above is addressed.")
        return "\n".join(lines)

    # -- real disk state: the backlog snapshot ---------------------------

    def _backlog_snapshot(self) -> dict[str, BoundItem]:
        """Every real ``specs/backlog/*.md`` item, reduced to slug -> bound anchor changes.

        Reads live disk state via the same loader the panel/doctor use
        (:func:`load_backlog_items`) and binds each item's ``intents[]`` through the R1
        canonical-subject registry (:func:`bound_anchor_changes`). An item with an unresolved
        subject still contributes whatever DID resolve here; the post-authoring gate reports
        unresolved subjects separately for the authored item(s) only.
        """
        backlog_dir = self._selector.spec_context.specs_dir / "backlog"
        snapshot: dict[str, BoundItem] = {}
        for item in load_backlog_items(backlog_dir):
            anchor_changes, _unresolved = bound_anchor_changes(item, self._registry)
            snapshot[item.slug] = BoundItem(slug=item.slug, anchor_changes=anchor_changes)
        return snapshot

    # -- Python step: backlog_review_gate (the real post-authoring gate) ---

    def _run_review_gate(
        self, run: LifecycleRun, step: BacklogStep, before: dict[str, BoundItem]
    ) -> tuple[list[Classification], LifecycleRun, BacklogStepResult]:
        """Validate what ``backlog_author`` actually wrote to disk — folds four former gates.

        1. Diff the post-authoring backlog snapshot against *before*: any slug that is new or
           whose bound anchor-changes differ is "authored" this run (folds ``subject_bind``'s
           and ``backlog_review_gate``'s old "was anything produced" checks into one real
           disk-grounded diff). No changed slug -> BLOCK (nothing to validate).
        2. Any authored item carrying an unresolved subject -> BLOCK (folds ``subject_bind``'s
           HALT-on-unresolved).
        3. Run the R1 ``classify()`` for each authored item against the rest of the real
           backlog (folds ``existing_backlog_review``). A NEW item may not overlap any
           existing item at all (folds ``reconcile_decision``'s NEW-only-if-every-existing-
           UNRELATED rule); an EDIT may not introduce a DUPLICATE/DIVERGENT_CONFLICT (folds
           the former ``backlog_review_gate``).
        """
        after = self._backlog_snapshot()
        backlog_dir = self._selector.spec_context.specs_dir / "backlog"
        unresolved_by_slug: dict[str, tuple[str, ...]] = {}
        for item in load_backlog_items(backlog_dir):
            _anchor_changes, unresolved = bound_anchor_changes(item, self._registry)
            if unresolved:
                unresolved_by_slug[item.slug] = tuple(unresolved)

        changed = sorted(
            slug
            for slug, bound in after.items()
            if before.get(slug) is None or before[slug].anchor_changes != bound.anchor_changes
        )
        if not changed:
            blocked = BlockedState(
                reason=(
                    "backlog_review_gate: no new/changed item found under specs/backlog/ — "
                    "backlog_author must write a NEW item or edit an existing one"
                ),
                blocked_at_step=step.label,
                resume_token=run.idempotency_key,
            )
            return [], self._with_block(run, step.label, blocked), self._blocked_sr(step, blocked)

        overlap: list[Classification] = []
        for slug in changed:
            if slug in unresolved_by_slug:
                blocked = BlockedState(
                    reason=(
                        f"backlog_review_gate: authored item {slug!r} carries unresolved "
                        f"subject(s): {'; '.join(unresolved_by_slug[slug])}"
                    ),
                    blocked_at_step=step.label,
                    resume_token=run.idempotency_key,
                    detail={"slug": slug},
                )
                return (
                    overlap,
                    self._with_block(run, step.label, blocked),
                    self._blocked_sr(step, blocked),
                )

            rest = tuple(bound for other, bound in after.items() if other != slug)
            verdicts = classify(after[slug], rest)
            overlap.extend(verdicts)
            is_new = slug not in before
            if is_new:
                offending = [c for c in verdicts if c.verdict is not Verdict.UNRELATED]
                reason_kind = "is a NEW item but overlaps existing item(s)"
            else:
                offending = [
                    c
                    for c in verdicts
                    if c.verdict in {Verdict.DUPLICATE, Verdict.DIVERGENT_CONFLICT}
                ]
                reason_kind = "introduces a DUPLICATE/DIVERGENT_CONFLICT"
            if offending:
                classes = ", ".join(f"{c.other_slug}:{c.verdict.value}" for c in offending)
                blocked = BlockedState(
                    reason=f"backlog_review_gate: {slug!r} {reason_kind} ({classes})",
                    blocked_at_step=step.label,
                    resume_token=run.idempotency_key,
                    detail={"slug": slug},
                )
                return (
                    overlap,
                    self._with_block(run, step.label, blocked),
                    self._blocked_sr(step, blocked),
                )

        return overlap, self._still_running(run, step.label), self._ok_sr(step)

    # -- opt-in grill digest (item 2: consumed, not decorative) ----------

    def _intake_grill_digest(self, run: LifecycleRun) -> str | None:
        """Resolve ``intake_grill``'s produced payload (when it ran) and render a digest.

        A *simple local digest pass* (Ruling C): reuses the exact ledger-lookup +
        :meth:`WorkflowHandoffResolver.render_digest` rendering every model step already
        writes through via ``produce()``, without joining ``_fragment_gate``'s declarative
        ``consumes``/``produces`` graph-completeness machinery. Returns ``None`` when no
        resolver is wired or ``intake_grill`` never produced a payload (it did not run, or
        this call resumed past it) — absence is never an error here, the grill is optional.
        """
        if self._handoff_resolver is None:
            return None
        try:
            resolved = self._handoff_resolver.resolve_required(
                run, producer_step="intake_grill", attempt=0
            )
        except (RequiredHandoffMissingError, MalformedHandoffError):
            return None
        return WorkflowHandoffResolver.render_digest(resolved)

    # -- model step (intake_grill / backlog_author) -----------------------

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
        if step.label == "backlog_author":
            # Item 2: when intake_grill ran (grill=True), its output must be CONSUMED, not
            # merely produced — inject a compact digest into the author's prompt.
            digest = self._intake_grill_digest(run)
            if digest:
                selected = "\n\n".join(filter(None, (selected, digest)))
        # One-shot resume-rejection digest for the resume-point step.
        resume_digest = self._resume_feedback.pop(step.label, None)
        if resume_digest:
            selected = "\n\n".join(filter(None, (selected, resume_digest)))
        suffix = build_fragment_suffix(
            self._fragment_bundle(step, fragment, shared),
            selected_context=selected,
            # Every backlog model step is a CREATE step (BacklogStep is kind-based, no
            # is_review field) — it emits an artifact, never a self-verdict (D-2 / A4).
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
                # Every backlog model step is a CREATE step: it must pass on a schema-valid
                # payload, never a verdict (L1).
                is_review=False,
                # Bug codex-live-workflow-sandbox-unavailable-in-hermes-worker (0.3.1
                # retest): a worker that "completes" without writing a backlog item must
                # BLOCK AT THIS STEP with the worker's own diagnostic (and get the one
                # bounded structural-correction retry), not sail through on its
                # step-output envelope and fail later at backlog_review_gate with no
                # trace of what the worker actually returned.
                deliverable_globs=(
                    (
                        f"repos/{self._context}/specs/backlog/**",
                        "specs/backlog/**",
                    )
                    if step.label == "backlog_author"
                    else ()
                ),
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
        return replace(
            run,
            phase=run.phase,
            status=LifecycleRunStatus.RUNNING,
            current_step=step_label,
            blocked=None,
        )

    @staticmethod
    def _with_block(run: LifecycleRun, step_label: str, blocked: BlockedState) -> LifecycleRun:
        return replace(
            run,
            phase=LifecyclePhase.BLOCKED,
            status=LifecycleRunStatus.BLOCKED,
            current_step=step_label,
            blocked=blocked,
        )

    @staticmethod
    def _advance(run: LifecycleRun) -> LifecycleRun:
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
