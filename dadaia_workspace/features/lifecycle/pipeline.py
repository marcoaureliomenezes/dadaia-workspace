"""Multi-step lifecycle pipeline — one run threaded through several phases, each on a
per-step-selectable harness.

This is the multi-harness vision in one object: a single ``LifecycleRun`` advances through
an ordered sequence of bounded worker steps (e.g. implement → qa → security → code), and
each step runs on whatever harness that step selects (claude to implement, codex to review,
...). The state machine stays provider-agnostic; mixing harnesses is purely a per-step
adapter swap via the injected runtime factory. The pipeline stops at the first blocked gate
and persists progress at every step (resumable).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import Field, dataclass, replace
from pathlib import Path
from typing import Any, ClassVar, Protocol

from dadaia_workspace.core.harness_models import (
    CODEX_HARNESS,
    HarnessModelOption,
    options_for,
)
from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRuntimeKind,
    BlockedState,
    GateEvidenceKind,
    GateRequirement,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_execution import (
    ResolvedModelConfig,
    WorkflowPolicySnapshot,
    WorkflowPolicyStepEntry,
)
from dadaia_workspace.core.models.workflow_handoff import RetentionMode
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStore
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    MaxContextPolicy,
    SelectionAudit,
)
from dadaia_workspace.features.lifecycle.fragments.loader import (
    Fragment,
    FragmentLoader,
)
from dadaia_workspace.features.lifecycle.personas.loader import (
    PersonaLoader,
    resolve_persona_for_role,
)
from dadaia_workspace.features.lifecycle.prompt_builder import (
    FragmentBundle,
    LifecyclePromptBuilder,
    PromptPrefix,
    PromptScope,
    build_fragment_suffix,
)
from dadaia_workspace.features.lifecycle.role_atoms import inject_role_atoms
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver

#: ``kind -> adapter`` — injected so tests can supply fakes per harness.
RuntimeFactory = Callable[[AgentRuntimeKind], AgentRuntimePort]


@dataclass(frozen=True)
class PipelineStep:
    """One bounded step in a lifecycle pipeline, bound to a chosen harness.

    A step may carry a ``fragment_id`` (``workflow.step``) plus the shared fragment ids it
    cites. When present, the step's prompt suffix is assembled from that fragment bundle —
    the fragment's own body, the cited shared bodies, the dynamically selected context
    (bounded by the fragment's ``max_context_policy``), and the fragment's output schema —
    instead of the generic ``"Run the {label} step"`` placeholder (WS-6). A step with no
    ``fragment_id`` keeps the generic suffix (the remaining pipeline steps are not migrated
    in this release).
    """

    label: str
    role: str
    from_phase: LifecyclePhase
    target_phase: LifecyclePhase
    runtime_kind: AgentRuntimeKind
    requirements: tuple[GateRequirement, ...] = ()
    model_profile: str | None = None
    fragment_id: str | None = None
    shared_fragment_ids: tuple[str, ...] = ()
    # Whether this is a REVIEW step (v0.1.31 / C1 / L4). The ``review_qa`` /
    # ``review_security`` / ``review_code`` steps gate a release toward the push boundary
    # and MUST keep their ``verdict == APPROVED`` requirement; ``implement`` is a create
    # step (``is_review=False``). Threaded into ``AgentRunnerInput`` so the runner applies
    # the verdict gate to review steps only. Without this field the push-boundary review
    # gates would silently default to create-step semantics and lose the verdict check.
    is_review: bool = False
    # The governance-resolved concrete model for this step (T-28-A-07). Threaded into the
    # step's scope/request so the adapter runs the policy-selected model. Additive-optional.
    resolved_model: ResolvedModelConfig | None = None
    # FR7 (T-66-08): additive-optional extra write-scope path globs, threaded from the CLI's
    # ``--write-scope`` option. ``_scope`` unions these into ``allowed_paths`` for NON-REVIEW
    # steps only (gated on ``is_review is False`` — never a ``label == "implement"`` string
    # match, which would silently stop covering any future non-review step and could be
    # bypassed by a differently-labeled review step; ARCHITECT FINDING MEDIUM-2). Review steps
    # (``is_review=True``) ALWAYS ignore this field and stay handoff-only — they must never
    # gain production write rights. Default ``()`` preserves today's handoff-only behavior for
    # every existing caller that does not set it.
    extra_allowed_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class PipelineStepResult:
    label: str
    runtime_kind: AgentRuntimeKind
    accepted: bool
    phase: LifecyclePhase
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[PipelineStepResult, ...] = ()
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class ImplementReviewRound:
    """One implement→review round of the bounded retry loop (T-30-D-06)."""

    attempt: int
    review_verdict: str


@dataclass(frozen=True)
class ImplementReviewLoopResult:
    """Typed outcome of the implement/review attempt loop (A24)."""

    run_id: str
    completed: bool
    attempts: int
    rounds: tuple[ImplementReviewRound, ...] = ()
    blocked: BlockedState | None = None


class LifecyclePipeline:
    """Thread one run through an ordered, per-step-harness-selectable phase sequence."""

    def __init__(
        self,
        *,
        context: str,
        release_id: str,
        run_store: LifecycleRunStore,
        runtime_factory: RuntimeFactory,
        prefix: PromptPrefix | None = None,
        prompt_builder: LifecyclePromptBuilder | None = None,
        state_machine: LifecycleStateMachine | None = None,
        fragment_loader: FragmentLoader | None = None,
        persona_loader: PersonaLoader | None = None,
        context_selector: ContextSelector | None = None,
        policy_snapshot: WorkflowPolicySnapshot | None = None,
        handoff_resolver: WorkflowHandoffResolver | None = None,
        max_review_retries: int = 2,
        specs_dir: Path | None = None,
    ) -> None:
        self._context = context
        self._release_id = release_id
        self._run_store = run_store
        self._runtime_factory = runtime_factory
        self._prefix = prefix
        self._prompt_builder = prompt_builder or LifecyclePromptBuilder()
        self._state_machine = state_machine or LifecycleStateMachine()
        # Workflow-step handoff resolver (v0.1.30 Item 5 / T-30-D-06). Drives the
        # implement/review attempt ledger so ``implement#2`` consumes the EXACT ``qa#1``
        # rejection by (run, producer step, attempt) — never qa#0 / latest-by-filename.
        self._handoff_resolver = handoff_resolver
        # Bounded automatic retry for the implement/review loop (GRILL: default 2). When the
        # review keeps REJECTING past this many retries the loop BLOCKS for operator
        # intervention rather than looping forever.
        self._max_review_retries = max_review_retries
        # The resolved governance snapshot (T-28-A-07 / LAW 7). When present it is frozen
        # onto the run BEFORE the first step; an overlay mutated after start cannot change
        # the in-flight run because the run carries this immutable snapshot, not the live
        # overlay. ``dataclasses.replace`` in the state machine + agent runner preserves it
        # across every step transition.
        self._policy_snapshot = policy_snapshot
        # A step that declares a ``fragment_id`` is assembled from the fragment library
        # (WS-6). The loader defaults to the packaged fragment root; the context selector
        # is optional — when absent, fragment steps still emit fragment-sourced prompts
        # (the fragment body + cited shared bodies + output schema), only without the
        # dynamically resolved file context.
        self._fragment_loader = fragment_loader or FragmentLoader()
        # The persona library (v0.1.44 / AC-2). A step's ``role`` is resolved to its
        # Layer-2 persona mandate here and threaded into the scope so the worker envelope
        # carries an operative directive to act per that mandate. ``role: shared`` and any
        # role with no persona atom resolve to ``None`` (no persona block).
        self._persona_loader = persona_loader or PersonaLoader()
        self._context_selector = context_selector
        # The active context's ``specs/`` tree (v0.1.57 FR2 / A1). Wired by
        # ``build_lifecycle_pipeline`` from ``workspace_root + context`` so the declarative
        # role→atom map resolves atoms via a light direct read — independent of the (absent)
        # context selector, whose ``implementation.*`` fragment inputs are unregistered. When
        # ``None`` (a fixture-constructed pipeline) no role atom is injected: the map is inert
        # only when the surface is deliberately un-wired, never in the real pipeline path.
        self._specs_dir = specs_dir

    def _inject_role_atoms(
        self, run: LifecycleRun, step: PipelineStep, scope: PromptScope
    ) -> tuple[LifecycleRun, PromptScope]:
        """Append the step role's mapped memory atom(s) to *scope*'s prompt + record their refs.

        Delegates to the single :func:`inject_role_atoms` helper (never a copy of the map/read
        logic). Returns the (possibly unchanged) run + a scope whose prompt carries the atom
        block(s); a fixture pipeline with no ``specs_dir`` is byte-identical (no injection).
        """
        run, prompt = inject_role_atoms(
            run=run,
            step_label=step.label,
            role=step.role,
            specs_dir=self._specs_dir,
            prompt=scope.prompt,
        )
        return run, replace(scope, prompt=prompt)

    def run(self, run_id: str, steps: tuple[PipelineStep, ...]) -> PipelineResult:
        if not steps:
            raise ValueError("pipeline requires at least one step")
        run = LifecycleRun(
            run_id=run_id,
            context=self._context,
            release_id=self._release_id,
            command="pipeline",
            phase=steps[0].from_phase,
            status=LifecycleRunStatus.RUNNING,
            current_step=steps[0].label,
            idempotency_key=run_id,
            workflow_policy=self._policy_snapshot,
        )
        self._run_store.save(run)

        results: list[PipelineStepResult] = []
        for step in steps:
            runtime = self._runtime_factory(step.runtime_kind)
            # FR2 (A1): resolve the step role's mapped atom(s), append them to the prompt, and
            # record the atom refs on the run BEFORE the worker call — the state machine's
            # ``replace``-based transition preserves ``injected_context`` onto ``decision.run``.
            run, scope = self._inject_role_atoms(run, step, self._scope(step, run_id))
            built = self._prompt_builder.build(
                scope,
                runtime=runtime.runtime_kind(),
                prefix=self._prefix,
            )
            runner = LifecycleAgentRunner(runtime=runtime, state_machine=self._state_machine)
            decision = runner.run(
                run,
                AgentRunnerInput(
                    request=built.request,
                    target_phase=step.target_phase,
                    requirements=step.requirements,
                    current_step=step.label,
                    is_review=step.is_review,
                ),
            )
            run = decision.run
            self._run_store.save(run)
            # FR5 (A5): the accept signal is the state machine's dual-signal contract, NOT
            # ``run.blocked is None`` — the latter read ``True`` on an illegal transition
            # (run unchanged, no blocked state) and wrongly advanced the ladder.
            accepted = decision.advanced
            results.append(
                PipelineStepResult(
                    label=step.label,
                    runtime_kind=step.runtime_kind,
                    accepted=accepted,
                    phase=run.phase,
                    blocked=run.blocked,
                )
            )
            if not accepted:
                return PipelineResult(
                    run_id=run_id,
                    completed=False,
                    final_phase=run.phase,
                    steps=tuple(results),
                    blocked=run.blocked,
                )
        return PipelineResult(
            run_id=run_id,
            completed=True,
            final_phase=run.phase,
            steps=tuple(results),
        )

    # -- implement/review attempt loop (T-30-D-06 / A24) ---------------------

    def run_implement_review_loop(
        self,
        run_id: str,
        *,
        implement_step: PipelineStep,
        review_step: PipelineStep,
    ) -> ImplementReviewLoopResult:
        """Run implement → review with run-scoped attempt tracking + bounded retry (A24).

        Each round writes immutable per-attempt payloads through the handoff resolver:
        ``implement#N`` then ``review#N``. On a REJECTED review the next implement attempt
        consumes the EXACT ``review#N`` rejection by (run, producer step, attempt) — never
        ``review#0`` / latest-by-filename. After ``max_review_retries`` rejected rounds the
        loop BLOCKS for operator intervention rather than retrying forever.

        Requires a wired ``handoff_resolver`` — the loop's whole point is the attempt
        ledger. The two steps run on their declared harnesses via the runtime factory.
        """
        if self._handoff_resolver is None:
            raise ValueError("run_implement_review_loop requires a wired handoff_resolver")
        resolver = self._handoff_resolver

        run = LifecycleRun(
            run_id=run_id,
            context=self._context,
            release_id=self._release_id,
            command="implement_review_loop",
            phase=implement_step.from_phase,
            status=LifecycleRunStatus.RUNNING,
            current_step=implement_step.label,
            idempotency_key=run_id,
            workflow_policy=self._policy_snapshot,
        )
        self._run_store.save(run)

        rounds: list[ImplementReviewRound] = []
        # attempt 0 is the first try; up to max_review_retries additional attempts follow.
        for attempt in range(self._max_review_retries + 1):
            # implement#attempt — from attempt 1 it consumes the prior review rejection, whose
            # COMPACT digest is injected into the implement prompt (FR3 — the l.309 drop is
            # replaced). The digest reaches the built request the implement worker receives.
            digest: str | None = None
            if attempt > 0:
                resolved = resolver.resolve_required(
                    run, producer_step=review_step.label, attempt=attempt - 1
                )
                run = resolver.record_consumption(
                    run,
                    producer_step=review_step.label,
                    producer_attempt=attempt - 1,
                    consumer_step=implement_step.label,
                    consumer_attempt=attempt,
                )
                digest = WorkflowHandoffResolver.render_digest(resolved)
            impl_result, impl_blocked = self._run_loop_worker(
                run, implement_step, attempt, digest=digest
            )
            # Structural runner gate (evidence only, is_review=False): a non-SUCCEEDED /
            # evidence-less / out-of-scope implement worker BLOCKS the loop — it is a broken
            # worker, never a rejected review to retry.
            if impl_blocked is not None:
                return self._finalize_structural_block(run, impl_blocked, rounds, attempt)
            run, _ = resolver.produce(
                run,
                producer_step=implement_step.label,
                attempt=attempt,
                output_schema="implementation-handoff-v1",
                payload={"summary": impl_result.summary or "implementation"},
                declared_consumers=(review_step.label,),
            )

            # review#attempt — consumes implement#attempt, produces its verdict. The review
            # worker is gated on EVIDENCE ONLY (is_review=False): a REJECTED verdict must NOT
            # block the loop (is_review=True would block the first REJECTED and destroy the
            # retry model — agent_runner l.196). The verdict is read from the returned result
            # to drive the attempt ledger; only a STRUCTURAL failure blocks here.
            run = resolver.record_consumption(
                run,
                producer_step=implement_step.label,
                producer_attempt=attempt,
                consumer_step=review_step.label,
                consumer_attempt=attempt,
            )
            review_result, review_blocked = self._run_loop_worker(run, review_step, attempt)
            if review_blocked is not None:
                return self._finalize_structural_block(run, review_blocked, rounds, attempt)
            verdict = review_result.structured_output.get("verdict")
            run, _ = resolver.produce(
                run,
                producer_step=review_step.label,
                attempt=attempt,
                output_schema="qa-review-handoff-v1",
                payload={
                    "verdict": verdict if isinstance(verdict, str) else "REJECTED",
                    "verdict_reason": review_result.summary or "review",
                },
                declared_consumers=(implement_step.label,),
                retention_mode=RetentionMode.PROMOTE_TO_EVIDENCE,
            )
            rounds.append(ImplementReviewRound(attempt=attempt, review_verdict=str(verdict)))
            if verdict == "APPROVED":
                run = replace(run, status=LifecycleRunStatus.COMPLETED)
                self._run_store.save(run)
                return ImplementReviewLoopResult(
                    run_id=run_id, completed=True, attempts=attempt + 1, rounds=tuple(rounds)
                )

        # Exhausted the retry budget on well-formed REJECTED rounds — BLOCK for operator
        # intervention. This is retry EXHAUSTION, distinct from a structural evidence block.
        blocked = BlockedState(
            reason=(
                f"implement/review loop exceeded the bounded retry count "
                f"({self._max_review_retries}); operator intervention required"
            ),
            blocked_at_step=review_step.label,
            detail={"attempts": str(self._max_review_retries + 1)},
        )
        run = replace(
            run, phase=LifecyclePhase.BLOCKED, status=LifecycleRunStatus.BLOCKED, blocked=blocked
        )
        self._run_store.save(run)
        return ImplementReviewLoopResult(
            run_id=run_id,
            completed=False,
            attempts=self._max_review_retries + 1,
            rounds=tuple(rounds),
            blocked=blocked,
        )

    def _finalize_structural_block(
        self,
        run: LifecycleRun,
        blocked: BlockedState,
        rounds: list[ImplementReviewRound],
        attempt: int,
    ) -> ImplementReviewLoopResult:
        """Persist a structural (evidence) BLOCK on either loop worker and return the result.

        A structural block — non-SUCCEEDED, empty ``artifact_refs``, or out-of-scope paths
        (the runner's evidence-only decision, ``is_review=False``) — stops the loop
        immediately: a broken worker is not a rejected review to retry. ``attempts`` counts
        the current 1-based attempt, since the block occurred during it.
        """
        run = replace(
            run,
            phase=LifecyclePhase.BLOCKED,
            status=LifecycleRunStatus.BLOCKED,
            blocked=blocked,
        )
        self._run_store.save(run)
        return ImplementReviewLoopResult(
            run_id=run.run_id,
            completed=False,
            attempts=attempt + 1,
            rounds=tuple(rounds),
            blocked=blocked,
        )

    def _run_loop_worker(
        self,
        run: LifecycleRun,
        step: PipelineStep,
        attempt: int,
        *,
        digest: str | None = None,
    ) -> tuple[AgentRunResult, BlockedState | None]:
        """Run one implement/review worker for *attempt* through the STRUCTURAL runner gate.

        Both workers route through :meth:`LifecycleAgentRunner.evaluate_gate_with_result`
        with ``is_review=False`` (gate WITHOUT a phase transition, as ``release_definition`` /
        ``audit`` do) — the gate decides on EVIDENCE ONLY (non-SUCCEEDED / empty
        ``artifact_refs`` / out-of-scope paths BLOCK), never on the review verdict. Gating the
        review ``is_review=True`` would return a block on the first REJECTED verdict
        (``agent_runner`` l.196) and destroy the retry-with-digest model; the caller reads the
        APPROVED/REJECTED verdict from the returned result to drive the attempt ledger
        instead. When *digest* is present (the ``implement#N``, N ≥ 1 case) it trails the scope
        prompt so the built request the worker receives carries the ``review#N-1`` rejection.
        """
        runtime = self._runtime_factory(step.runtime_kind)
        built = self._prompt_builder.build(
            self._scope(step, f"{run.run_id}#a{attempt}", digest_suffix=digest),
            runtime=runtime.runtime_kind(),
            prefix=self._prefix,
        )
        runner = LifecycleAgentRunner(runtime=runtime, state_machine=self._state_machine)
        return runner.evaluate_gate_with_result(
            run,
            AgentRunnerInput(
                request=built.request,
                target_phase=step.target_phase,
                requirements=step.requirements,
                current_step=step.label,
                is_review=False,
            ),
        )

    def _scope(
        self, step: PipelineStep, run_id: str, *, digest_suffix: str | None = None
    ) -> PromptScope:
        prompt = (
            self._fragment_prompt(step)
            if step.fragment_id is not None
            else self._generic_prompt(step)
        )
        if digest_suffix:
            # The prior review rejection digest (FR3) trails the step prompt so it reaches the
            # built request verbatim; the multi-step ``run`` path passes no digest (default).
            prompt = f"{prompt}\n\n{digest_suffix}"
        handoff_glob = f".dadaia/handoff/{self._context}/**"
        # FR7 (T-66-08): the handoff-dir glob is unioned with the step's
        # extra_allowed_paths for NON-REVIEW steps only. Gated on step.is_review is False
        # (ARCHITECT MEDIUM-2) — never a label string match — so review steps
        # (review_qa/review_security/review_code, is_review=True) ALWAYS stay
        # handoff-only regardless of what extra_allowed_paths carries.
        allowed_paths = (
            (handoff_glob, *step.extra_allowed_paths) if not step.is_review else (handoff_glob,)
        )
        return PromptScope(
            role=step.role,
            context=self._context,
            release_id=self._release_id,
            task_id=f"{run_id}:{step.label}",
            prompt=prompt,
            allowed_paths=allowed_paths,
            required_evidence=(GateEvidenceKind.HANDOFF,),
            model_profile=step.model_profile,
            resolved_model=step.resolved_model,
            persona=self._resolve_persona(step.role),
        )

    def _resolve_persona(self, role: str) -> str | None:
        """Resolve a step's ``role`` to its Layer-2 persona mandate(s) (AC-2).

        Delegates to the shared :func:`resolve_persona_for_role` helper (W1-3, the single
        source of role→persona resolution) with this pipeline's injectable loader, so the
        pipeline and every fragment workflow body + the CLI step path resolve personas
        identically.
        """
        return resolve_persona_for_role(role, self._persona_loader)

    def _generic_prompt(self, step: PipelineStep) -> str:
        """Generic (no-fragment) step prompt — step-kind-aware (v0.1.32 / C6 / L2 / A4b).

        This is the second stale surface: it is NOT a ``build_fragment_suffix`` caller and
        previously hard-coded the universal self-verdict text for every step, re-introducing
        Drift 1 on the pipeline's generic steps. It now branches on ``step.is_review`` the
        same way the suffix builder does: review steps self-verdict; create steps emit an
        artifact and do NOT self-verdict.
        """
        lead = (
            f"Run the {step.label} step for release {self._release_id} in context {self._context}."
        )
        if step.is_review:
            tail = (
                " Because this is a REVIEW step, emit a handoff whose "
                "structured_output.verdict is APPROVED or REJECTED, with an artifact_ref "
                "pointing at the handoff document."
            )
        else:
            tail = (
                " Because this is a CREATE step, emit a handoff with the produced artifact "
                "in artifact_refs pointing at the handoff document; do NOT self-judge — the "
                "review gate owns the APPROVED/REJECTED decision."
            )
        return lead + tail

    def _fragment_prompt(self, step: PipelineStep) -> str:
        """Assemble a fragment-sourced suffix for a step that declares a ``fragment_id``.

        Uses the same fragment-suffix path as the release-definition workflow
        (:func:`build_fragment_suffix` + :class:`FragmentLoader` + the context selector,
        honoring the fragment's ``max_context_policy``). When no context selector is
        wired, the dynamic context is empty but the fragment body + cited shared bodies +
        output schema still drive the prompt — never the generic placeholder.
        """
        assert step.fragment_id is not None
        fragment = self._fragment_loader.load_fragment(step.fragment_id)
        shared = tuple(self._fragment_loader.load_fragment(fid) for fid in step.shared_fragment_ids)
        selected = self._select_context(step, fragment)
        return build_fragment_suffix(
            self._fragment_bundle(step, fragment, shared),
            selected_context=self._render_selection(selected),
            is_review=step.is_review,
        )

    def _select_context(self, step: PipelineStep, fragment: Fragment) -> SelectionAudit:
        """Resolve the fragment's dynamic inputs, bounded by its ``max_context_policy``.

        Returns an empty audit when no context selector is wired — the fragment material
        still carries the prompt; only the dynamically resolved files are omitted.
        """
        if self._context_selector is None:
            return SelectionAudit(step=step.label)
        policy = MaxContextPolicy.parse(fragment.max_context_policy)
        return self._context_selector.select_all(
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

    def _fragment_bundle(
        self,
        step: PipelineStep,
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


#: Default Layer-2 discrete model for pipeline steps when the caller does not select
#: one (LAW 2 / ADR-B). Codex's first catalog option is the standard worker profile;
#: the prior ``"sonnet"/"opus"`` tier literals were never valid Codex tier names and
#: are dropped. ``model_profile`` now carries the discrete option's effort string so
#: the seam remains observable without re-introducing a tier abstraction.
_DEFAULT_STEP_MODEL: HarnessModelOption = options_for(CODEX_HARNESS)[0]


def implementation_ladder(
    default_kind: AgentRuntimeKind,
    *,
    model: HarnessModelOption | None = None,
) -> tuple[PipelineStep, ...]:
    """The canonical release-implementation pipeline: implement → qa → security → code.

    Each step defaults to ``default_kind`` (override per step for harness mixing). The
    discrete Layer-2 model defaults from the catalog (LAW 2 / ADR-B) — no ``sonnet``/
    ``opus`` literals. Each step's ``model_profile`` records the chosen option's effort
    so the pipeline run record stays auditable; the actual ``(id, effort)`` reaches the
    adapter through the runtime factory (``build_agent_runtime(..., model=...)``).
    """
    chosen = model or _DEFAULT_STEP_MODEL
    effort = chosen.effort
    return (
        PipelineStep(
            label="implement",
            role="software-engineer",
            from_phase=LifecyclePhase.IMPLEMENTATION,
            target_phase=LifecyclePhase.QA_REVIEW,
            runtime_kind=default_kind,
            model_profile=effort,
            # WS-6: the implementation step runs on the fragment library. Its bundle is
            # the TDD implement fragment, citing the shared write-scope / anti-slop /
            # output-handoff disciplines plus the self-verify fragment.
            fragment_id="implementation.implement_tdd",
            shared_fragment_ids=(
                "shared.write_scope",
                "shared.anti_slop",
                "shared.output_handoff",
                "implementation.self_verify",
            ),
        ),
        PipelineStep(
            label="review_qa",
            role="qa-engineer",
            from_phase=LifecyclePhase.QA_REVIEW,
            target_phase=LifecyclePhase.SECURITY_REVIEW,
            runtime_kind=default_kind,
            model_profile=effort,
            is_review=True,
            # WS-6: the QA review step is the second fragment-driven pipeline step.
            # WS-2b (v0.1.43): cite the shared output-handoff verdict contract.
            fragment_id="implementation.qa_review",
            shared_fragment_ids=("shared.output_handoff",),
        ),
        PipelineStep(
            label="review_security",
            role="security-reviewer",
            from_phase=LifecyclePhase.SECURITY_REVIEW,
            target_phase=LifecyclePhase.CODE_REVIEW,
            runtime_kind=default_kind,
            model_profile=effort,
            is_review=True,
            # WS-1a: the security review step runs on the fragment library — an OWASP-style
            # rubric over the change diff. This step mechanically gates every push, so it
            # must never fall back to the generic placeholder.
            fragment_id="implementation.security_review",
            shared_fragment_ids=("shared.anti_slop", "shared.output_handoff"),
        ),
        PipelineStep(
            label="review_code",
            role="code-reviewer",
            from_phase=LifecyclePhase.CODE_REVIEW,
            target_phase=LifecyclePhase.CLOSURE,
            runtime_kind=default_kind,
            model_profile=effort,
            is_review=True,
            # WS-1b: the code review step runs on the fragment library — a correctness /
            # code-quality rubric over the change diff.
            fragment_id="implementation.code_review",
            shared_fragment_ids=("shared.anti_slop", "shared.output_handoff"),
        ),
    )


#: The resolved Layer-2 harness name → the pipeline ``AgentRuntimeKind`` that runs it
#: (v0.1.29 / T-29-A-06 — the inverse of the catalog's kind→harness map). ``fake`` is NOT
#: here: it is never a *resolved* governed harness — it is the dry-run/test sentinel that
#: :func:`apply_resolved_policy` preserves explicitly.
_HARNESS_TO_KIND: dict[str, AgentRuntimeKind] = {
    "codex": AgentRuntimeKind.CODEX_EXEC,
    "pi": AgentRuntimeKind.PI_HEADLESS,
}


class PolicyApplicableStep(Protocol):
    """Structural contract a frozen step dataclass satisfies to receive a resolved policy.

    :func:`apply_resolved_policy` maps :func:`apply_entry_to_step` over any step exposing
    these four attributes — the pipeline :class:`PipelineStep`, the ``ReleaseStep`` /
    ``BacklogStep`` definition steps, and (W2) the Wave-E ``AuditStep`` / ``ResearchStep`` /
    ``BugReportStep``. Binding a **structural** Protocol (not an enumerated type-union) is
    what lets those frozen dataclasses receive the policy with no ``pipeline.py`` edit once
    they gain the two model fields (R-2 decoupling).

    Read-only ``@property`` members keep the concrete non-optional ``runtime_kind`` on
    :class:`PipelineStep` covariant with the ``| None`` declared here; the
    ``__dataclass_fields__`` marker lets :func:`dataclasses.replace` accept a value typed as
    the bound TypeVar under ``mypy --strict`` (a plain Protocol is not a dataclass).
    """

    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]

    @property
    def label(self) -> str: ...
    @property
    def runtime_kind(self) -> AgentRuntimeKind | None: ...
    @property
    def resolved_model(self) -> ResolvedModelConfig | None: ...
    @property
    def model_profile(self) -> str | None: ...


def apply_entry_to_step(
    entry: WorkflowPolicyStepEntry,
    *,
    base_kind: AgentRuntimeKind | None,
    preserve_fake: bool,
) -> tuple[AgentRuntimeKind, ResolvedModelConfig]:
    """Author one step's ``(runtime_kind, resolved_model)`` from its snapshot entry (R-2).

    The single FAKE-preserving per-step author. It threads the snapshot entry's resolved
    concrete model into a :class:`ResolvedModelConfig` and picks the runtime kind:

    * when ``preserve_fake`` (the base step is the FAKE dry-run/test sentinel — i.e.
      ``base_kind is FAKE``) the kind stays FAKE, so ``--harness fake`` drives the fake
      adapter while the snapshot still records the governed harness for auditability;
    * otherwise the kind is the snapshot's **resolved harness** mapped through
      :data:`_HARNESS_TO_KIND` (``codex -> CODEX_EXEC``, ``pi -> PI_HEADLESS``).

    Both the per-step mapper (:func:`apply_resolved_policy`) and the single-step CLI verb
    (which has no step object to iterate) call this exactly once — it is the sole author of
    every run-a-worker verb's ``runtime_kind``.

    Raises:
        ValueError: if a non-fake entry names a harness with no known runtime kind (a
            corrupt/forbidden Layer-2 harness leaked past resolution).
    """
    resolved = ResolvedModelConfig(
        profile_id=entry.model_profile,
        harness=entry.harness,
        model=entry.model,
        reasoning=entry.reasoning,
        source=entry.source,
    )
    if preserve_fake:
        # preserve_fake ⟺ base_kind is the FAKE dry-run sentinel; keep it (never a
        # governed harness). Defensive None fallback keeps the return non-optional.
        return (base_kind if base_kind is not None else AgentRuntimeKind.FAKE), resolved
    mapped = _HARNESS_TO_KIND.get(entry.harness)
    if mapped is None:
        raise ValueError(
            f"step {entry.step!r}: resolved harness {entry.harness!r} has no "
            f"runtime kind; Layer-2 workers are codex or pi only"
        )
    return mapped, resolved


def apply_resolved_policy[StepT: PolicyApplicableStep](
    steps: tuple[StepT, ...],
    snapshot: WorkflowPolicySnapshot,
) -> tuple[StepT, ...]:
    """Map :func:`apply_entry_to_step` over every step that has a snapshot entry (D-2).

    The single author of each step's ``runtime_kind``, now generic over the structural
    :class:`PolicyApplicableStep` Protocol so the SAME applier governs the pipeline ladder,
    the release-/backlog-definition sequences, and (W2) the Wave-E bodies. A step matched by
    label adopts the snapshot's resolved concrete model into ``resolved_model`` (and
    ``model_profile`` for observability) and its ``runtime_kind`` from the resolved harness
    (FAKE preserved for a dry-run base). A step with no matching entry (e.g. a Python gate)
    is returned unchanged.

    **Fake dry-run is preserved (architect MEDIUM).** ``fake`` is never a *resolved*
    harness; a step built on :data:`AgentRuntimeKind.FAKE` keeps ``FAKE`` while the governed
    model is still threaded for auditability. Seeding each base step's ``runtime_kind`` to
    the run's default kind BEFORE calling this (mirroring the pipeline verb) is what keeps a
    ``None``-kind definition step from mapping ``None -> codex/pi`` and driving a live
    adapter on ``--harness fake`` (R-3).

    Raises:
        ValueError: if a snapshot entry names a harness with no known runtime kind.
    """
    from dataclasses import replace

    out: list[StepT] = []
    for step in steps:
        entry = snapshot.step(step.label)
        if entry is None:
            out.append(step)
            continue
        runtime_kind, resolved = apply_entry_to_step(
            entry,
            base_kind=step.runtime_kind,
            preserve_fake=step.runtime_kind is AgentRuntimeKind.FAKE,
        )
        out.append(
            replace(
                step,
                runtime_kind=runtime_kind,
                resolved_model=resolved,
                model_profile=entry.model_profile,
            )
        )
    return tuple(out)


# Re-exported for callers assembling custom ladders.
__all__ = [
    "ImplementReviewLoopResult",
    "ImplementReviewRound",
    "LifecyclePipeline",
    "PipelineResult",
    "PipelineStep",
    "PipelineStepResult",
    "PolicyApplicableStep",
    "RuntimeFactory",
    "apply_entry_to_step",
    "apply_resolved_policy",
    "implementation_ladder",
]
