"""Release-definition workflow body — the SPEC §6.1 sequence on fragments + gates (WS-5).

The keystone of the v0.1.24 two-layer redesign: the release-definition workflow runs as a
Python-owned procedure rather than a single generic ``"Run the {label} step"`` prompt. Python
owns step **order** and gate **decisions**; each model step's prompt is assembled from its
fragment bundle + the dynamically selected context (bounded by ``max_context_policy``) + the
output schema + the discrete ``(harness, model)`` for the step.

As of v0.1.57 FR1 the assembly + gate machinery lives once in
:class:`~dadaia_workspace.features.lifecycle.workflows._fragment_gate.FragmentGateWorkflow`
(the ONE prompt-assembly seam shared with ``audit``). This body
is now a thin subclass that declares the five divergence hooks — the ``release_definition``
command, the RELEASE_DEFINITION initial phase, the terminal transition to IMPLEMENTATION, and
the ``ReleaseStep`` / ``ReleaseDefinitionResult`` dataclass types — and keeps its module-global
``_SEQUENCE`` (imported by the fragment-coverage / loader / persona guardrail suites).

**Python owns the gates.** Each review step's structured verdict (APPROVED / REJECTED) is read
by Python; a REJECTED or missing-evidence review BLOCKS advancement. The terminal
``definition_commit_gate`` is a Python step with **no model** — it advances the release to
IMPLEMENTATION only when every prior gate passed and the workflow-step handoff graph is whole.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    BlockedState,
    LifecyclePhase,
)
from dadaia_workspace.core.models.workflow_execution import ResolvedModelConfig
from dadaia_workspace.features.lifecycle.workflows._fragment_gate import (
    FragmentGateWorkflow,
    _StepOutcome,
)


@dataclass(frozen=True)
class ReleaseStep:
    """One step of the §6.1 release-definition sequence.

    A model step names its fragment id (``workflow.step``), the shared fragment ids it cites,
    the runtime kind it runs on, and whether it is a **review** (a gate whose verdict can
    REJECT and thereby BLOCK advancement). The terminal Python gate carries ``fragment_id=None``
    and ``runtime_kind=None`` — it runs no model.
    """

    label: str
    role: str
    fragment_id: str | None
    shared_fragment_ids: tuple[str, ...] = ()
    is_review: bool = False
    runtime_kind: AgentRuntimeKind | None = None
    # Workflow-step handoff data plane edges (v0.1.30 Item 5 / T-30-D-05). ``produces`` is the
    # named payload schema this step writes (None ⇒ no ledger payload); ``consumes`` is the
    # tuple of upstream producer-step labels this step resolves by exact (run id, producer
    # step, attempt) BEFORE running (A19/A20/A25). Inert unless a resolver is wired.
    produces: str | None = None
    consumes: tuple[str, ...] = ()
    # Governance-resolved concrete model for this step (v0.1.56 / FR1). ``apply_resolved_policy``
    # threads the resolved snapshot model here; the base ``_scope`` forwards it to the request so
    # the adapter runs the policy-selected model. Additive-optional, mirroring ``PipelineStep``.
    resolved_model: ResolvedModelConfig | None = None
    model_profile: str | None = None
    # Step-declared write paths beyond the handoff zone (bug
    # release-definition-create-steps-cannot-write-specs). Placeholders {context} and
    # {release_id} are expanded by the shared ``_scope``.
    extra_allowed_paths: tuple[str, ...] = ()


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
#: Fragment ids match the shipped ``release_definition/*`` bundle; ``spec_arch_review`` maps to
#: ``release_definition.spec_review_architecture``.
_SEQUENCE: tuple[ReleaseStep, ...] = (
    ReleaseStep(
        label="release_scope",
        role="product-engineer",
        fragment_id="release_definition.release_scope",
        produces="release-scope-handoff-v1",
    ),
    ReleaseStep(
        label="spec_create",
        role="product-engineer",
        fragment_id="release_definition.spec_create",
        shared_fragment_ids=(
            "shared.anti_slop",
            "shared.memory_selection",
        ),
        produces="generic-step-handoff-v1",
        extra_allowed_paths=(
            "repos/{context}/specs/releases/{release_id}/**",
            "specs/releases/{release_id}/**",
            "repos/{context}/specs/releases/ACTIVE.md",
            "specs/releases/ACTIVE.md",
        ),
        consumes=("release_scope",),
    ),
    ReleaseStep(
        label="spec_review",
        role="software-architect, qa-engineer",
        fragment_id="release_definition.spec_review",
        is_review=True,
        produces="spec-review-handoff-v1",
        consumes=("spec_create",),
    ),
    ReleaseStep(
        label="plan_create",
        role="product-engineer",
        fragment_id="release_definition.plan_create",
        shared_fragment_ids=(
            "shared.anti_slop",
            "shared.memory_selection",
        ),
        produces="generic-step-handoff-v1",
        extra_allowed_paths=(
            "repos/{context}/specs/releases/{release_id}/**",
            "specs/releases/{release_id}/**",
            "repos/{context}/specs/releases/ACTIVE.md",
            "specs/releases/ACTIVE.md",
        ),
        consumes=("spec_create",),
    ),
    ReleaseStep(
        label="plan_review",
        role="qa-engineer, software-architect",
        fragment_id="release_definition.plan_review",
        is_review=True,
        produces="plan-review-handoff-v1",
        consumes=("plan_create",),
    ),
    ReleaseStep(
        label="tasks_create",
        role="product-engineer",
        fragment_id="release_definition.tasks_create",
        shared_fragment_ids=("shared.anti_slop",),
        produces="generic-step-handoff-v1",
        extra_allowed_paths=(
            "repos/{context}/specs/releases/{release_id}/**",
            "specs/releases/{release_id}/**",
            "repos/{context}/specs/releases/ACTIVE.md",
            "specs/releases/ACTIVE.md",
        ),
        consumes=("plan_create",),
    ),
    ReleaseStep(
        label="tasks_implementability_review",
        role="software-engineer",
        fragment_id="release_definition.tasks_review_implementability",
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


class ReleaseDefinitionWorkflow(FragmentGateWorkflow[ReleaseStep, ReleaseDefinitionResult]):
    """Run the §6.1 release-definition sequence with fragment prompts + Python gates.

    Thin subclass of :class:`FragmentGateWorkflow`: the shared assembly + gate machinery lives
    in the base; this body declares the divergence hooks and its result factory. The terminal
    gate transitions the release to IMPLEMENTATION (``_TERMINAL_PHASE``).
    """

    _COMMAND = "release_definition"
    _WORKFLOW_LABEL = "release-definition"
    _INITIAL_PHASE = LifecyclePhase.RELEASE_DEFINITION
    _TERMINAL_PHASE = LifecyclePhase.IMPLEMENTATION

    def run(
        self,
        run_id: str,
        sequence: tuple[ReleaseStep, ...] = _SEQUENCE,
        *,
        resume_from: str | None = None,
        skip_scope: bool = False,
    ) -> ReleaseDefinitionResult:
        """Execute the sequence; stop at the first blocked gate; advance on success.

        ``skip_scope=True`` (small-release fast path): when the CLI already consumed a
        completed backlog-definition pick (injected as the authoritative prompt prefix),
        the ``release_scope`` model step is a redundant restatement — it is dropped from
        the sequence and its ``consumes`` edges are erased, saving one worker session.
        """
        if skip_scope:
            from dataclasses import replace as _replace

            sequence = tuple(
                _replace(
                    step,
                    consumes=tuple(c for c in step.consumes if c != "release_scope"),
                )
                for step in sequence
                if step.label != "release_scope"
            )
        return self._run_sequence(run_id, sequence, resume_from=resume_from)

    #: Review-gate label → the SDD artifact it approves (bug
    #: approved-review-never-flips-artifact-status). ``spec_review`` is the single
    #: merged SPEC gate (architecture + QA angles in one call, v0.2.x simplification).
    _STATUS_FLIP_BY_REVIEW: ClassVar[dict[str, str]] = {
        "spec_review": "SPEC.md",
        "plan_review": "PLAN.md",
        "tasks_implementability_review": "TASKS.md",
    }

    def _on_step_accepted(self, step: ReleaseStep) -> BlockedState | None:
        """Validate PLAN dependencies, then approve reviewed artifacts.

        Deterministic Python, not model output: the workflow's own review gate IS the
        approval authority, so the canonical ``> **Status:**`` token must reflect it —
        otherwise downstream workers correctly refuse to build on a Draft artifact.
        """
        if step.label == "plan_create":
            dependency_block = self._validate_plan_dependency_table()
            if dependency_block is not None:
                return dependency_block
        if step.label == "tasks_create":
            hygiene_block = self._validate_tasks_command_hygiene()
            if hygiene_block is not None:
                return hygiene_block
        filename = self._STATUS_FLIP_BY_REVIEW.get(step.label)
        if filename is None:
            return None
        path = self._selector.spec_context.specs_dir / "releases" / self._release_id / filename
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        status_line = (
            r"(?mi)^(?:>\s*)?(?:\*\*Status:\*\*|Status:)\s*"
            r"(?:Draft|Em revisão|Em revisao|Aprovado)\s*$"
        )
        updated = re.sub(status_line + r"\n?", "", text)
        frontmatter = re.match(r"\A---\n.*?\n---\n?", updated, flags=re.DOTALL)
        if frontmatter is not None:
            insertion_at = frontmatter.end()
        else:
            heading = re.match(r"\A#[^\n]*(?:\n|\Z)", updated)
            insertion_at = heading.end() if heading is not None else 0
        updated = (
            updated[:insertion_at].rstrip()
            + "\n\n> **Status:** Aprovado\n\n"
            + updated[insertion_at:].lstrip()
        )
        path.write_text(updated, encoding="utf-8")
        return None

    def _validate_tasks_command_hygiene(self) -> BlockedState | None:
        """Reject executable pytest snippets that can dirty the repository.

        Model review still judges the full validation strategy. This narrow Python
        backstop enforces the workspace invariant that pytest must not create
        ``.pytest_cache``. ``--cache-clear`` is deliberately insufficient because it
        removes an old cache before allowing the cache provider to create a new one.
        """
        path = self._selector.spec_context.specs_dir / "releases" / self._release_id / "TASKS.md"
        if not path.is_file():
            return self._tasks_hygiene_block("TASKS.md was not created")

        text = path.read_text(encoding="utf-8")
        snippets = re.findall(r"`([^`\n]+)`", text)
        snippets.extend(
            match.group(1) for match in re.finditer(r"```[^\n]*\n(.*?)```", text, flags=re.DOTALL)
        )
        pytest_invocation = re.compile(
            r"(?:^|[;&|\n]\s*|\s)"
            r"(?:(?:\S*/)?python(?:\d+(?:\.\d+)*)?\s+-m\s+)?"
            r"(?:\S*/)?pytest(?:\s|$)",
            flags=re.IGNORECASE,
        )
        for snippet in snippets:
            if pytest_invocation.search(snippet) and not re.search(
                r"(?:^|\s)-p\s+no:cacheprovider(?:\s|$)", snippet
            ):
                compact = " ".join(snippet.split())
                if len(compact) > 160:
                    compact = compact[:157] + "..."
                return self._tasks_hygiene_block(
                    f"pytest validation command is missing '-p no:cacheprovider': {compact!r}"
                )
        return None

    @staticmethod
    def _tasks_hygiene_block(reason: str) -> BlockedState:
        return BlockedState(
            reason=f"TASKS command hygiene lint failed: {reason}",
            blocked_at_step="tasks_create",
            operator_command=(
                "re-run release-definition with --resume-from tasks_create "
                "(only the TASKS authoring step re-executes)"
            ),
            detail={"artifact": "TASKS.md", "gate": "task-command-hygiene-v1"},
        )

    def _validate_plan_dependency_table(self) -> BlockedState | None:
        """Reject structurally unverifiable or forward-dependent PLAN validation.

        Model review still judges whether the table is truthful. This Python gate makes
        the dependency declaration mandatory and prevents an explicitly forward-pointing
        validation plan from consuming reviewer time or reaching TASK authoring.
        """
        path = self._selector.spec_context.specs_dir / "releases" / self._release_id / "PLAN.md"
        if not path.is_file():
            return self._plan_dependency_block("PLAN.md was not created")
        lines = path.read_text(encoding="utf-8").splitlines()
        try:
            heading = next(
                index
                for index, line in enumerate(lines)
                if re.fullmatch(
                    r"##\s+(?:\d+\s*[.)-]?\s+)?validation dependency table",
                    line.strip(),
                    flags=re.IGNORECASE,
                )
            )
        except StopIteration:
            return self._plan_dependency_block(
                "PLAN.md is missing the required 'Validation Dependency Table' section"
            )

        section: list[str] = []
        for line in lines[heading + 1 :]:
            if line.lstrip().startswith("## "):
                break
            section.append(line)
        table_lines = [line.strip() for line in section if line.strip().startswith("|")]
        if len(table_lines) < 3:
            return self._plan_dependency_block(
                "validation dependency table requires a header and at least one workstream row"
            )
        header = [" ".join(cell.split()).lower() for cell in table_lines[0].strip("|").split("|")]
        expected = [
            "workstream",
            "produces by end",
            "direct validation",
            "validation dependencies",
            "deferred integration evidence",
        ]
        if header != expected:
            return self._plan_dependency_block(
                "validation dependency table columns must match the workflow contract "
                f"(case/whitespace-insensitive): expected {expected}, got {header}"
            )

        seen: set[int] = set()
        for raw in table_lines[2:]:
            cells = [cell.strip() for cell in raw.strip("|").split("|")]
            if len(cells) != len(expected) or any(not cell for cell in cells):
                return self._plan_dependency_block(
                    "every validation dependency row must contain all five non-empty cells"
                )
            match = re.fullmatch(r"WS-(\d+)", cells[0], flags=re.IGNORECASE)
            if match is None:
                return self._plan_dependency_block(
                    f"invalid workstream identifier {cells[0]!r}; expected WS-<number>"
                )
            current = int(match.group(1))
            if current in seen:
                return self._plan_dependency_block(f"duplicate workstream WS-{current}")
            seen.add(current)
            refs = {int(value) for value in re.findall(r"WS-(\d+)", cells[3], flags=re.IGNORECASE)}
            forward = sorted(ref for ref in refs if ref > current)
            if forward:
                return self._plan_dependency_block(
                    f"WS-{current} validation depends on later workstream(s): "
                    + ", ".join(f"WS-{ref}" for ref in forward)
                )
        return None

    @staticmethod
    def _plan_dependency_block(reason: str) -> BlockedState:
        return BlockedState(
            reason=f"plan dependency lint failed: {reason}",
            blocked_at_step="plan_create",
            operator_command=(
                "re-run release-definition with --resume-from plan_create "
                "(only the PLAN authoring step re-executes)"
            ),
            detail={"artifact": "PLAN.md", "gate": "validation-dependency-table-v1"},
        )

    def _on_sequence_completed(self) -> None:
        """Repoint ACTIVE.md to the newly defined release (deterministic Python).

        Bug definition-commit-gate-never-repoints-active-md: a completed definition IS
        the release-activation authority — every ACTIVE.md reader (doctor, memory-phase
        gate, spec navigator, workers) must see the new release immediately, not the
        previous one. Same Python-owned semantics as the review status flips.
        """
        releases_dir = self._selector.spec_context.specs_dir / "releases"
        releases_dir.mkdir(parents=True, exist_ok=True)
        (releases_dir / "ACTIVE.md").write_text(
            f"release: {self._release_id}\nphase: IMPLEMENTATION\n",
            encoding="utf-8",
        )

    def _make_result(
        self,
        *,
        run_id: str,
        completed: bool,
        final_phase: LifecyclePhase,
        outcomes: tuple[_StepOutcome, ...],
        blocked: BlockedState | None,
    ) -> ReleaseDefinitionResult:
        return ReleaseDefinitionResult(
            run_id=run_id,
            completed=completed,
            final_phase=final_phase,
            steps=tuple(_to_step_result(outcome) for outcome in outcomes),
            blocked=blocked,
        )


def _to_step_result(outcome: _StepOutcome) -> ReleaseStepResult:
    return ReleaseStepResult(
        label=outcome.label,
        accepted=outcome.accepted,
        is_gate=outcome.is_gate,
        fragment_id=outcome.fragment_id,
        prompt_text=outcome.prompt_text,
        runtime_kind=outcome.runtime_kind,
        blocked=outcome.blocked,
    )


__all__ = [
    "ReleaseDefinitionResult",
    "ReleaseDefinitionWorkflow",
    "ReleaseStep",
    "ReleaseStepResult",
]
