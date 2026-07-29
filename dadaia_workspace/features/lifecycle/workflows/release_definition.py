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
import unicodedata
from dataclasses import dataclass, field
from typing import ClassVar

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    BlockedState,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.models.workflow_execution import ResolvedModelConfig
from dadaia_workspace.core.spec_status import (
    ANY_STATUS_LINE,
    APPROVED_LINE,
    is_approved,
)
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
    #: The EXACT release-artifact filename this create step must persist (bug
    #: release-definition-completes-without-persisting-artifacts): the zone-wide glob
    #: let a worker "pass" spec_create by writing anything in the release dir. When
    #: set, the structural gate requires THIS file among the step's refs/changed paths.
    deliverable: str | None = None


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
    #: Review objections accepted after their bounded revision was spent. A model verdict is
    #: advisory, never terminal — but never silent: these travel with the release.
    warnings: tuple[str, ...] = field(default_factory=tuple)


#: The §6.1 release-definition sequence. ``runtime_kind=None`` on a model step means the
#: workflow's default harness is used; the terminal gate carries no fragment and no model.
#: Fragment ids match the shipped ``release_definition/*`` bundle; ``spec_arch_review`` maps to
#: ``release_definition.spec_review_architecture``.
_SEQUENCE: tuple[ReleaseStep, ...] = (
    ReleaseStep(
        label="definition_draft",
        role="product-engineer",
        deliverable="SPEC.md",
        fragment_id="release_definition.definition_draft",
        shared_fragment_ids=("shared.anti_slop", "shared.memory_selection"),
        produces="generic-step-handoff-v1",
        extra_allowed_paths=(
            "repos/{context}/specs/releases/{release_id}/**",
            "specs/releases/{release_id}/**",
            "repos/{context}/specs/releases/ACTIVE.md",
            "specs/releases/ACTIVE.md",
        ),
    ),
    ReleaseStep(
        label="definition_review",
        role="software-architect, qa-engineer",
        fragment_id="release_definition.definition_review",
        is_review=True,
        produces="combined-review-handoff-v1",
        consumes=("definition_draft",),
    ),
    ReleaseStep(label="definition_commit_gate", role="python", fragment_id=None),
)


def _resume_command(
    *, context: str, release_id: str, run_id: str, kind: object, step: str, note: str = ""
) -> str:
    """A pasteable resume command, not prose around a flag.

    Module-level and explicit rather than a method: the block builders are exercised with
    lightweight stubs, and making them reach through `self` for this turned every stub
    into a partial reimplementation of the workflow (bug
    r20-release-recovery-loses-accepted-draft-payload — the remedy read "re-run
    release-definition with --resume-from X", which nobody can paste).
    """
    from dadaia_workspace.core.models.lifecycle import HARNESS_CLI_NAMES

    harness = "codex"
    if isinstance(kind, AgentRuntimeKind):
        harness = HARNESS_CLI_NAMES.get(kind, "codex")
    tail = f"  # {note}" if note else ""
    return (
        f"dadaia lifecycle release-definition --context {context} "
        f"--release-id {release_id} --run-id {run_id} --harness {harness} "
        f"--resume-from {step}{tail}"
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
        operator_demand: str | None = None,
    ) -> ReleaseDefinitionResult:
        """Execute the sequence; stop at the first blocked gate; advance on success.

        ``skip_scope=True`` (small-release fast path): when the CLI already consumed a
        completed backlog-definition pick (injected as the authoritative prompt prefix),
        the ``release_scope`` model step is a redundant restatement — it is dropped from
        the sequence and its ``consumes`` edges are erased, saving one worker session.
        """
        self._operator_demand = operator_demand
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
        # Bug r20-release-recovery-loses-accepted-draft-payload: the remedies read
        # "re-run release-definition with --resume-from X" — prose around a flag, not a
        # command. Remember the run id so every block can print a line the operator pastes
        # verbatim; a remedy that has to be assembled by hand is a remedy that gets typed
        # wrong under pressure.
        self._current_run_id = run_id
        return self._run_sequence(run_id, sequence, resume_from=resume_from)

    #: Review-gate label → the SDD artifact it approves (bug
    #: approved-review-never-flips-artifact-status). ``spec_review`` is the single
    #: merged SPEC gate (architecture + QA angles in one call, v0.2.x simplification).
    #: The ONE review approves all three artifacts, so the flip is a list, not a 1:1 map.
    _STATUS_FLIP_BY_REVIEW: ClassVar[dict[str, tuple[str, ...]]] = {
        "definition_review": ("SPEC.md", "PLAN.md", "TASKS.md"),
    }

    #: Artifact → the create step that re-authors it (bug
    #: release-definition-approved-plan-not-persisted-041 — flip-failure remedy).
    _CREATE_STEP_BY_ARTIFACT: ClassVar[dict[str, str]] = {
        "SPEC.md": "definition_draft",
        "PLAN.md": "definition_draft",
        "TASKS.md": "definition_draft",
    }

    #: Artifact → the review step whose re-run re-asserts the Aprovado flip (the
    #: terminal gate's remedy for a Draft artifact with an APPROVED ledger).
    _REVIEW_STEP_BY_ARTIFACT: ClassVar[dict[str, str]] = {
        "SPEC.md": "definition_review",
        "PLAN.md": "definition_review",
        "TASKS.md": "definition_review",
    }

    def _on_step_accepted(self, step: ReleaseStep) -> BlockedState | None:
        """Validate PLAN dependencies, then approve reviewed artifacts.

        Deterministic Python, not model output: the workflow's own review gate IS the
        approval authority, so the canonical ``> **Status:**`` token must reflect it —
        otherwise downstream workers correctly refuse to build on a Draft artifact.
        Python is the SOLE owner of that token (bug
        release-definition-approved-plan-not-persisted-041): an approved review over a
        MISSING artifact fails LOUD here with the create-step resume as remedy — never
        a silent skip that surfaces 3+ model steps later at the terminal gate.
        """
        filenames = self._STATUS_FLIP_BY_REVIEW.get(step.label)
        # The deterministic lints run on the draft step (early feedback) AND again wherever
        # artifacts are flipped to Aprovado. Attaching them ONLY to the step that PRODUCES
        # the artifacts let `--resume-from definition_review` skip production while still
        # performing approval, so a PLAN with no Validation column and a pytest command
        # missing `-p no:cacheprovider` became binding unchecked (bugs
        # r13-release-plan-validation-bypassed-on-resume and
        # r13-release-pytest-hygiene-bypassed-on-resume). A gate a resume can step over is
        # not a gate: approval is the moment the content starts to matter, so it holds there.
        if step.label == "definition_draft" or filenames is not None:
            dependency_block = self._validate_plan_dependency_table()
            if dependency_block is not None:
                return dependency_block
            hygiene_block = self._validate_tasks_command_hygiene()
            if hygiene_block is not None:
                return hygiene_block
        if filenames is None:
            return None
        for filename in filenames:
            block = self._flip_one(filename, step)
            if block is not None:
                return block
        return None

    def _flip_one(self, filename: str, step: ReleaseStep) -> BlockedState | None:
        """Flip ONE reviewed artifact to Aprovado, or block naming its create step."""
        path = self._selector.spec_context.specs_dir / "releases" / self._release_id / filename
        if not path.is_file():
            create_step = self._CREATE_STEP_BY_ARTIFACT[filename]
            return BlockedState(
                reason=(
                    f"{step.label} approved but {filename} is missing on disk — the "
                    "artifact the review approved was never persisted (worker write lost "
                    "or written out of scope)"
                ),
                blocked_at_step=create_step,
                operator_command=(
                    _resume_command(
                        context=self._context,
                        release_id=self._release_id,
                        run_id=getattr(self, "_current_run_id", "release-define"),
                        kind=getattr(self, "_default_kind", None),
                        step="create_step",
                        note=f"only the {filename} authoring step re-executes",
                    )
                ),
                detail={"artifact": filename, "gate": "review-status-flip-v1"},
            )
        text = path.read_text(encoding="utf-8")
        # Single-writer law over the Status token: remove EVERY worker-authored status
        # variant — blockquote or not, bullet-prefixed, colon inside or outside the bold
        # markers, any case ((?i) covers Draft/draft and Status/status) — then insert
        # the one canonical Python-owned line.
        updated = ANY_STATUS_LINE.sub("", text)
        updated = re.sub(r"\n{3,}", "\n\n", updated)
        frontmatter = re.match(r"\A---\n.*?\n---\n?", updated, flags=re.DOTALL)
        if frontmatter is not None:
            insertion_at = frontmatter.end()
        else:
            heading = re.match(r"\A#[^\n]*(?:\n|\Z)", updated)
            insertion_at = heading.end() if heading is not None else 0
        updated = (
            updated[:insertion_at].rstrip()
            + f"\n\n{APPROVED_LINE}\n\n"
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
        # Class-level call: the sibling hygiene checks are exercised with lightweight
        # stubs, and a `self.` lookup would demand the stub grow an attribute that has
        # nothing to do with what those tests assert.
        markers_block = self._unreadable_task_markers_block(text)
        if markers_block is not None:
            return markers_block
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

    def _unreadable_task_markers_block(self, text: str) -> BlockedState | None:
        """BLOCK a TASKS.md whose markers ``implementation-reviews`` cannot parse.

        Bug ``r10-approved-task-markers-rejected-by-implementation``: a live worker wrote
        ``- [ ] TASK-WS1 - …``; the release was APPROVED and then refused at
        implementation start with "no recognizable task markers". Approved-and-unrunnable
        is the worst outcome the chain can produce — the operator is told the release is
        ready and then hits a wall with no path back.

        The check imports the implementation pipeline's OWN regexes rather than restating
        the grammar. A second copy of the rule is how the two sides came to disagree in
        the first place; sharing the predicate makes divergence impossible instead of
        merely unlikely.
        """
        from dadaia_workspace.features.lifecycle.pipeline import _TASK_MARKER_LINE_RES

        lines = text.splitlines()
        if any(
            pattern.match(line) is not None for line in lines for pattern in _TASK_MARKER_LINE_RES
        ):
            return None
        # Only complain when the document looks like it MEANT to carry tasks: a TASKS.md
        # with no checkbox at all is a different failure the artifact gates already own.
        if not any("[ ]" in line or "[-]" in line or "[x]" in line for line in lines):
            return None
        offenders = [line.strip() for line in lines if "[ ]" in line or "[-]" in line][:3]
        return BlockedState(
            reason=(
                "TASKS.md carries checkbox lines that `implementation-reviews` cannot "
                "parse, so this release would be approved and then refused at "
                "implementation start with 'no recognizable task markers'. Task ids must "
                "match T-?<digits> in one of the accepted forms — '- [ ] T-1 - title', "
                "'- [ ] **T01 - title**', '### [ ] T1 - title', or a standalone '[ ] T-1'. "
                f"Unparseable line(s): {offenders}. Rewrite the ids and resume."
            ),
            blocked_at_step="definition_draft",
            operator_command=(
                _resume_command(
                    context=self._context,
                    release_id=self._release_id,
                    run_id=getattr(self, "_current_run_id", "release-define"),
                    kind=getattr(self, "_default_kind", None),
                    step="definition_draft",
                    note="only the TASKS authoring step re-executes",
                )
            ),
            detail={"artifact": "TASKS.md", "gate": "task-marker-parity-v1"},
        )

    def _tasks_hygiene_block(self, reason: str) -> BlockedState:
        return BlockedState(
            reason=f"TASKS command hygiene lint failed: {reason}",
            blocked_at_step="definition_draft",
            operator_command=(
                _resume_command(
                    context=self._context,
                    release_id=self._release_id,
                    run_id=getattr(self, "_current_run_id", "release-define"),
                    kind=getattr(self, "_default_kind", None),
                    step="definition_draft",
                    note="only the TASKS authoring step re-executes",
                )
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

        # Presentation tolerance (bug release-plan-author-does-not-converge-
        # validation-contract): a live worker may legitimately localize the section
        # heading and column titles. The heading is matched by NORMALIZED content
        # (case/accents stripped, canonical English OR a translated
        # dependency+validation table title); semantics below stay strict.
        def _normalize(text: str) -> str:
            stripped = "".join(
                ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
            )
            return " ".join(stripped.lower().split())

        def _is_table_heading(line: str) -> bool:
            candidate = line.strip()
            if not candidate.startswith("##"):
                return False
            title = _normalize(re.sub(r"^#+\s*(?:\d+\s*[.)-]?\s+)?", "", candidate))
            if title == "validation dependency table":
                return True
            return ("valida" in title) and ("depend" in title) and ("tab" in title)

        try:
            heading = next(index for index, line in enumerate(lines) if _is_table_heading(line))
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
        # Column titles: canonical English exactly, OR a positional 5-column fallback
        # (localized titles keep the canonical order; the semantic checks below —
        # WS ids in column 1, dependency refs in column 4 — still bind strictly).
        if header != expected and len(header) != len(expected):
            return self._plan_dependency_block(
                "validation dependency table columns must match the workflow contract "
                f"(five columns, canonical order): expected {expected}, got {header}"
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

    def _plan_dependency_block(self, reason: str) -> BlockedState:
        return BlockedState(
            reason=f"plan dependency lint failed: {reason}",
            blocked_at_step="definition_draft",
            operator_command=(
                _resume_command(
                    context=self._context,
                    release_id=self._release_id,
                    run_id=getattr(self, "_current_run_id", "release-define"),
                    kind=getattr(self, "_default_kind", None),
                    step="definition_draft",
                    note="only the PLAN authoring step re-executes",
                )
            ),
            detail={"artifact": "PLAN.md", "gate": "validation-dependency-table-v1"},
        )

    def _terminal_semantic_block(
        self,
        run: LifecycleRun,
        step: ReleaseStep,
        sequence: tuple[ReleaseStep, ...],
    ) -> BlockedState | None:
        """Refuse to complete a definition whose artifacts are not persisted+approved.

        Bug release-definition-completes-without-persisting-artifacts: a live worker
        can satisfy the transport gate without writing its artifact. The terminal gate
        re-reads DISK truth: SPEC.md/PLAN.md/TASKS.md must exist and SPEC/PLAN must
        carry the review-flipped ``**Status:** Aprovado`` before ACTIVE.md is
        repointed or ``completed`` is reported.
        """
        release_dir = self._selector.spec_context.specs_dir / "releases" / self._release_id
        # NOT run-scoped (bug r22-release-completes-with-unapproved-plan-tasks). These
        # requirements used to be conditioned on whether ``definition_draft`` /
        # ``definition_review`` appeared in THIS run's sequence — so a
        # `--resume-from definition_commit_gate` (which is exactly what a killed-driver
        # recovery prints) arrived carrying no requirement at all, and the gate repointed
        # ACTIVE.md to IMPLEMENTATION over a PLAN/TASKS with no Status line whatsoever.
        #
        # Reaching this gate is not a step in an itinerary, it is the claim that the
        # release is DEFINED and binding on every reader downstream. So it checks DISK
        # truth — what the next reader will actually find — and never the history of the
        # run that happens to be asking. Same reasoning that took the definition lints
        # off the draft step (r13-release-plan-validation-bypassed-on-resume): a gate a
        # resume can step over is not a gate.
        required = ("SPEC.md", "PLAN.md", "TASKS.md")
        missing: list[str] = []
        remedies: list[str] = []
        for name in required:
            path = release_dir / name
            if not path.is_file():
                missing.append(f"{name} (absent)")
                continue
            if not is_approved(path.read_text(encoding="utf-8")):
                missing.append(f"{name} (not Aprovado)")
                # Bug release-definition-approved-plan-not-persisted-041: a Draft
                # artifact with an APPROVED ledger (resumed/rewritten mid-run) recovers
                # by re-running ONLY its review — the flip is re-asserted on acceptance.
                review_step = self._REVIEW_STEP_BY_ARTIFACT.get(name)
                # All three artifacts share ONE review now, so the same remedy would be
                # emitted three times; a command repeated three times is not a command.
                if review_step is not None and f"--resume-from {review_step}" not in remedies:
                    remedies.append(f"--resume-from {review_step}")
        if missing:
            return BlockedState(
                reason=(
                    "definition_commit_gate: release artifacts are not persisted/approved "
                    "on disk: " + ", ".join(missing)
                ),
                blocked_at_step=step.label,
                # NEVER None. An artifact that is missing entirely maps to no review, so
                # `remedies` came back empty and the gate blocked with no way forward
                # (bug a2-release-missing-spec-gate-lacks-resume-remedy). Re-authoring is
                # always a valid recovery, so it is the floor.
                operator_command=(
                    _resume_command(
                        context=self._context,
                        release_id=self._release_id,
                        run_id=getattr(self, "_current_run_id", "release-define"),
                        kind=getattr(self, "_default_kind", None),
                        step=(
                            sorted(remedies)[0].removeprefix("--resume-from ")
                            if remedies
                            else "definition_draft"
                        ),
                        note="the step re-executes and the review re-asserts the Aprovado flip",
                    )
                ),
                detail={"unpersisted_artifacts": ", ".join(missing)},
            )
        return None

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
        # Bug fake-release-definition-leaves-dirty-worktree: the completed definition
        # commits the context repo's definition artifacts (Python-owned, best-effort —
        # like the closure commit), so implementation preflight never inherits a dirty
        # tree. Fixtures wire no committer and stay byte-identical.
        if self._definition_committer is not None:
            import contextlib

            with contextlib.suppress(Exception):
                self._definition_committer()

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
            warnings=self._last_warnings,
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
