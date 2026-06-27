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
from dataclasses import dataclass

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
from dadaia_workspace.features.lifecycle.prompt_builder import (
    FragmentBundle,
    LifecyclePromptBuilder,
    PromptPrefix,
    PromptScope,
    build_fragment_suffix,
)
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
        context_selector: ContextSelector | None = None,
        policy_snapshot: WorkflowPolicySnapshot | None = None,
        handoff_resolver: WorkflowHandoffResolver | None = None,
        max_review_retries: int = 2,
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
        self._context_selector = context_selector

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
            built = self._prompt_builder.build(
                self._scope(step, run_id),
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
            accepted = run.blocked is None
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
            # implement#attempt — from attempt 1 it consumes the prior review rejection.
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
                _ = resolved  # digest would be injected into the implement prompt here.
            impl_result = self._run_loop_worker(run, implement_step, attempt)
            run, _ = resolver.produce(
                run,
                producer_step=implement_step.label,
                attempt=attempt,
                output_schema="implementation-handoff-v1",
                payload={"summary": impl_result.summary or "implementation"},
                declared_consumers=(review_step.label,),
            )

            # review#attempt — consumes implement#attempt, produces its verdict.
            run = resolver.record_consumption(
                run,
                producer_step=implement_step.label,
                producer_attempt=attempt,
                consumer_step=review_step.label,
                consumer_attempt=attempt,
            )
            review_result = self._run_loop_worker(run, review_step, attempt)
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
                from dataclasses import replace

                run = replace(run, status=LifecycleRunStatus.COMPLETED)
                self._run_store.save(run)
                return ImplementReviewLoopResult(
                    run_id=run_id, completed=True, attempts=attempt + 1, rounds=tuple(rounds)
                )

        # Exhausted the retry budget — BLOCK for operator intervention.
        from dataclasses import replace

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

    def _run_loop_worker(
        self, run: LifecycleRun, step: PipelineStep, attempt: int
    ) -> AgentRunResult:
        """Run one implement/review worker for *attempt* and return its raw result."""
        runtime = self._runtime_factory(step.runtime_kind)
        built = self._prompt_builder.build(
            self._scope(step, f"{run.run_id}#a{attempt}"),
            runtime=runtime.runtime_kind(),
            prefix=self._prefix,
        )
        return runtime.run(built.request)

    def _scope(self, step: PipelineStep, run_id: str) -> PromptScope:
        prompt = (
            self._fragment_prompt(step)
            if step.fragment_id is not None
            else self._generic_prompt(step)
        )
        return PromptScope(
            role=step.role,
            context=self._context,
            release_id=self._release_id,
            task_id=f"{run_id}:{step.label}",
            prompt=prompt,
            allowed_paths=(f".dadaia/handoff/{self._context}/**",),
            required_evidence=(GateEvidenceKind.HANDOFF,),
            model_profile=step.model_profile,
            resolved_model=step.resolved_model,
        )

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
            fragment_id="implementation.qa_review",
        ),
        PipelineStep(
            label="review_security",
            role="security-reviewer",
            from_phase=LifecyclePhase.SECURITY_REVIEW,
            target_phase=LifecyclePhase.CODE_REVIEW,
            runtime_kind=default_kind,
            model_profile=effort,
            is_review=True,
        ),
        PipelineStep(
            label="review_code",
            role="code-reviewer",
            from_phase=LifecyclePhase.CODE_REVIEW,
            target_phase=LifecyclePhase.CLOSURE,
            runtime_kind=default_kind,
            model_profile=effort,
            is_review=True,
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


def apply_resolved_policy(
    steps: tuple[PipelineStep, ...],
    snapshot: WorkflowPolicySnapshot,
) -> tuple[PipelineStep, ...]:
    """Overlay a resolved policy snapshot onto pipeline steps — the single author of
    ``runtime_kind`` (T-29-A-06 / D-2).

    Matches each step to its snapshot entry by label and threads the resolved concrete
    model into the step's ``resolved_model`` (and ``model_profile`` for observability), then
    sets ``runtime_kind`` from the snapshot's **resolved harness** so the adapter that runs
    and the snapshot that is recorded always agree — there is no separate post-resolve
    ``runtime_kind`` swap. A step with no matching snapshot entry is returned unchanged.

    **Fake dry-run is preserved (architect MEDIUM).** ``fake`` is never a *resolved*
    harness; when the caller built the step on :data:`AgentRuntimeKind.FAKE` (a dry-run or
    a test against ``FakeAgentRuntime``), the step keeps ``FAKE`` while the governed model
    is still threaded for auditability. Only a real (non-fake) base step adopts the
    resolved harness's kind.

    Raises:
        ValueError: if a snapshot entry names a harness with no known runtime kind (a
            corrupt/forbidden Layer-2 harness leaked past resolution).
    """
    from dataclasses import replace

    out: list[PipelineStep] = []
    for step in steps:
        entry = snapshot.step(step.label)
        if entry is None:
            out.append(step)
            continue
        resolved = ResolvedModelConfig(
            profile_id=entry.model_profile,
            harness=entry.harness,
            model=entry.model,
            reasoning=entry.reasoning,
            source=entry.source,
        )
        if step.runtime_kind is AgentRuntimeKind.FAKE:
            runtime_kind = AgentRuntimeKind.FAKE
        else:
            mapped = _HARNESS_TO_KIND.get(entry.harness)
            if mapped is None:
                raise ValueError(
                    f"step {step.label!r}: resolved harness {entry.harness!r} has no "
                    f"runtime kind; Layer-2 workers are codex or pi only"
                )
            runtime_kind = mapped
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
    "RuntimeFactory",
    "apply_resolved_policy",
    "implementation_ladder",
]
