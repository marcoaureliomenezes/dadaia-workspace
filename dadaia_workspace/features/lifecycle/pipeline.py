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

import contextlib
import os
import re
import uuid
from collections.abc import Callable
from dataclasses import Field, dataclass, replace
from pathlib import Path
from typing import Any, ClassVar, Protocol

from dadaia_workspace.core.exceptions import TasksMarkerStateError
from dadaia_workspace.core.harness_models import (
    CODEX_HARNESS,
    HarnessModelOption,
    options_for,
)
from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRunStatus,
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
from dadaia_workspace.core.models.workflow_handoff import WorkflowStepLedger
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStore
from dadaia_workspace.core.protocols.runtime_files import RuntimeFilePort
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    MaxContextPolicy,
    SelectionAudit,
    SelectionResult,
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
    canonical_worker_output_ref,
    filter_context_spec_paths,
    worker_output_glob,
)
from dadaia_workspace.features.lifecycle.role_atoms import inject_role_atoms
from dadaia_workspace.features.lifecycle.run_store import refuse_completed_rerun
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine, TransitionInput
from dadaia_workspace.features.lifecycle.workflow_handoffs import (
    WorkflowHandoffResolver,
    durable_payload_from_result,
)

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
    target_phase: LifecyclePhase | None
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
    attempt: int = 0


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[PipelineStepResult, ...] = ()
    blocked: BlockedState | None = None


#: v0.1.78 T-B / FR-B — the named payload schema each REVIEW step's handoff-ledger payload
#: is produced under (see ``workflow_handoffs._PAYLOAD_VALIDATORS``). ``review_qa`` reuses
#: the pre-existing ``qa-review-handoff-v1``; ``review_security``/``review_code`` get their
#: own verdict-shaped schemas so the ledger's ``output_schema`` stays honest about which
#: gate produced it. An unmapped review label falls back to ``qa-review-handoff-v1`` (a
#: generic verdict shape) rather than raising — the ladder's 4 canonical labels are always
#: covered; a future custom review step still produces *a* valid payload.
_REVIEW_OUTPUT_SCHEMA_BY_LABEL: dict[str, str] = {
    "review_combined": "combined-review-handoff-v1",
    "review_qa": "qa-review-handoff-v1",
    "review_security": "security-review-handoff-v1",
    "review_code": "code-review-handoff-v1",
}

_TASK_MARKER_LINE_RES = (
    # Checklist grammar: ``- [ ] **T01 - title**`` (bold optional: ``- [ ] T1 - ...``).
    re.compile(r"^\s*-\s*\[(?P<marker>[ x-])\]\s+(?:\*\*\s*)?T-?[0-9]"),
    # H3 grammar, with the marker before or after the task id/title:
    # ``### [ ] T1 - title`` and ``### T-1 - title `[ ]```.
    re.compile(r"^\s*###\s+(?=.*\bT-?[0-9])[^\n]*?\[(?P<marker>[ x-])\]"),
    # Consumer grammar: a standalone marker associated with a bold task heading.
    re.compile(r"^\s*\[(?P<marker>[ x-])\]\s+T-?[0-9][0-9A-Za-z.\-]*\s*$"),
)


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
        runtime_files: RuntimeFilePort | None = None,
        artifact_root: Path | None = None,
        executed_test_gate: Callable[[], tuple[bool | None, str]] | None = None,
        memory_catalog_regenerator: Callable[[], None] | None = None,
        memory_lint_gate: Callable[[], tuple[bool, str]] | None = None,
        repo_hygiene_sweeper: Callable[[], None] | None = None,
        closure_committer: Callable[[], None] | None = None,
    ) -> None:
        self._context = context
        self._release_id = release_id
        self._run_store = run_store
        self._runtime_factory = runtime_factory
        # Bug implementation-review-approves-unexecuted-validation: when wired
        # (production composition), the terminal `close` step COMPLETES only on an
        # EXECUTED, GREEN test run — Python-owned evidence, never a worker self-report.
        # The gate yields (ok, evidence): ok=False blocks close; ok=None means the
        # release declares no test paths (unaffected). ``None`` (fixtures) keeps
        # behavior byte-identical.
        self._executed_test_gate = executed_test_gate
        # Bug closure-catalog-references-missing-memory-atom: the memory catalog is
        # DERIVED from the atoms on disk. After a successful close, Python regenerates
        # catalog.json + index.md so a hand-edited phantom entry cannot survive the
        # cycle and doctor CAT-1 stays impossible post-closure. Best-effort: a
        # regeneration failure never un-closes the release.
        self._memory_catalog_regenerator = memory_catalog_regenerator
        # Bug closure-allows-memory-doctor-warnings: when wired, the close step refuses
        # to complete while the context's memory atoms carry lint findings — closure
        # leaves memory lint-clean or blocks with the findings digest.
        self._memory_lint_gate = memory_lint_gate
        # Bug lifecycle-workflows-leave-python-bytecode-in-repo: when wired, a
        # completed cycle deterministically sweeps cache dirs (__pycache__,
        # .pytest_cache, ...) out of the context repo. Best-effort, never un-closes.
        self._repo_hygiene_sweeper = repo_hygiene_sweeper
        # Bug implementation-closure-leaves-uncommitted-release-tree: a completed cycle
        # commits the context repo's release/implementation/memory changes — closure is
        # a durable state, not a dirty working tree. Best-effort, never un-closes.
        self._closure_committer = closure_committer
        # One-shot prior-block digest injected into the first resumed step's prompt.
        self._resume_digest: str | None = None
        self._prefix = prefix
        self._prompt_builder = prompt_builder or LifecyclePromptBuilder()
        self._state_machine = state_machine or LifecycleStateMachine()
        # v0.1.78 T-D / FR-D: additive-optional run-artifact writer, threaded to every
        # ``LifecycleAgentRunner`` this pipeline constructs — a noncompliant worker attempt
        # persists its diagnostic under the run's step-artifact zone. ``None`` (the default,
        # every pre-existing fixture pipeline) keeps behavior byte-identical.
        self._runtime_files = runtime_files
        # Bug gate-accepts-phantom-artifact-evidence: when wired (production builders pass
        # the workspace root), declared artifact refs must EXIST or the step BLOCKs.
        self._artifact_root = artifact_root
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

    def run(
        self,
        run_id: str,
        steps: tuple[PipelineStep, ...],
        *,
        resume_from: str | None = None,
    ) -> PipelineResult:
        if not steps:
            raise ValueError("pipeline requires at least one step")
        # Idempotency guard (bug completed-workflow-rerun-not-refused): a COMPLETED run
        # id is immutable history — refuse cleanly before any marker rewrite or zone
        # reclaim; blocked/failed run ids remain restartable.
        refuse_completed_rerun(self._run_store, run_id)
        # Python owns task-marker state because the implementation worker's write scope
        # deliberately excludes TASKS.md. Reservations survive retries and blocked runs;
        # completion happens only after the entire review + close ladder succeeds.
        self._rewrite_task_markers(" ", "-")
        self._require_task_markers(("-", "x"), boundary="implementation start")
        if resume_from is not None:
            # Bug implementation-reviews-resume-token-without-cli-resume: the ledger
            # advertised a resume token with no command honoring it. A blocked run now
            # resumes from the named step — upstream ledger records are KEPT (their
            # payloads stay addressable), only the resumed-step-onward zone is reclaimed.
            labels = tuple(step.label for step in steps)
            if resume_from not in labels:
                raise ValueError(
                    f"resume_from step {resume_from!r} is not in the pipeline sequence {labels}"
                )
            prior = self._run_store.load(run_id)
            if prior is not None and prior.blocked is not None:
                # Parity with the fragment-gate engines: the resumed step's prompt
                # carries the prior rejection/block digest — a blind re-run repeats
                # the identical findings forever.
                blocked_prior = prior.blocked
                resume_digest_lines = [
                    "## Prior rejection feedback (resumed run)",
                    f"The previous run blocked at step {blocked_prior.blocked_at_step!r}: "
                    f"{blocked_prior.reason}",
                ]
                for key, value in sorted(blocked_prior.detail.items()):
                    resume_digest_lines.append(f"- {key}: {value}")
                resume_digest_lines.append(
                    "Revise the deliverable so every point above is addressed."
                )
                self._resume_digest = "\n".join(resume_digest_lines)
            if prior is None:
                raise ValueError(
                    f"cannot resume run {run_id!r} from {resume_from!r}: no persisted run"
                )
            index = labels.index(resume_from)
            resumed_labels = set(labels[index:])
            if self._handoff_resolver is not None:
                self._handoff_resolver.reset_run_zone(
                    run_id,
                    producer_steps=resumed_labels,
                    worker_output_refs=tuple(
                        canonical_worker_output_ref(
                            self._context, f"{run_id}:{step.label}:attempt-{attempt}"
                        )
                        for step in steps[index:]
                        for attempt in range(self._max_review_retries + 1)
                    ),
                    context=self._context,
                    release_id=self._release_id,
                )
            kept = tuple(
                record
                for record in prior.workflow_steps.records
                if record.producer_step not in resumed_labels
            )
            run = replace(
                prior,
                phase=steps[index].from_phase,
                status=LifecycleRunStatus.RUNNING,
                current_step=resume_from,
                blocked=None,
                workflow_steps=WorkflowStepLedger(records=kept),
            )
            steps = steps[index:]
        else:
            # Restart semantics (bug rerun-of-run-id-collides-with-immutable-payload-zone):
            # replacing the run record discards its ledger, so reclaim the orphaned payload
            # zone before the new generation's attempt-0 writes.
            if self._handoff_resolver is not None:
                self._handoff_resolver.reset_run_zone(
                    run_id,
                    worker_output_refs=tuple(
                        canonical_worker_output_ref(
                            self._context, f"{run_id}:{step.label}:attempt-{attempt}"
                        )
                        for step in steps
                        for attempt in range(self._max_review_retries + 1)
                    ),
                    context=self._context,
                    release_id=self._release_id,
                )
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
        attempt = 0
        retry_source: tuple[str, int] | None = None
        while True:
            retry_requested = False
            for index, step in enumerate(steps, start=1):
                digest: str | None = None
                if self._resume_digest is not None:
                    digest = self._resume_digest
                    self._resume_digest = None
                live_step = step.runtime_kind is not AgentRuntimeKind.FAKE
                if live_step:
                    self._progress(
                        f"implementation-reviews step {step.label!r} ({index}/{len(steps)}) "
                        f"started on {step.runtime_kind.value} — a live worker step may take "
                        "several minutes; it times out and blocks cleanly on its own"
                    )
                close_zone_snapshot = self._snapshot_close_zone() if step.label == "close" else None
                if step.label == "implement" and retry_source is not None:
                    assert self._handoff_resolver is not None
                    producer_step, producer_attempt = retry_source
                    resolved = self._handoff_resolver.resolve_required(
                        run, producer_step=producer_step, attempt=producer_attempt
                    )
                    run = self._handoff_resolver.record_consumption(
                        run,
                        producer_step=producer_step,
                        producer_attempt=producer_attempt,
                        consumer_step=step.label,
                        consumer_attempt=attempt,
                    )
                    digest = WorkflowHandoffResolver.render_digest(resolved)
                    retry_source = None

                runtime = self._runtime_factory(step.runtime_kind)
                run, scope = self._inject_role_atoms(
                    run,
                    step,
                    self._scope(step, run_id, attempt=attempt, digest_suffix=digest),
                )
                built = self._prompt_builder.build(
                    scope, runtime=runtime.runtime_kind(), prefix=self._prefix
                )
                runner = LifecycleAgentRunner(
                    runtime=runtime,
                    state_machine=self._state_machine,
                    runtime_files=self._runtime_files,
                    artifact_root=self._artifact_root,
                )
                runner_input = AgentRunnerInput(
                    request=built.request,
                    target_phase=step.target_phase or run.phase,
                    requirements=step.requirements,
                    current_step=step.label,
                    is_review=step.is_review,
                    deliverable_globs=(
                        (
                            (f"repos/{self._context}/specs/releases/{self._release_id}/CLOSURE.md"),
                            f"specs/releases/{self._release_id}/CLOSURE.md",
                        )
                        if step.label == "close"
                        # Bug lifecycle-worker-executes-at-workspace-root-not-context-repo:
                        # when the implement step carries a derived write set, at least
                        # one delivered path must land INSIDE it — a worker writing at
                        # the workspace root (outside repos/<ctx>/) blocks AT the step
                        # with the correct zone in its retry digest.
                        else (
                            self._implement_deliverable_globs(step)
                            if step.label == "implement" and step.extra_allowed_paths
                            else ()
                        )
                    ),
                )
                if step.target_phase is None:
                    worker_result, blocked = runner.evaluate_gate_with_result(run, runner_input)
                    if blocked is None:
                        run = replace(run, current_step=step.label)
                        accepted = True
                    else:
                        decision = self._state_machine.transition(
                            run,
                            TransitionInput(
                                target_phase=LifecyclePhase.BLOCKED,
                                blocked_state=blocked,
                                current_step=step.label,
                            ),
                        )
                        run = decision.run
                        accepted = False
                else:
                    decision, worker_result = runner.run_with_result(run, runner_input)
                    run = decision.run
                    accepted = decision.advanced

                if accepted and step.label == "close" and self._memory_lint_gate is not None:
                    lint_ok, lint_evidence = self._memory_lint_gate()
                    if not lint_ok:
                        blocked_lint = BlockedState(
                            reason=(
                                "close blocked: memory atoms carry lint findings — closure "
                                "must leave specs/memory lint-clean (fix the atom headings/"
                                "frontmatter per the memory template, then resume)"
                            ),
                            blocked_at_step="close",
                            resume_token=run.idempotency_key,
                            detail={"memory_lint": lint_evidence[-1500:]},
                        )
                        decision = self._state_machine.transition(
                            run,
                            TransitionInput(
                                target_phase=LifecyclePhase.BLOCKED,
                                blocked_state=blocked_lint,
                                current_step=step.label,
                            ),
                        )
                        run = decision.run
                        accepted = False

                if accepted and step.label == "close" and self._executed_test_gate is not None:
                    tests_ok, tests_evidence = self._executed_test_gate()
                    if tests_ok is False:
                        blocked_close = BlockedState(
                            reason=(
                                "close blocked: executed test validation is not green — "
                                "closure requires the declared test suite to RUN and pass "
                                "(planned-but-unexecuted validation never closes a release)"
                            ),
                            blocked_at_step="close",
                            resume_token=run.idempotency_key,
                            detail={"executed_tests": tests_evidence[-1500:]},
                        )
                        decision = self._state_machine.transition(
                            run,
                            TransitionInput(
                                target_phase=LifecyclePhase.BLOCKED,
                                blocked_state=blocked_close,
                                current_step=step.label,
                            ),
                        )
                        run = decision.run
                        accepted = False

                verdict = worker_result.structured_output.get("verdict")
                rejected_review = (
                    step.is_review
                    and worker_result.status is AgentRunStatus.SUCCEEDED
                    and bool(worker_result.artifact_refs)
                    and verdict == "REJECTED"
                )
                will_retry = rejected_review and attempt < self._max_review_retries
                if (accepted or rejected_review) and self._handoff_resolver is not None:
                    run = self._produce_step_payload(
                        run,
                        step,
                        worker_result,
                        attempt=attempt,
                        declared_consumers=("implement",) if will_retry else (),
                    )
                if step.label == "close" and not accepted:
                    # Transactional close (bug blocked-close-materializes-closure-...):
                    # a blocked close leaves no half-written closure/memory state.
                    self._restore_close_zone(close_zone_snapshot)
                if live_step:
                    self._progress(
                        f"implementation-reviews step {step.label!r} ({index}/{len(steps)}) "
                        + ("accepted" if accepted else "blocked")
                    )
                self._run_store.save(run)
                results.append(
                    PipelineStepResult(
                        label=step.label,
                        runtime_kind=step.runtime_kind,
                        accepted=accepted,
                        phase=run.phase,
                        blocked=run.blocked,
                        attempt=attempt,
                    )
                )
                if accepted:
                    continue
                if will_retry:
                    retry_source = (step.label, attempt)
                    attempt += 1
                    run = replace(
                        run,
                        phase=LifecyclePhase.IMPLEMENTATION,
                        status=LifecycleRunStatus.RUNNING,
                        current_step=steps[0].label,
                        blocked=None,
                    )
                    self._run_store.save(run)
                    retry_requested = True
                    break
                return PipelineResult(
                    run_id=run_id,
                    completed=False,
                    final_phase=run.phase,
                    steps=tuple(results),
                    blocked=run.blocked,
                )
            if not retry_requested:
                break
        # FR-B: the terminal ATOMIC save — CLI-reported success and the persisted run must
        # agree. A save
        # failure propagates (the run store raises), which fails the command rather than
        # silently reporting success over an unpersisted terminal state.
        run = replace(run, status=LifecycleRunStatus.COMPLETED)
        self._rewrite_task_markers("-", "x")
        self._require_task_markers(("x",), boundary="implementation completion")
        if self._memory_catalog_regenerator is not None:
            # Derived-state refresh must never un-close a completed release.
            with contextlib.suppress(Exception):
                self._memory_catalog_regenerator()
        if self._repo_hygiene_sweeper is not None:
            with contextlib.suppress(Exception):
                self._repo_hygiene_sweeper()
        self._reset_active_md()
        if self._closure_committer is not None:
            with contextlib.suppress(Exception):
                self._closure_committer()
        self._run_store.save(run)
        return PipelineResult(
            run_id=run_id,
            completed=True,
            final_phase=run.phase,
            steps=tuple(results),
        )

    def _rewrite_task_markers(self, source: str, target: str) -> int:
        """Atomically rewrite generated checklist task markers in active TASKS.md."""
        if self._specs_dir is None:
            return 0
        path = self._specs_dir / "releases" / self._release_id / "TASKS.md"
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return 0

        count = 0
        updated_lines: list[str] = []
        for line in text.splitlines(keepends=True):
            updated = line
            for pattern in _TASK_MARKER_LINE_RES:
                match = pattern.match(line.rstrip("\r\n"))
                if match is None:
                    continue
                if match.group("marker") == source:
                    start, end = match.span("marker")
                    updated = f"{line[:start]}{target}{line[end:]}"
                    count += 1
                break
            updated_lines.append(updated)

        updated = "".join(updated_lines)
        if not count:
            return 0
        tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
        tmp.write_text(updated, encoding="utf-8")
        try:
            os.replace(tmp, path)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise
        return count

    def _implement_deliverable_globs(self, step: PipelineStep) -> tuple[str, ...]:
        """The implement step's deliverable zone in BOTH canonical spellings.

        Bug implementation-deliverable-zone-misses-context-repo: TASKS write sets are
        commonly repo-relative (``src/**``) while workers report workspace-relative
        paths (``repos/<ctx>/src/...``) — both name the same zone, so both must match.
        A glob already qualified with ``repos/`` passes through unchanged.
        """
        globs: list[str] = []
        for raw in step.extra_allowed_paths:
            path = raw.format(context=self._context, release_id=self._release_id)
            if path not in globs:
                globs.append(path)
            if not path.startswith("repos/"):
                qualified = f"repos/{self._context}/{path}"
                if qualified not in globs:
                    globs.append(qualified)
        return tuple(globs)

    @staticmethod
    def _progress(message: str) -> None:
        """One human progress line on STDERR (bug
        release-definition-codex-hangs-after-spec-create, visibility half): a live
        multi-minute run must never be silent — validators kill healthy workers.
        stdout stays machine-pure for --json consumers.
        """
        import sys as _sys

        print(f"[lifecycle] {message}", file=_sys.stderr, flush=True)

    def _snapshot_close_zone(self) -> dict[str, bytes | None] | None:
        """Capture the closure-mutable zone before the close worker runs.

        Bug blocked-close-materializes-closure-and-leaves-specs-incoherent: the close
        worker legitimately writes CLOSURE.md + memory atoms, but a BLOCKED close must
        be transactional. Captures every file under ``specs/memory/`` plus the
        release's CLOSURE.md (``None`` marks paths that did not exist).
        """
        if self._specs_dir is None:
            return None
        snapshot: dict[str, bytes | None] = {}
        memory_dir = self._specs_dir / "memory"
        if memory_dir.is_dir():
            for path in memory_dir.rglob("*"):
                if path.is_file():
                    with contextlib.suppress(OSError):
                        snapshot[str(path)] = path.read_bytes()
        closure = self._specs_dir / "releases" / self._release_id / "CLOSURE.md"
        snapshot[str(closure)] = closure.read_bytes() if closure.is_file() else None
        # Sentinel key so restore can prune NEW files created under memory/.
        snapshot["__memory_dir__"] = str(memory_dir).encode("utf-8")
        return snapshot

    def _restore_close_zone(self, snapshot: dict[str, bytes | None] | None) -> None:
        """Roll the closure-mutable zone back to its pre-close-worker state."""
        if snapshot is None or self._specs_dir is None:
            return
        memory_dir_raw = snapshot.get("__memory_dir__")
        memory_dir = Path(memory_dir_raw.decode("utf-8")) if memory_dir_raw else None
        known = {key for key in snapshot if key != "__memory_dir__"}
        # Remove files CREATED by the blocked close attempt.
        if memory_dir is not None and memory_dir.is_dir():
            for path in memory_dir.rglob("*"):
                if path.is_file() and str(path) not in known:
                    with contextlib.suppress(OSError):
                        path.unlink()
        # Restore pre-existing content; drop files that did not exist.
        for key in known:
            path = Path(key)
            content = snapshot[key]
            with contextlib.suppress(OSError):
                if content is None:
                    if path.is_file():
                        path.unlink()
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)

    def _reset_active_md(self) -> None:
        """Point ACTIVE.md at none/none — the Python-owned effect of a SUCCESSFUL close.

        Bug implementation-close-block-resets-active-release-and-breaks-resume: the
        worker must never touch ACTIVE.md (it is out of the close scope now); Python
        rewrites it only after the whole ladder completes.
        """
        if self._specs_dir is None:
            return
        releases = self._specs_dir / "releases"
        with contextlib.suppress(OSError):
            releases.mkdir(parents=True, exist_ok=True)
            (releases / "ACTIVE.md").write_text("release: none\nphase: none\n", encoding="utf-8")

    def _require_task_markers(self, allowed: tuple[str, ...], *, boundary: str) -> None:
        """Fail closed when TASKS marker state does not match a pipeline boundary."""
        if self._specs_dir is None:
            return
        path = self._specs_dir / "releases" / self._release_id / "TASKS.md"
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            # ``--skip-preflight`` diagnostic/test pipelines may deliberately omit SDD
            # artifacts. The normal CLI preflight owns the missing-file gate.
            return
        except OSError as exc:
            raise TasksMarkerStateError(
                f"cannot validate task markers at {boundary}: {path}"
            ) from exc

        markers: list[str] = []
        for line in text.splitlines():
            for pattern in _TASK_MARKER_LINE_RES:
                match = pattern.match(line)
                if match is not None:
                    markers.append(match.group("marker"))
                    break
        if not markers:
            raise TasksMarkerStateError(
                f"no recognizable task markers at {boundary}: {path}. TASKS.md must "
                "declare at least one task line the pipeline grammar recognizes "
                "(e.g. '- [ ] T-1 - <title>')."
            )
        unexpected = sorted({marker for marker in markers if marker not in allowed})
        if unexpected:
            rendered = ", ".join(f"[{marker}]" for marker in unexpected)
            raise TasksMarkerStateError(
                f"invalid task marker state at {boundary}: found {rendered} in {path}"
            )

    def _produce_step_payload(
        self,
        run: LifecycleRun,
        step: PipelineStep,
        result: AgentRunResult,
        *,
        attempt: int = 0,
        declared_consumers: tuple[str, ...] = (),
    ) -> LifecycleRun:
        """Write *step*'s run-scoped handoff-ledger payload through the wired resolver.

        A review step (``is_review=True``) produces a verdict-shaped payload (the schema
        keyed by label — ``qa-review-handoff-v1`` / ``security-review-handoff-v1`` /
        ``code-review-handoff-v1``); a create step (``is_review=False``, e.g.
        ``implement``) produces a summary-shaped ``generic-step-handoff-v1`` payload. No
        consumer is declared (the full ladder is Python-sequenced, not itself a
        producer→consumer graph like the implement/review loop) — this is pure
        observability/diagnosability for ``handoffs doctor`` and the panel, matching the
        loop's per-attempt payloads.
        """
        assert self._handoff_resolver is not None
        payload = durable_payload_from_result(
            result, fallback_summary=step.label, is_review=step.is_review
        )
        output_schema = (
            _REVIEW_OUTPUT_SCHEMA_BY_LABEL.get(step.label, "qa-review-handoff-v1")
            if step.is_review
            else ("closure-handoff-v1" if step.label == "close" else "generic-step-handoff-v1")
        )
        run, _record = self._handoff_resolver.produce(
            run,
            producer_step=step.label,
            attempt=attempt,
            output_schema=output_schema,
            payload=payload,
            declared_consumers=declared_consumers,
        )
        return run

    def _scope(
        self,
        step: PipelineStep,
        run_id: str,
        *,
        attempt: int = 0,
        digest_suffix: str | None = None,
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
        output_glob = worker_output_glob(self._context)
        # FR7 (T-66-08): the raw-output glob is unioned with the step's
        # extra_allowed_paths for NON-REVIEW steps only. Gated on step.is_review is False
        # (ARCHITECT MEDIUM-2) — never a label string match — so review steps
        # (review_qa/review_security/review_code, is_review=True) ALWAYS stay
        # handoff-only regardless of what extra_allowed_paths carries.
        expanded_paths_list: list[str] = []
        for _raw in step.extra_allowed_paths:
            _path = _raw.format(context=self._context, release_id=self._release_id)
            if _path not in expanded_paths_list:
                expanded_paths_list.append(_path)
            # Dual spelling (bug implementation-deliverable-zone-misses-context-repo):
            # repo-relative write sets and workspace-relative worker reports name the
            # same zone.
            if not _path.startswith("repos/"):
                _qualified = f"repos/{self._context}/{_path}"
                if _qualified not in expanded_paths_list:
                    expanded_paths_list.append(_qualified)
        expanded_paths = tuple(expanded_paths_list)
        expanded_paths = filter_context_spec_paths(
            expanded_paths,
            workspace_root=self._artifact_root,
            specs_dir=self._specs_dir,
        )
        allowed_paths = (output_glob, *expanded_paths) if not step.is_review else (output_glob,)
        return PromptScope(
            role=step.role,
            context=self._context,
            release_id=self._release_id,
            task_id=f"{run_id}:{step.label}:attempt-{attempt}",
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
                " Because this is a REVIEW step, emit a structured result whose "
                "structured_output.verdict is APPROVED or REJECTED, with an artifact_ref "
                "pointing at the assigned step-output artifact."
            )
        else:
            tail = (
                " Because this is a CREATE step, emit a structured result with the produced "
                "artifact in artifact_refs pointing at the assigned step-output; do NOT "
                "self-judge — the "
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
        selected = self._select_context(step, (fragment, *shared))
        return build_fragment_suffix(
            self._fragment_bundle(step, fragment, shared),
            selected_context=self._render_selection(selected),
            is_review=step.is_review,
        )

    def _select_context(
        self, step: PipelineStep, fragments: tuple[Fragment, ...]
    ) -> SelectionAudit:
        """Resolve main and shared fragment inputs under each fragment's own policy."""
        if self._context_selector is None:
            return SelectionAudit(step=step.label)
        results: list[SelectionResult] = []
        seen: set[str] = set()
        for fragment in fragments:
            names = tuple(name for name in fragment.dynamic_inputs if name not in seen)
            seen.update(names)
            if not names:
                continue
            selected = self._context_selector.select_all(
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
    """The canonical release pipeline: implement → reviews → bounded correction → close.

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
            # the TDD implement fragment, citing the shared write-scope / anti-slop
            # disciplines plus the self-verify fragment. The output contract is stated
            # once by the engine's Required-output section — no shared restatement.
            fragment_id="implementation.implement_tdd",
            shared_fragment_ids=(
                "shared.write_scope",
                "shared.anti_slop",
                "implementation.self_verify",
            ),
        ),
        PipelineStep(
            label="review_combined",
            role="qa-engineer, security-reviewer, code-reviewer",
            from_phase=LifecyclePhase.QA_REVIEW,
            target_phase=LifecyclePhase.CLOSURE,
            runtime_kind=default_kind,
            model_profile=effort,
            is_review=True,
            # v0.2.x simplification: ONE tri-angle review (QA + security + code) replaces
            # the three sequential single-angle reviews — same rubric coverage, one
            # worker session. This step still mechanically gates the release toward the
            # push boundary and must never fall back to the generic placeholder.
            fragment_id="implementation.combined_review",
        ),
        PipelineStep(
            label="close",
            role="product-engineer",
            from_phase=LifecyclePhase.CLOSURE,
            target_phase=None,
            runtime_kind=default_kind,
            model_profile=effort,
            fragment_id="implementation.close_release",
            shared_fragment_ids=("shared.memory_selection",),
            extra_allowed_paths=(
                # ACTIVE.md is deliberately NOT here: pointing it at none/none is a
                # Python-owned effect of a SUCCESSFUL close (bug
                # implementation-close-block-resets-active-release-and-breaks-resume).
                "repos/{context}/specs/releases/{release_id}/**",
                "specs/releases/{release_id}/**",
                "repos/{context}/specs/memory/**",
                "specs/memory/**",
            ),
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
    the run's default kind before calling this is what keeps a
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
