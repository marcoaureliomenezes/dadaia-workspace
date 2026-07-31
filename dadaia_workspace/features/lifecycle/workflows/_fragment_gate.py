"""``FragmentGateWorkflow`` base + ``_FragmentAssemblyMixin`` — the ONE prompt-assembly seam.

v0.1.57 FR1 folds the handoff-ledger workflow bodies
(``release_definition`` / ``audit``) onto a single generic
base, and shares the pure prompt-assembly helpers with the structurally-outlying
``backlog_definition`` body via a thin mixin. Before this dedup a role-grounding or
assembly fix had to land five times or land by luck; now it lands once.

Two collaborators live here:

* :class:`_FragmentAssemblyMixin` — the pure fragment-assembly helpers
  (``_prefix_with_static_inputs`` / ``_collect_static_inputs`` / ``_fragment_bundle`` /
  ``_select_context`` / ``_render_selection`` / ``_scope``). Shared by the base AND
  :class:`~dadaia_workspace.features.lifecycle.workflows.backlog_definition.BacklogDefinitionWorkflow`
  (which keeps its own kind-based dispatch + Python-disposing steps — it does NOT join the
  full base, per Ruling C). The converged ``_scope`` threads ``model_profile`` /
  ``resolved_model`` so backlog's ``PromptScope`` no longer drops the resolved model (the
  grill Problem #8 fix).
* :class:`FragmentGateWorkflow` — the full base for the handoff-ledger bodies. It owns
  the run loop, the model-step assembly + Python-owned gate, the run-scoped workflow-step
  handoff data plane, and the terminal Python gate. The five legitimate divergence axes are
  parameterized: the ``_COMMAND`` string, the ``_INITIAL_PHASE``, the terminal ``_TERMINAL_PHASE``
  (``release_definition`` transitions → IMPLEMENTATION; the others COMPLETE with no
  transition), the Step/Result dataclass types (generic ``StepT`` / ``ResultT`` + the
  ``_make_result`` factory). The empty-sequence ``ValueError`` message is derived from the
  class ``_WORKFLOW_LABEL`` so each body keeps its exact current text.

**Refactor trap — sequence-scoped iteration (the exact single-seam defect the dedup removes).**
``_produce_payload`` and ``_graph_completeness_check`` iterate the sequence threaded through
``run()`` — never a module-global ``_SEQUENCE``. Each body keeps its module-global
``_SEQUENCE`` by name (three guardrail suites import it), used only as ``run()``'s default
``sequence`` argument.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import ClassVar, Protocol

from dadaia_workspace.core.lifecycle_recovery import resume_command
from dadaia_workspace.core.models.lifecycle import (
    HARNESS_CLI_NAMES,
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
from dadaia_workspace.core.models.workflow_handoff import RetentionMode, WorkflowStepLedger
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStore
from dadaia_workspace.core.protocols.runtime_files import RuntimeFilePort
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
    SelectionResult,
    StaticInput,
)
from dadaia_workspace.features.lifecycle.fragments.loader import Fragment, FragmentLoader
from dadaia_workspace.features.lifecycle.personas.loader import resolve_persona_for_role
from dadaia_workspace.features.lifecycle.pipeline import InvalidResumeStepError, RuntimeFactory
from dadaia_workspace.features.lifecycle.prompt_builder import (
    FragmentBundle,
    LifecyclePromptBuilder,
    PromptPrefix,
    PromptScope,
    build_fragment_suffix,
    canonical_worker_output_ref,
    filter_context_spec_paths,
    worker_output_glob,
)
from dadaia_workspace.features.lifecycle.role_atoms import inject_role_atoms
from dadaia_workspace.features.lifecycle.run_store import (
    emit_progress,
    refuse_blocked_restart,
    refuse_completed_rerun,
)
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine
from dadaia_workspace.features.lifecycle.workflow_handoffs import (
    _NO_RELEASE_CONTEXT_COMMANDS,
    MalformedHandoffError,
    RequiredHandoffMissingError,
    WorkflowHandoffResolver,
    _compact_digest_text,
    durable_payload_from_result,
)


class AssemblyStep(Protocol):
    """The step attributes the pure fragment-assembly helpers read.

    Satisfied structurally by BOTH the four handoff-ledger step dataclasses (``ReleaseStep`` …)
    and the outlying ``BacklogStep`` — so ``_FragmentAssemblyMixin`` binds against a narrow
    contract common to every assembly consumer.
    """

    @property
    def label(self) -> str: ...
    @property
    def role(self) -> str: ...
    @property
    def fragment_id(self) -> str | None: ...
    @property
    def shared_fragment_ids(self) -> tuple[str, ...]: ...
    @property
    def model_profile(self) -> str | None: ...
    @property
    def resolved_model(self) -> ResolvedModelConfig | None: ...


class FragmentGateStep(AssemblyStep, Protocol):
    """The full handoff-ledger step contract the :class:`FragmentGateWorkflow` loop reads.

    Extends :class:`AssemblyStep` with the gate + data-plane attributes carried by the four
    handoff-ledger step dataclasses (``ReleaseStep`` / ``AuditStep`` / ``ResearchStep`` /
    ``BugReportStep``). ``BacklogStep`` does NOT satisfy this (no ``is_review`` / ``produces`` /
    ``consumes``) — it shares only the assembly mixin.
    """

    @property
    def is_review(self) -> bool: ...
    @property
    def runtime_kind(self) -> AgentRuntimeKind | None: ...
    @property
    def produces(self) -> str | None: ...
    @property
    def consumes(self) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class _StepOutcome:
    """The base's internal per-step outcome, mapped to each body's StepResult by ``_make_result``.

    Structurally the union of every body's ``*StepResult`` fields; the ``_make_result`` hook
    (the divergence axis "result factory") reshapes a tuple of these into the body's concrete
    result + step-result dataclasses.
    """

    label: str
    accepted: bool
    is_gate: bool
    fragment_id: str | None = None
    prompt_text: str | None = None
    runtime_kind: AgentRuntimeKind | None = None
    blocked: BlockedState | None = None


def next_attempt_for(ledger: WorkflowStepLedger, producer_step: str) -> int:
    """The attempt number a produce for *producer_step* must use.

    Bug ``r23-resume-overwrites-ledger-owned-step-payload``: every produce site hard-coded
    ``attempt=0``, so a resumed step produced at the SAME ledger key, ``upsert`` replaced
    the record, and the interrupted attempt's payload and content hash ceased to exist —
    destroying precisely the evidence an operator wants after an interruption.

    The data plane is immutable per ``(step, attempt)`` and always was. An attempt is not a
    slot to reuse; a resume is a NEW one.
    """
    latest = ledger.latest_attempt(producer_step)
    return 0 if latest is None else latest.attempt + 1


def _graph_recovery(run: LifecycleRun, step_label: str) -> str:
    """The recovery for every step-graph block: a real command, not advice about one.

    Five sites carried the identical prose ("re-run with --resume-from X; if the step
    graph itself is wrong ..."). Prose repeated five times is one defect written five
    times (bug ``r22-release-review-rejection-deadlocks``, escapability half), so they now
    share the one builder that knows how a resume is spelled.
    """
    return resume_command(
        command=run.command,
        run_id=run.run_id,
        step=step_label,
        context=run.context,
        release_id=run.release_id or "",
        note=(
            "if the step graph itself is wrong this is a library defect — "
            "register it with `dadaia bugs append`"
        ),
    )


def _is_rejected_verdict(blocked: BlockedState | None) -> bool:
    """True when a block carries an explicit reviewer REJECTED verdict (never transport noise)."""
    if blocked is None:
        return False
    if str(blocked.detail.get("verdict", "")).upper() == "REJECTED":
        return True
    return "rejected" in blocked.reason.lower()


def prescribe_review_recovery(
    blocked: BlockedState,
    *,
    command: str,
    context: str,
    release_id: str,
    run_id: str,
    create_step: str,
    runtime_kind: AgentRuntimeKind,
) -> BlockedState:
    """Attach the exact recovery command to a rejected-review block.

    A reviewer returns a verdict and findings; it never fills ``operator_command``. The
    engine spends one bounded in-run revision and then returned that RAW block, so a
    release whose review rejected twice handed the operator a rejection and no way
    forward — the validator's report was that it could not proceed "without inventing a
    change" (bug r9-plan-review-missing-operator-command). Every other gate prescribes
    its recovery; this is the one a real release hits most often.

    The command names the SAME run, the create step this review consumes, and the run's
    OWN harness — a remedy that silently switches runtime is its own bug
    (r6h-backlog-remedy-command-loses-fake-harness). An ``operator_command`` that is
    already set is never overwritten: a more specific gate remedy always wins.
    """
    if blocked.operator_command:
        return blocked
    verb = command.replace("_", "-")
    return replace(
        blocked,
        operator_command=(
            f"dadaia lifecycle {verb} --context {context} --release-id {release_id} "
            f"--run-id {run_id} --harness {HARNESS_CLI_NAMES.get(runtime_kind, 'codex')} "
            f"--resume-from {create_step}  # address the review findings above, then re-run"
        ),
    )


class _FragmentAssemblyMixin:
    """Pure fragment-assembly helpers shared by the base and ``BacklogDefinitionWorkflow``.

    These methods carry no workflow control flow — they turn a step + its fragment into a
    cacheable prefix, a fragment bundle, resolved dynamic context, and a bounded worker
    :class:`PromptScope`. The consuming class supplies the instance state declared below in
    its ``__init__``.
    """

    _prefix: PromptPrefix | None
    _loader: FragmentLoader
    _selector: ContextSelector
    _context: str
    _release_id: str

    @property
    def _repo_slug(self) -> str:
        """The repo DIRECTORY name for this context — derived, never assumed.

        Path templates carry ``repos/{context}/…``, and formatting them with the context
        NAME broke every context whose name differs from its ``--repo`` slug: the write
        scope pointed at a directory that does not exist, so the worker's write fell out of
        scope and the run reported success having written nothing
        (bug a1-context-specs-resolution-ignores-repo-slug).

        Taken from the already-resolved ``specs_dir`` (``<ws>/repos/<slug>/specs``) rather
        than re-derived from the registry, so there is exactly one resolution and the
        template can never disagree with the directory the selector actually reads.
        """
        return self._selector.spec_context.specs_dir.parent.name

    # -- static-input injection (folded into the cacheable prefix) -------

    def _prefix_with_static_inputs(self, sequence: tuple[AssemblyStep, ...]) -> PromptPrefix | None:
        """Return the prefix augmented with every fragment's resolved static_inputs.

        Static inputs (e.g. ``specs/constitution.md``, ``specs/memory/architecture.md``) are
        stable across the whole release, so they belong in the cacheable prefix. The
        de-duplicated declared static inputs across all model-step fragments are resolved via
        the context selector (graceful skip when absent) and re-derived into a single prefix.
        With no resolvable static inputs the original prefix is returned unchanged — the
        byte-identity guard for runs with no static inputs is preserved exactly.
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

    def _collect_static_inputs(self, sequence: tuple[AssemblyStep, ...]) -> tuple[StaticInput, ...]:
        """Resolve the de-duplicated static_inputs declared across the sequence's fragments.

        Each entry is resolved at most once (first declaration order wins). A declared static
        input absent from this context is included with ``present=False`` so the skip is
        recorded/auditable; only present ones reach the prefix.
        """
        seen: set[str] = set()
        out: list[StaticInput] = []
        for step in sequence:
            if step.fragment_id is None:
                continue
            fragments = (
                self._loader.load_fragment(step.fragment_id),
                *(self._loader.load_fragment(fid) for fid in step.shared_fragment_ids),
            )
            for fragment in fragments:
                for declared in fragment.static_inputs:
                    ref = declared.strip().lstrip("/")
                    if ref in seen:
                        continue
                    seen.add(ref)
                    out.append(self._selector.resolve_static_input(declared))
        return tuple(out)

    # -- assembly helpers ------------------------------------------------

    def _fragment_bundle(
        self, step: AssemblyStep, fragment: Fragment, shared: tuple[Fragment, ...]
    ) -> FragmentBundle:
        return FragmentBundle(
            fragment_id=fragment.id,
            role=step.role,
            body=fragment.body,
            output_schema=fragment.output_schema,
            shared_bodies=tuple(frag.body for frag in shared),
            shared_ids=tuple(frag.id for frag in shared),
        )

    def _select_context(
        self, step: AssemblyStep, fragments: tuple[Fragment, ...]
    ) -> SelectionAudit:
        """Resolve main and shared fragment inputs under their declared policies."""
        results: list[SelectionResult] = []
        seen: set[str] = set()
        for fragment in fragments:
            names = tuple(name for name in fragment.dynamic_inputs if name not in seen)
            seen.update(names)
            if not names:
                continue
            selected = self._selector.select_all(
                step.label,
                names,
                MaxContextPolicy.parse(fragment.max_context_policy),
                fragment_ids=(fragment.id,),
            )
            results.extend(selected.results)
        return SelectionAudit(
            step=step.label,
            results=tuple(results),
            fragment_ids=tuple(fragment.id for fragment in fragments),
        )

    @staticmethod
    def _render_selection(audit: SelectionAudit) -> str:
        blocks = [
            f"### {result.name}\n{result.content}".rstrip()
            for result in audit.results
            if result.content.strip()
        ]
        return "\n\n".join(blocks)

    def _scope(self, step: AssemblyStep, run_id: str, suffix: str) -> PromptScope:
        """Build the per-step bounded worker scope (converged — threads the resolved model).

        The unified scope threads ``model_profile`` + ``resolved_model`` (grill Problem #8):
        ``backlog_definition`` previously dropped both although ``BacklogStep`` carries them,
        so its worker ran on the wrong model. The four handoff-ledger bodies already threaded
        them, so this is byte-neutral for them (the golden excludes those fields, Q1) and the
        RED-first ``resolved_model is not None`` backlog test proves the convergence.
        """
        # Step-declared extra write paths (bug
        # release-definition-create-steps-cannot-write-specs): a create step whose
        # deliverable lives outside the handoff zone (SPEC/PLAN/TASKS under
        # specs/releases/) declares it on the step model; placeholders are expanded
        # against this workflow's context/release.
        extra = tuple(
            pattern.format(context=self._repo_slug, release_id=self._release_id)
            for pattern in getattr(step, "extra_allowed_paths", ())
        )
        extra = filter_context_spec_paths(
            extra,
            workspace_root=getattr(self, "_artifact_root", None),
            specs_dir=self._selector.spec_context.specs_dir,
        )
        return PromptScope(
            role=step.role,
            context=self._context,
            release_id=self._release_id,
            task_id=f"{run_id}:{step.label}",
            prompt=suffix,
            allowed_paths=(worker_output_glob(self._context), *extra),
            required_evidence=(GateEvidenceKind.HANDOFF,),
            model_profile=step.model_profile,
            resolved_model=step.resolved_model,
            persona=resolve_persona_for_role(step.role),
        )


class FragmentGateWorkflow[StepT: FragmentGateStep, ResultT](_FragmentAssemblyMixin):
    """The one prompt-assembly + Python-gate seam for the four handoff-ledger workflow bodies.

    Python owns step order and the gate decisions; each model step's prompt is assembled from
    its fragment bundle + the dynamically selected context (bounded by ``max_context_policy``)
    + the output schema + the discrete ``(harness, model)`` for the step. Stable static inputs
    fold once into a cacheable :class:`PromptPrefix`. Each review step's structured verdict is
    read by Python via the typed gate; a REJECTED / missing-evidence review BLOCKS advancement.
    The terminal Python gate carries no model and either transitions the phase
    (``_TERMINAL_PHASE``) or COMPLETEs in place.

    Subclasses set the five divergence hooks (``_COMMAND`` / ``_WORKFLOW_LABEL`` /
    ``_INITIAL_PHASE`` / ``_TERMINAL_PHASE`` + the ``_make_result`` factory), keep their own
    Step/Result dataclasses + module-global ``_SEQUENCE``, and expose a thin ``run()`` whose
    default ``sequence`` argument is that ``_SEQUENCE``.
    """

    #: ``LifecycleRun.command`` for this workflow (e.g. ``"release_definition"``).
    _COMMAND: ClassVar[str]
    #: The label used to derive the empty-sequence ``ValueError`` message so each body keeps
    #: its exact current text (``"release-definition"`` / ``"audit"``), hence a dedicated
    #: label rather than reusing ``_COMMAND``).
    _WORKFLOW_LABEL: ClassVar[str]
    #: The phase the run starts in.
    _INITIAL_PHASE: ClassVar[LifecyclePhase]
    #: The phase the terminal gate transitions to on success, or ``None`` to COMPLETE in place
    #: with no transition (``release_definition`` → IMPLEMENTATION; audit keeps its phase).
    _TERMINAL_PHASE: ClassVar[LifecyclePhase | None] = None

    #: Advisory review objections from the last ``run()`` — reviews accepted after their
    #: bounded revision was spent. A model verdict is advisory, never terminal, but it is
    #: never silent either: bodies attach these to their result so the operator sees them.
    _last_warnings: tuple[str, ...] = ()
    #: Advisory objections collected during the current ``run()`` (drained into the result).
    _advisories: list[str]

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
        artifact_root: Path | None = None,
        runtime_files: RuntimeFilePort | None = None,
        definition_committer: Callable[[], None] | None = None,
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
        # The resolved governance snapshot (v0.1.56 / LAW 7). When present it is frozen onto
        # the run BEFORE the first step; an overlay mutated after start cannot change the
        # in-flight run because the run carries this immutable snapshot. The replace-based step
        # helpers preserve it across every step transition.
        self._policy_snapshot = policy_snapshot
        # When wired, the resolver drives the run-scoped workflow-step handoff data plane: each
        # step resolves its declared upstream payloads by exact (run id, producer step, attempt)
        # and writes its own produced payload. When None the workflow behaves exactly as before
        # (back-compat) — the produces/consumes edges are inert.
        self._handoff_resolver = handoff_resolver
        # Bug gate-accepts-phantom-artifact-evidence: when wired (production builders pass
        # the workspace root), the structural gate additionally requires every declared
        # artifact ref to EXIST under this root.
        self._artifact_root = artifact_root
        self._runtime_files = runtime_files
        # Bug fake-release-definition-leaves-dirty-worktree: when wired (production
        # builders), a COMPLETED definition commits the context repo's definition
        # artifacts — implementation preflight never inherits a dirty tree. ``None``
        # (fixtures) keeps behavior byte-identical; the call is best-effort.
        self._definition_committer = definition_committer
        # Bug resumed-definition-step-blind-to-rejecting-review-feedback: on a resume of a
        # run that blocked on a review rejection, the resume-point step's prompt carries a
        # compact digest of that prior BlockedState (the definition-sequence analogue of
        # implementation retry rejection digest). Keyed by step label; consumed
        # exactly once by the first re-run of that step.
        self._resume_feedback: dict[str, str] = {}

    # -- post-acceptance hook (divergence axis) --------------------------

    def _on_step_accepted(self, step: StepT) -> BlockedState | None:
        """Run a deterministic post-step check; return a block when it fails.

        ``release_definition`` overrides this to flip the reviewed artifact's canonical
        ``> **Status:**`` token to ``Aprovado`` when its review gate approves and to
        validate plan dependency structure before model review. The default accepts.
        """
        return None

    def _terminal_semantic_block(
        self, run: LifecycleRun, step: StepT, sequence: tuple[StepT, ...]
    ) -> BlockedState | None:
        """Validate workflow-specific cross-step semantics after graph completeness."""
        return None

    # -- result factory (divergence hook) -------------------------------

    def _make_result(
        self,
        *,
        run_id: str,
        completed: bool,
        final_phase: LifecyclePhase,
        outcomes: tuple[_StepOutcome, ...],
        blocked: BlockedState | None,
    ) -> ResultT:
        """Reshape the base's internal outcomes into this body's Result dataclass.

        Overridden by each body (the "result factory" divergence axis) to build its concrete
        ``*Result`` + ``*StepResult`` types from the generic outcomes.
        """
        raise NotImplementedError

    # -- the run loop ----------------------------------------------------

    def _run_sequence(
        self, run_id: str, sequence: tuple[StepT, ...], *, resume_from: str | None = None
    ) -> ResultT:
        """Execute *sequence*; stop at the first blocked gate; finish per the terminal gate.

        *resume_from* (bug blocked-definition-run-cannot-resume-from-step) re-executes an
        existing run from the named step: the prior run record is loaded, its ledger
        entries for the steps BEFORE the resume point are kept (so ``consumes`` edges
        still resolve), only the resume-point-onward payloads are reclaimed, and the
        already-approved upstream steps are not re-run.
        """
        if not sequence:
            raise ValueError(f"{self._WORKFLOW_LABEL} workflow requires at least one step")
        # Static inputs are folded PER STEP at model-step time (each step pays only for
        # the static inputs its own fragments declare) — never unioned across the whole
        # sequence, which taxed every step with every other step's inputs.
        if resume_from is None:
            # Idempotency guard (bug completed-workflow-rerun-not-refused): a COMPLETED
            # run id refuses cleanly; blocked runs stay restartable/resumable.
            refuse_completed_rerun(self._run_store, run_id)
            refuse_blocked_restart(self._run_store, run_id)
            # Restart semantics: a fresh run over an existing run_id replaces the record
            # (and its ledger), so reclaim the orphaned payload zone first — otherwise the
            # prior generation's immutable attempt-0 files block this run's produce() (bug
            # rerun-of-run-id-collides-with-immutable-payload-zone).
            if self._handoff_resolver is not None:
                self._handoff_resolver.reset_run_zone(
                    run_id,
                    worker_output_refs=tuple(
                        canonical_worker_output_ref(self._context, f"{run_id}:{step.label}")
                        for step in sequence
                        if step.fragment_id is not None
                    ),
                    context=self._context,
                    release_id=self._zone_release_id(),
                )
            run = LifecycleRun(
                run_id=run_id,
                context=self._context,
                release_id=self._release_id,
                command=self._COMMAND,
                phase=self._INITIAL_PHASE,
                status=LifecycleRunStatus.RUNNING,
                current_step=sequence[0].label,
                idempotency_key=run_id,
                workflow_policy=self._policy_snapshot,
            )
            remaining = sequence
        else:
            labels = tuple(step.label for step in sequence)
            if resume_from not in labels:
                raise InvalidResumeStepError.for_labels(resume_from, labels)
            prior = self._run_store.load(run_id)
            if prior is None:
                raise ValueError(
                    f"cannot resume run {run_id!r} from {resume_from!r}: no persisted run"
                )
            index = labels.index(resume_from)
            if prior.blocked is not None:
                # Feed the prior rejection back into the resumed step (bug
                # resumed-definition-step-blind-to-rejecting-review-feedback) — without it
                # the revision worker re-authors blind and the rejecting reviewer repeats
                # the identical findings forever.
                self._resume_feedback[resume_from] = self._render_prior_block_digest(prior.blocked)
            if self._handoff_resolver is not None:
                # Reclaim the run's temporary worker outputs only. The resumed steps'
                # DURABLE payloads are deliberately left alone (bug
                # r25-resume-still-overwrites-attempt-zero-on-the-cli-path): purging them
                # made sense only while a resumed step re-produced at ``attempt-0`` and
                # would have collided with its own previous file. It now produces at the
                # NEXT attempt — a different filename — so nothing collides, and deleting
                # the earlier payload would destroy the one thing an operator reads after
                # an interruption: what the interrupted attempt actually wrote.
                self._handoff_resolver.reset_run_zone(
                    run_id,
                    producer_steps=frozenset(),
                    worker_output_refs=tuple(
                        canonical_worker_output_ref(self._context, f"{run_id}:{step.label}")
                        for step in sequence[index:]
                        if step.fragment_id is not None
                    ),
                    context=self._context,
                    release_id=self._zone_release_id(),
                )
            # Every prior record is KEPT, including the resumed steps' own. Dropping them
            # is what made ``next_attempt_for`` read an empty ledger and answer 0 again, so
            # the resumed produce landed back on attempt-0 and replaced it in place — the
            # exact defect the attempt numbering was introduced to end. A resume adds to
            # the record; it never rewrites it.
            kept = prior.workflow_steps.records
            run = replace(
                prior,
                phase=self._INITIAL_PHASE,
                status=LifecycleRunStatus.RUNNING,
                current_step=resume_from,
                blocked=None,
                workflow_steps=WorkflowStepLedger(records=kept),
                # Same observability law as the in-run revision: a resumed run rewinds
                # to RUNNING + kept-ledger, and the record must SAY so (bug
                # release-definition-retry-stalls-with-empty-workflow-steps-041).
                revision_note=f"resumed run from step {resume_from!r}",
            )
            remaining = sequence[index:]
        self._run_store.save(run)

        outcomes: list[_StepOutcome] = []
        revisions_used: dict[str, int] = {}
        self._advisories = []
        steps_seq = list(remaining)
        idx = 0
        while idx < len(steps_seq):
            step = steps_seq[idx]
            live_step = (
                step.fragment_id is not None
                and (getattr(step, "runtime_kind", None) or self._default_kind)
                is not AgentRuntimeKind.FAKE
            )
            if live_step:
                emit_progress(
                    f"{self._WORKFLOW_LABEL} step {step.label!r} ({idx + 1}/{len(steps_seq)}) "
                    "started — a live worker step may take several minutes; it times out "
                    "and blocks cleanly on its own"
                )
            if step.fragment_id is None:
                run, outcome = self._run_terminal_gate(run, step, sequence)
            else:
                run, outcome = self._run_model_step(
                    run,
                    step,
                    sequence,
                    # Once this review has spent its one bounded revision its verdict becomes
                    # ADVISORY: a further REJECTED is recorded as a warning, never a block.
                    # A model verdict is never terminal: it is advisory once its one
                    # bounded revision is spent, AND immediately when there is no create
                    # step to revise (otherwise such a review would block forever, which is
                    # the very deadlock this rule removes).
                    review_is_advisory=bool(
                        getattr(step, "is_review", False)
                        and (
                            revisions_used.get(f"review:{step.label}", 0) >= 1
                            or self._revision_target(step, list(sequence)) is None
                        )
                    ),
                )
            if live_step:
                emit_progress(
                    f"{self._WORKFLOW_LABEL} step {step.label!r} "
                    + ("accepted" if outcome.accepted else "blocked")
                )
            self._run_store.save(run)
            outcomes.append(outcome)
            if outcome.accepted:
                post_accept_block = self._on_step_accepted(step)
                if post_accept_block is not None:
                    run = self._with_step_outcome(
                        run, post_accept_block.blocked_at_step, post_accept_block
                    )
                    self._run_store.save(run)
                    outcomes.append(
                        _StepOutcome(
                            label=post_accept_block.blocked_at_step,
                            accepted=False,
                            is_gate=True,
                            blocked=post_accept_block,
                        )
                    )
                    # Deterministic post-accept lint: revise the SAME create step once
                    # with the lint digest instead of blocking the whole run (the
                    # release-definition-lint-restart-advice fix, in-run half).
                    revised = self._begin_revision(
                        run,
                        target_label=step.label,
                        blocked=post_accept_block,
                        steps_seq=steps_seq,
                        revisions_used=revisions_used,
                        budget_key=f"lint:{step.label}",
                    )
                    if revised is not None:
                        run, idx = revised
                        continue
                    self._last_warnings = tuple(self._advisories)
                    return self._make_result(
                        run_id=run_id,
                        completed=False,
                        final_phase=run.phase,
                        outcomes=tuple(outcomes),
                        blocked=post_accept_block,
                    )
                idx += 1
                continue
            # Review REJECTED verdict: one bounded in-run revision of the create step
            # this review consumes, with the rejection digest injected.
            if step.is_review and run.blocked is not None and _is_rejected_verdict(run.blocked):
                target = self._revision_target(step, steps_seq)
                rejection = run.blocked
                if target is not None:
                    revised = self._begin_revision(
                        run,
                        target_label=target,
                        blocked=rejection,
                        steps_seq=steps_seq,
                        revisions_used=revisions_used,
                        budget_key=f"review:{step.label}",
                    )
                    if revised is not None:
                        run, idx = revised
                        continue
                # The budget is now spent, so the NEXT attempt of this review runs in
                # ADVISORY mode (see the ``review_is_advisory`` argument at the call site):
                # a further REJECTED verdict is recorded as a warning and the step proceeds,
                # payload and all. Reaching this line therefore means the block is not a
                # model verdict — fall through and report it like any deterministic block.
                del rejection
            self._last_warnings = tuple(self._advisories)
            if run.blocked is None:
                # Bug r15-release-definition-running-after-accepted-draft: a sequence that
                # stops without a RECORDED block left the run persisted as `running` with
                # no reason and no remedy, and the prescribed recovery reproduced the same
                # state — a dead end the operator cannot read or escape. Stopping is
                # allowed; stopping SILENTLY is not.
                last = outcomes[-1].label if outcomes else (sequence[0].label if sequence else "?")
                synthesized = BlockedState(
                    reason=(
                        f"the sequence stopped after step {last!r} without reaching a "
                        "terminal state and without recording a block — the step's worker "
                        "did not produce an acceptable result. Inspect the run's step "
                        "payload for the worker's own output before resuming."
                    ),
                    blocked_at_step=last,
                    resume_token=run.idempotency_key,
                    operator_command=(
                        f"dadaia lifecycle status --run-id {run_id}  # then resume from "
                        f"the step it names, or use a fresh --run-id to start over"
                    ),
                    detail={"step": last, "gate": "non-terminal-stop-v1"},
                )
                run = replace(
                    run,
                    phase=LifecyclePhase.BLOCKED,
                    status=LifecycleRunStatus.BLOCKED,
                    current_step=last,
                    blocked=synthesized,
                )
                self._run_store.save(run)
            return self._make_result(
                run_id=run_id,
                completed=False,
                final_phase=run.phase,
                outcomes=tuple(outcomes),
                blocked=run.blocked,
            )
        # Post-completion hook (bug definition-commit-gate-never-repoints-active-md):
        # bodies override to apply their deterministic Python-owned completion effects
        # (e.g. release_definition rewrites ACTIVE.md). Runs only on a FULLY completed
        # sequence — a blocked run never reaches it.
        self._on_sequence_completed()
        self._last_warnings = tuple(self._advisories)
        return self._make_result(
            run_id=run_id,
            completed=True,
            final_phase=run.phase,
            outcomes=tuple(outcomes),
            blocked=None,
        )

    def _on_sequence_completed(self) -> None:
        """Called once after every step of the sequence is accepted. Default: no-op."""

    def _zone_release_id(self) -> str | None:
        """The release-aware handoff zone this workflow's payloads live in.

        Mirrors ``workflow_handoffs._zone_release_id`` for reclaim-time callers that
        have no run object yet: a no-release-context command (backlog definition)
        routes to the shared backlog zone (``None``); everything else to its release.
        """
        return None if self._COMMAND in _NO_RELEASE_CONTEXT_COMMANDS else self._release_id

    # -- bounded in-run revision -----------------------------------------

    @staticmethod
    def _revision_target(step: StepT, steps_seq: list[StepT]) -> str | None:
        """The create step a rejected review revises: its first consumed non-review model step."""
        by_label = {s.label: s for s in steps_seq}
        for producer in step.consumes:
            candidate = by_label.get(producer)
            if (
                candidate is not None
                and candidate.fragment_id is not None
                and not candidate.is_review
            ):
                return producer
        return None

    def _begin_revision(
        self,
        run: LifecycleRun,
        *,
        target_label: str,
        blocked: BlockedState,
        steps_seq: list[StepT],
        revisions_used: dict[str, int],
        budget_key: str,
    ) -> tuple[LifecycleRun, int] | None:
        """Rewind the run to *target_label* once, feeding the block digest into its re-run.

        Returns the reset run + the loop index to continue from, or ``None`` when the
        revision budget for *budget_key* is spent (at most one revision per gate) — the
        caller then blocks exactly as before, so worst-case behavior is unchanged.
        """
        if revisions_used.get(budget_key, 0) >= 1:
            return None
        labels = [s.label for s in steps_seq]
        if target_label not in labels:
            return None
        revisions_used[budget_key] = 1
        target_idx = labels.index(target_label)
        resumed_labels = set(labels[target_idx:])
        self._resume_feedback[target_label] = self._render_prior_block_digest(blocked)
        if self._handoff_resolver is not None:
            self._handoff_resolver.reset_run_zone(
                run.run_id,
                producer_steps=resumed_labels,
                worker_output_refs=tuple(
                    canonical_worker_output_ref(self._context, f"{run.run_id}:{s.label}")
                    for s in steps_seq[target_idx:]
                    if s.fragment_id is not None
                ),
                context=self._context,
                release_id=self._zone_release_id(),
            )
        kept = tuple(
            record
            for record in run.workflow_steps.records
            if record.producer_step not in resumed_labels
        )
        run = replace(
            run,
            phase=self._INITIAL_PHASE,
            status=LifecycleRunStatus.RUNNING,
            current_step=target_label,
            blocked=None,
            workflow_steps=WorkflowStepLedger(records=kept),
            # Bug release-definition-retry-stalls-with-empty-workflow-steps-041: make
            # the bounded revision OBSERVABLE in the persisted record — a bare RUNNING
            # + reclaimed ledger reads exactly like the old stall to any watcher.
            revision_note=(
                f"bounded revision 1/1 of {target_label!r} after "
                f"{blocked.blocked_at_step!r} rejected: {blocked.reason}"
            ),
        )
        self._run_store.save(run)
        return run, target_idx

    # -- model step ------------------------------------------------------

    def _run_model_step(
        self,
        run: LifecycleRun,
        step: StepT,
        sequence: tuple[StepT, ...],
        *,
        review_is_advisory: bool = False,
    ) -> tuple[LifecycleRun, _StepOutcome]:
        assert step.fragment_id is not None
        fragment = self._loader.load_fragment(step.fragment_id)
        shared = tuple(self._loader.load_fragment(fid) for fid in step.shared_fragment_ids)

        # Resolve every declared upstream payload BEFORE the prompt runs (A19/A20/A25). A
        # missing/malformed required upstream BLOCKS the step here — the worker is never run on
        # incomplete inputs. When no resolver is wired this is a no-op.
        run, upstream_block, digests = self._resolve_upstream(run, step)
        if upstream_block is not None:
            run = self._with_step_outcome(run, step.label, upstream_block)
            self._run_store.save(run)
            return run, _StepOutcome(
                label=step.label,
                accepted=False,
                is_gate=step.is_review,
                fragment_id=step.fragment_id,
                runtime_kind=step.runtime_kind or self._default_kind,
                blocked=upstream_block,
            )

        audit = self._select_context(step, (fragment, *shared))
        run = record_injected_context(run, audit)

        selected = self._render_selection(audit)
        # Bug release-definition-has-no-demand-channel-for-review-corrections: when a
        # review REJECTS, the operator's only channel into the next attempt was the
        # engine's own rejection digest — they could not supply the decision the reviewer
        # asked for, only re-roll. An operator demand, when supplied, is injected into
        # every executed model step exactly as backlog-definition already does.
        demand_text = getattr(self, "_operator_demand", None)
        if demand_text:
            selected = "\n\n".join(filter(None, (f"## Operator demand\n\n{demand_text}", selected)))
        # One-shot prior-rejection digest for the resume-point step (bug
        # resumed-definition-step-blind-to-rejecting-review-feedback).
        resume_digest = self._resume_feedback.pop(step.label, None)
        if resume_digest:
            digests = (*digests, resume_digest)
        if digests:
            selected = "\n\n".join(filter(None, (selected, *digests)))
        suffix = build_fragment_suffix(
            self._fragment_bundle(step, fragment, shared),
            selected_context=selected,
            is_review=step.is_review,
        )
        # v0.1.57 FR2 (A1): append the step role's mapped memory atom(s) + record their refs.
        # The single resolve-and-inject helper; specs_dir comes from the wired selector's spec
        # context. Independent of the fragment's dynamic_inputs — role alone guarantees grounding.
        run, suffix = inject_role_atoms(
            run=run,
            step_label=step.label,
            role=step.role,
            specs_dir=self._selector.spec_context.specs_dir,
            prompt=suffix,
        )
        kind = step.runtime_kind or self._default_kind
        runtime = self._runtime_factory(kind)
        scope = self._scope(step, run.run_id, suffix)
        # Per-step prefix: only THIS step's declared static inputs ride along.
        step_prefix = self._prefix_with_static_inputs((step,))
        built = self._prompt_builder.build(
            scope, runtime=runtime.runtime_kind(), prefix=step_prefix
        )

        # Python owns the gate, REVIEW-ONLY for the verdict (v0.1.31 / L1). A review step runs
        # the worker and reads its structured verdict (APPROVED + in-scope evidence => pass;
        # REJECTED or missing evidence => BlockedState); a create step passes on a schema-valid
        # payload + in-scope paths regardless of the verdict field. The worker runs ONCE; its
        # structured output is reused to write the step's produced payload.
        runner = LifecycleAgentRunner(
            runtime=runtime,
            state_machine=self._state_machine,
            artifact_root=self._artifact_root,
            runtime_files=self._runtime_files,
        )
        # Deliverable-zone requirement (bug
        # create-step-gate-accepts-refusal-handoff-as-success): a create step that
        # declares extra write paths must actually deliver inside them.
        step_deliverable = getattr(step, "deliverable", None)
        if step_deliverable:
            # Exact-file deliverable (bug
            # release-definition-completes-without-persisting-artifacts): the step
            # passes only when ITS artifact was written, not any write in the zone.
            deliverable_globs = (
                f"repos/{self._repo_slug}/specs/releases/{self._release_id}/{step_deliverable}",
                f"specs/releases/{self._release_id}/{step_deliverable}",
            )
        else:
            deliverable_globs = tuple(
                pattern.format(context=self._repo_slug, release_id=self._release_id)
                for pattern in getattr(step, "extra_allowed_paths", ())
            )
        worker_result, blocked = runner.evaluate_gate_with_result(
            run,
            AgentRunnerInput(
                request=built.request,
                target_phase=run.phase,
                current_step=step.label,
                is_review=step.is_review and getattr(step, "blocks_on_rejection", True),
                deliverable_globs=deliverable_globs,
            ),
        )
        # A MODEL VERDICT IS ADVISORY, NEVER TERMINAL. Once this review has spent its one
        # bounded revision, a further REJECTED verdict is recorded as a warning and the step
        # proceeds — including producing its payload, so the ledger stays complete and the
        # commit gate is not starved downstream. Only the model's opinion is downgraded:
        # every deterministic block (missing evidence, out-of-scope write, malformed handoff)
        # is left exactly as it was, because those can be satisfied by construction.
        if review_is_advisory and _is_rejected_verdict(blocked):
            self._advisories.append(
                f"[review-advisory] {step.label}: {blocked.reason if blocked else ''} "
                "— accepted after the bounded revision was spent; a model verdict is "
                "advisory, never terminal. Address it in the next release, or re-run "
                "with --demand."
            )
            blocked = None
        # Write the produced payload before acknowledging upstream consumption. A worker can
        # satisfy the generic transport gate yet still violate its domain handoff schema; that
        # is a deterministic BLOCK, not an exception and not a consumed upstream message.
        if blocked is None:
            try:
                run = self._produce_payload(run, step, worker_result, sequence)
            except MalformedHandoffError as exc:
                blocked = BlockedState(
                    operator_command=_graph_recovery(run, step.label),
                    reason=f"worker output violates {step.produces}: {exc}",
                    blocked_at_step=step.label,
                    detail={"output_schema": str(step.produces)},
                )
            else:
                run = self._record_consumptions(run, step)
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
        return run, _StepOutcome(
            label=step.label,
            accepted=blocked is None,
            is_gate=step.is_review,
            fragment_id=step.fragment_id,
            prompt_text=built.prompt_text,
            runtime_kind=kind,
            blocked=blocked,
        )

    @staticmethod
    def _render_prior_block_digest(blocked: BlockedState) -> str:
        """Render the prior run's BlockedState as a compact revision brief.

        Includes the blocking step, the gate reason (which names an explicit review
        verdict + its reason since bug blocked-reason-misreports-rejected-verdict), and
        every detail entry — notably ``verdict``/``verdict_reason`` and any artifact or
        diagnostic refs the worker can open for the full findings.

        Bounded (bug impl-reviews-retry-prompt-exceeds-codex-window): each detail value
        is compacted and the whole brief is capped — an unbounded findings dump once
        pushed the resumed step's prompt past the Codex context window. The full
        findings stay reachable through the artifact/diagnostic refs in the brief.
        """
        lines = [
            "## Prior rejection feedback (resumed run)",
            f"The previous run of this workflow blocked at step "
            f"'{blocked.blocked_at_step}': {blocked.reason}",
        ]
        for key, value in sorted(blocked.detail.items()):
            lines.append(f"- {key}: {_compact_digest_text(str(value))}")
        lines.append(
            "Revise the artifact so every point above is addressed; the same reviewer "
            "gate runs again after this step."
        )
        rendered = "\n".join(lines)
        limit = 8000
        if len(rendered) > limit:
            rendered = (
                rendered[:limit]
                + "\n- [digest truncated: full findings at the artifact/diagnostic refs above]"
            )
        return rendered

    @staticmethod
    def _with_step_outcome(
        run: LifecycleRun, step_label: str, blocked: BlockedState | None
    ) -> LifecycleRun:
        """Record a model step's outcome on the run, keeping the workflow phase.

        Uses :func:`dataclasses.replace` so every additive-optional field — notably the
        ``workflow_steps`` ledger and the ``workflow_policy`` snapshot — is preserved across
        the step transition rather than silently reset.
        """
        status = LifecycleRunStatus.BLOCKED if blocked is not None else LifecycleRunStatus.RUNNING
        phase = LifecyclePhase.BLOCKED if blocked is not None else run.phase
        return replace(run, phase=phase, status=status, current_step=step_label, blocked=blocked)

    # -- workflow-step handoff data plane -------------------------------------

    def _resolve_upstream(
        self, run: LifecycleRun, step: StepT
    ) -> tuple[LifecycleRun, BlockedState | None, tuple[str, ...]]:
        """Resolve every declared upstream payload by exact (run, producer step, attempt).

        Returns the (possibly unchanged) run, a :class:`BlockedState` when a required upstream
        is missing/malformed (A20), and the compact digests to inject. A no-op when no resolver
        is wired or the step declares no ``consumes`` edges.
        """
        if self._handoff_resolver is None or not step.consumes:
            return run, None, ()
        digests: list[str] = []
        for producer in step.consumes:
            try:
                # The LATEST attempt, never a literal zero: after a resume, attempt 0 is
                # the interrupted one, and consuming it would be strictly worse than the
                # overwrite this numbering replaced
                # (r23-resume-overwrites-ledger-owned-step-payload).
                latest_record = run.workflow_steps.latest_attempt(producer)
                resolved = self._handoff_resolver.resolve_required(
                    run,
                    producer_step=producer,
                    attempt=0 if latest_record is None else latest_record.attempt,
                )
            except (RequiredHandoffMissingError, MalformedHandoffError) as exc:
                blocked = BlockedState(
                    operator_command=_graph_recovery(run, step.label),
                    reason=f"required upstream handoff unavailable: {exc}",
                    blocked_at_step=step.label,
                    detail={"producer_step": producer, "consumer_step": step.label},
                )
                return run, blocked, ()
            digests.append(WorkflowHandoffResolver.render_digest(resolved))
        return run, None, tuple(digests)

    def _record_consumptions(self, run: LifecycleRun, step: StepT) -> LifecycleRun:
        """Record this step's consumption of each declared upstream payload (A22)."""
        if self._handoff_resolver is None:
            return run
        for producer in step.consumes:
            # Ack the attempt actually consumed. Acking attempt 0 after a resume marks the
            # wrong payload as consumed, which drives the produced -> consumed_all
            # transition and thus cleanup eligibility for a payload nobody read.
            produced = run.workflow_steps.latest_attempt(producer)
            consumed = run.workflow_steps.latest_attempt(step.label)
            run = self._handoff_resolver.record_consumption(
                run,
                producer_step=producer,
                producer_attempt=0 if produced is None else produced.attempt,
                consumer_step=step.label,
                consumer_attempt=0 if consumed is None else consumed.attempt,
            )
        return run

    def _produce_payload(
        self,
        run: LifecycleRun,
        step: StepT,
        worker_result: AgentRunResult,
        sequence: tuple[StepT, ...],
    ) -> LifecycleRun:
        """Write this step's immutable produced payload + ledger entry (A18/A21).

        ``declared_consumers`` are the downstream steps in the RUN-SCOPED *sequence* that
        declare a ``consumes`` edge on this producer — computed from the threaded ``sequence``,
        never a module-global ``_SEQUENCE`` (the single-seam defect the dedup removes).
        """
        if self._handoff_resolver is None or step.produces is None:
            return run
        payload = self._payload_from_result(step, worker_result)
        consumers = tuple(s.label for s in sequence if step.label in s.consumes)
        retention = (
            RetentionMode.PROMOTE_TO_EVIDENCE
            if step.is_review
            else RetentionMode.DELETE_AFTER_CONSUMED
        )
        run, _ = self._handoff_resolver.produce(
            run,
            producer_step=step.label,
            attempt=next_attempt_for(run.workflow_steps, step.label),
            output_schema=step.produces,
            payload=payload,
            declared_consumers=consumers,
            retention_mode=retention,
        )
        return run

    @staticmethod
    def _payload_from_result(step: StepT, worker_result: AgentRunResult) -> dict[str, object]:
        return durable_payload_from_result(
            worker_result, fallback_summary=step.label, is_review=step.is_review
        )

    # -- terminal Python gate (no model) --------------------------------

    def _run_terminal_gate(
        self, run: LifecycleRun, step: StepT, sequence: tuple[StepT, ...]
    ) -> tuple[LifecycleRun, _StepOutcome]:
        """Finish the run iff no prior gate blocked it and the handoff graph is whole.

        This step runs no model. The sequence only reaches it when every prior step passed;
        defensively, if the run is already blocked the gate refuses to finish. On success the
        run advances to ``_TERMINAL_PHASE`` (``release_definition``) or COMPLETEs in place with
        no phase transition (audit).
        """
        if run.blocked is not None:
            return run, _StepOutcome(
                label=step.label, accepted=False, is_gate=True, blocked=run.blocked
            )
        run, graph_block = self._graph_completeness_check(run, step, sequence)
        if graph_block is not None:
            blocked_run = self._with_step_outcome(run, step.label, graph_block)
            return blocked_run, _StepOutcome(
                label=step.label, accepted=False, is_gate=True, blocked=graph_block
            )
        semantic_block = self._terminal_semantic_block(run, step, sequence)
        if semantic_block is not None:
            blocked_run = self._with_step_outcome(run, step.label, semantic_block)
            return blocked_run, _StepOutcome(
                label=step.label,
                accepted=False,
                is_gate=True,
                blocked=semantic_block,
            )
        if self._TERMINAL_PHASE is not None:
            completed = replace(
                run,
                phase=self._TERMINAL_PHASE,
                status=LifecycleRunStatus.COMPLETED,
                current_step=step.label,
                blocked=None,
            )
        else:
            completed = replace(
                run,
                status=LifecycleRunStatus.COMPLETED,
                current_step=step.label,
                blocked=None,
            )
        return completed, _StepOutcome(label=step.label, accepted=True, is_gate=True)

    def _graph_completeness_check(
        self, run: LifecycleRun, step: StepT, sequence: tuple[StepT, ...]
    ) -> tuple[LifecycleRun, BlockedState | None]:
        """Validate the workflow-step handoff graph; reconcile lost records from disk.

        For every model step in the RUN-SCOPED *sequence*: a ``produces`` step must have a
        ledger record; for every ``consumes`` edge the consumer must have recorded a
        consumption of that producer. A record missing from the in-memory ledger is first
        RECONCILED from its persisted immutable payload (bug
        release-commit-gate-ignores-existing-plan-review-payload — an interrupted worker
        between resets/resumes can drop the record while the disk truth survives); only
        when the disk has no valid payload either does the gate block. No-op when no
        resolver is wired. Iterates the threaded ``sequence`` — never a module-global
        ``_SEQUENCE``.
        """
        if self._handoff_resolver is None:
            return run, None
        resolver = self._handoff_resolver
        recovered: set[str] = set()

        def _find_or_recover(label: str) -> LifecycleRun | None:
            nonlocal run
            # LATEST attempt, never a literal 0 (bug
            # r25-resume-still-overwrites-attempt-zero-on-the-cli-path). Now that a resume
            # KEEPS the earlier attempts instead of deleting them, attempt 0 is the
            # interrupted one; asking for it would judge the graph on evidence the run has
            # already superseded. Reconciliation from disk still starts at 0, which is the
            # only attempt that can exist when the in-memory ledger lost its record.
            if run.workflow_steps.latest_attempt(label) is not None:
                return run
            restored = resolver.recover_persisted_record(run, producer_step=label, attempt=0)
            if restored is None:
                return None
            run, _record = restored
            recovered.add(label)
            return run

        for s in sequence:
            if s.fragment_id is None:
                continue
            if s.produces is not None and _find_or_recover(s.label) is None:
                return run, BlockedState(
                    # The missing PRODUCER is what has to run again. Resuming the gate
                    # that DETECTED the hole simply re-detects it, so the printed remedy
                    # reproduced the block it came from — the r16 class on a new route,
                    # found by driving this path end to end for the first time.
                    operator_command=_graph_recovery(run, s.label),
                    reason=f"workflow-step graph incomplete: step {s.label!r} declared "
                    f"produces={s.produces!r} but wrote no ledger payload (and no "
                    "persisted payload could be reconciled from disk)",
                    blocked_at_step=step.label,
                    detail={"missing_producer": s.label},
                )
            for producer in s.consumes:
                if _find_or_recover(producer) is None:
                    return run, BlockedState(
                        operator_command=_graph_recovery(run, producer),
                        reason=f"workflow-step graph incomplete: {s.label!r} consumes "
                        f"{producer!r} which has no ledger payload (and no persisted "
                        "payload could be reconciled from disk)",
                        blocked_at_step=step.label,
                        detail={"consumer": s.label, "missing_producer": producer},
                    )
                record = run.workflow_steps.latest_attempt(producer)
                assert record is not None
                acked = any(c.consumer_step == s.label for c in record.consumptions)
                if not acked and producer not in recovered:
                    return run, BlockedState(
                        operator_command=_graph_recovery(run, step.label),
                        reason=f"workflow-step graph incomplete: {s.label!r} never recorded "
                        f"consumption of {producer!r}",
                        blocked_at_step=step.label,
                        detail={"consumer": s.label, "unconsumed_producer": producer},
                    )
        return run, None


__all__ = [
    "AssemblyStep",
    "FragmentGateStep",
    "FragmentGateWorkflow",
    "_FragmentAssemblyMixin",
    "_StepOutcome",
]
