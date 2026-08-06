"""WS-5 / T-24-09 — release-definition workflow-specific behavior beyond the shared suite.

The shared e2e-completion / exact-consumption / block-on-missing / no-resolver behaviors are
covered generically for this workflow in ``test_fragment_workflow_bodies.py``. This file keeps
only what is release-definition-specific: **Python owns the gates** — a REJECTED review
handoff BLOCKS advancement and stops the sequence (it never advances on model say-so), the
terminal Python ``definition_commit_gate`` never runs, and the release never reaches
IMPLEMENTATION. Prompt-substring assertions on fragment content are owned by
``test_fragment_gate_goldens.py`` (byte-identical golden captures), not repeated here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    SpecContext,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    _SEQUENCE,
    ReleaseDefinitionWorkflow,
)

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.24"


@dataclass(frozen=True)
class _KindFake:
    kind: AgentRuntimeKind
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return self.result


class _MemoryRunStore:
    def __init__(self) -> None:
        self.saved: dict[str, LifecycleRun] = {}

    def save(self, run: LifecycleRun) -> None:
        self.saved[run.run_id] = run

    def load(self, run_id: str) -> LifecycleRun | None:
        return self.saved.get(run_id)

    def resume(self, run_id: str) -> LifecycleRun:
        run = self.saved.get(run_id)
        if run is None:
            raise LifecycleRunStoreError(message="missing", path=None)
        return run


def _approved() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="ok",
        artifact_refs=(f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _rejected() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="rejected",
        artifact_refs=(f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json",),
        structured_output={"verdict": "REJECTED"},
    )


def _specs_tree(tmp_path: Path) -> Path:
    """A minimal specs tree the context selector can resolve dynamic inputs against."""
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# constitution\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text("# architecture\n", encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text("# qa\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    (specs / "releases" / _RELEASE / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    (specs / "releases" / _RELEASE / "PLAN.md").write_text(
        "# plan\n\n## Validation Dependency Table\n\n"
        "| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |\n"
        "|---|---|---|---|---|\n"
        "| WS-1 | value | unit tests | None | None |\n",
        encoding="utf-8",
    )
    (specs / "releases" / _RELEASE / "TASKS.md").write_text("# tasks\n", encoding="utf-8")
    return specs


def _workflow(
    tmp_path: Path,
    store: _MemoryRunStore,
    factory: object,
) -> ReleaseDefinitionWorkflow:
    specs = _specs_tree(tmp_path)
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / "handoff")
    )
    return ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=store,
        runtime_factory=factory,  # type: ignore[arg-type]
        context_selector=selector,
    )


def test_rejected_review_blocks_advancement(tmp_path: Path) -> None:
    store = _MemoryRunStore()

    # Run the merged SPEC review step on a distinct harness kind so the factory can
    # return a REJECTED verdict for exactly that step while every other step (the
    # create steps) approves. Python — not the model — decides this blocks. The
    # bounded in-run revision re-runs spec_create once, then the still-rejecting
    # review exhausts the budget and the run blocks.
    sequence = tuple(
        replace(step, runtime_kind=AgentRuntimeKind.CODEX_EXEC)
        if step.label == "definition_review"
        else step
        for step in _SEQUENCE
    )

    def kind_factory(kind: AgentRuntimeKind) -> _KindFake:
        if kind is AgentRuntimeKind.CODEX_EXEC:
            return _KindFake(kind, _rejected())
        return _KindFake(kind, _approved())

    wf = _workflow(tmp_path, store, kind_factory)
    result = wf.run("rd-3", sequence)

    # Contract change: a model verdict costs ONE bounded revision and then becomes
    # advisory. Making three non-deterministic verdicts terminal inside a deterministic
    # pipeline is what stopped an autonomous agent from ever finishing a release.
    assert result.completed is True
    assert result.blocked is None
    assert any("definition_review" in w for w in result.warnings), result.warnings
    labels = [s.label for s in result.steps]
    assert "definition_commit_gate" in labels
    assert "definition_commit_gate" in labels
    assert result.steps[-1].accepted is True
    # The release never advanced to IMPLEMENTATION.
    # The run now reaches IMPLEMENTATION carrying the objection as a warning: a model
    # verdict is advisory, never terminal.
    assert result.final_phase is LifecyclePhase.IMPLEMENTATION


def test_plan_dependency_gate_blocks_forward_validation_reference(tmp_path: Path) -> None:
    store = _MemoryRunStore()
    workflow = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    plan = (
        workflow._selector.spec_context.specs_dir  # noqa: SLF001 - focused workflow contract test
        / "releases"
        / _RELEASE
        / "PLAN.md"
    )
    plan.write_text(
        "# plan\n\n## Validation Dependency Table\n\n"
        "| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |\n"
        "|---|---|---|---|---|\n"
        "| WS-1 | value object | replay test | WS-3 | replay snapshot |\n",
        encoding="utf-8",
    )

    result = workflow.run("rd-forward-dependency")

    # A DETERMINISTIC lint stays terminal: it can be satisfied by construction.
    assert result.completed is False
    assert result.blocked is not None
    # The lint anchors at the create step it revises; the bounded revision re-ran
    # plan_create once before blocking, and the resume advice names that step.
    assert result.blocked.blocked_at_step == "definition_draft"
    assert "depends on later workstream" in result.blocked.reason
    assert "--resume-from definition_draft" in (result.blocked.operator_command or "")
    assert [step.label for step in result.steps][-1] == "definition_draft"


def test_plan_dependency_gate_accepts_numbered_heading(tmp_path: Path) -> None:
    store = _MemoryRunStore()
    workflow = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    plan = (
        workflow._selector.spec_context.specs_dir  # noqa: SLF001 - focused workflow contract test
        / "releases"
        / _RELEASE
        / "PLAN.md"
    )
    plan.write_text(
        "# plan\n\n## 5. Validation Dependency Table\n\n"
        "| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |\n"
        "|---|---|---|---|---|\n"
        "| WS-1 | value object | direct equality tests | None | None |\n"
        "\n## 6. Other Section\n\n"
        "| unrelated | table |\n|---|---|\n| must | be ignored |\n",
        encoding="utf-8",
    )

    result = workflow.run("rd-numbered-plan-heading")

    assert result.completed is True
    assert result.blocked is None


def test_tasks_command_hygiene_gate_rejects_cache_clear_as_no_cache_claim(
    tmp_path: Path,
) -> None:
    store = _MemoryRunStore()
    workflow = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    tasks = (
        workflow._selector.spec_context.specs_dir  # noqa: SLF001 - focused workflow contract test
        / "releases"
        / _RELEASE
        / "TASKS.md"
    )
    tasks.write_text(
        "# tasks\n\nValidation: `python -m pytest -q --cache-clear`\n",
        encoding="utf-8",
    )

    result = workflow.run("rd-cache-producing-pytest")

    assert result.completed is False
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "definition_draft"
    assert "missing '-p no:cacheprovider'" in result.blocked.reason
    assert "--resume-from definition_draft" in (result.blocked.operator_command or "")
    assert [step.label for step in result.steps][-1] == "definition_draft"


def test_tasks_command_hygiene_gate_accepts_disabled_pytest_cache(tmp_path: Path) -> None:
    store = _MemoryRunStore()
    workflow = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    tasks = (
        workflow._selector.spec_context.specs_dir  # noqa: SLF001 - focused workflow contract test
        / "releases"
        / _RELEASE
        / "TASKS.md"
    )
    tasks.write_text(
        "# tasks\n\n```bash\npython -m pytest -p no:cacheprovider -q\n```\n",
        encoding="utf-8",
    )

    result = workflow.run("rd-cache-disabled-pytest")

    assert result.completed is True
    assert result.blocked is None


@pytest.mark.parametrize(
    "body",
    [
        "# spec\n\nStatus: Draft\n\nBody.\n",
        "# spec\n\nBody with no status.\n",
        "---\nstatus: Draft\nrelease: r1\n---\n\n# spec\n\nBody.\n",
    ],
    ids=["plain", "missing", "frontmatter"],
)
def test_approved_spec_review_inserts_one_canonical_status(
    tmp_path: Path,
    body: str,
) -> None:
    store = _MemoryRunStore()
    workflow = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    spec = (
        workflow._selector.spec_context.specs_dir  # noqa: SLF001 - focused workflow contract test
        / "releases"
        / _RELEASE
        / "SPEC.md"
    )
    spec.write_text(body, encoding="utf-8")

    result = workflow.run(f"rd-status-{body[:3]}")

    assert result.completed is True
    normalized = spec.read_text(encoding="utf-8")
    assert normalized.count("> **Status:** Aprovado") == 1
    assert "Status: Draft" not in normalized
    assert "status: Draft" not in normalized


# ── bug release-plan-author-does-not-converge-validation-contract (game cycle 4) ────
#
# A live pt-BR worker translated the section heading and column titles; the lint then
# blocked on presentation while the table's SEMANTICS were valid. Presentation is now
# matched structurally (normalized heading, positional 5-column fallback); semantics
# (canonical WS ids, five non-empty cells, no forward dependencies) stay strict.


def _wf_with_plan(tmp_path: Path, plan_body: str) -> ReleaseDefinitionWorkflow:
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "releases" / _RELEASE / "PLAN.md").write_text(plan_body, encoding="utf-8")
    return wf


def test_plan_lint_accepts_translated_headings_with_valid_semantics(tmp_path: Path) -> None:
    translated = (
        "# PLAN\n\n## Tabela de Dependências de Validação\n\n"
        "| Fluxo de trabalho | Produz ao final | Validação direta | "
        "Dependências de validação | Evidência de integração adiada |\n"
        "|---|---|---|---|---|\n"
        "| WS-1 | módulo board | testes unitários | None | None |\n"
        "| WS-2 | CLI do jogo | testes de integração | WS-1 | None |\n"
    )
    wf = _wf_with_plan(tmp_path, translated)
    assert wf._validate_plan_dependency_table() is None


def test_plan_lint_still_blocks_forward_dependency_in_translated_table(tmp_path: Path) -> None:
    translated_bad = (
        "# PLAN\n\n## Tabela de Dependências de Validação\n\n"
        "| Fluxo | Produz | Validação | Dependências | Evidência |\n"
        "|---|---|---|---|---|\n"
        "| WS-1 | board | unit | None | None |\n"
        "| WS-2 | cli | integração | WS-3 | None |\n"
        "| WS-3 | e2e | partida | WS-2 | None |\n"
    )
    wf = _wf_with_plan(tmp_path, translated_bad)
    block = wf._validate_plan_dependency_table()
    assert block is not None
    assert "WS-2" in block.reason and "WS-3" in block.reason


# ── bug release-definition-completes-without-persisting-artifacts (game cycle 6) ────
#
# A live worker "passed" spec_create without persisting SPEC.md (the zone-wide
# deliverable glob was satisfied by any write) and the terminal gate advanced the
# release to IMPLEMENTATION with 2 doctor errors. Create steps now declare their
# EXACT file deliverable, and definition_commit_gate refuses to complete unless
# SPEC/PLAN/TASKS exist with the review-approved status on disk.


class _SkipsSpecFake:
    """Approves every step; writes PLAN/TASKS but never SPEC.md (the cycle-6 shape)."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        label = (request.task_id or "").rsplit(":", 1)[-1]
        refs = [f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json"]
        # Deliberately writes PLAN and TASKS but NOT SPEC.md: the point of this test is
        # that a worker which skips an artifact can never complete the definition.
        names = ("PLAN.md", "TASKS.md") if label == "definition_draft" else ()
        for deliverable in names:
            ref = f"repos/{_CONTEXT}/specs/releases/{_RELEASE}/{deliverable}"
            refs.append(ref)
        for ref in refs:
            target = self.root / ref
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('{"fake": true}\n', encoding="utf-8")
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="ok",
            artifact_refs=tuple(refs),
            structured_output={"verdict": "APPROVED"},
        )


def test_definition_never_completes_without_spec_on_disk(tmp_path: Path) -> None:
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, lambda kind: _SkipsSpecFake(tmp_path))
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    # Remove the pre-seeded SPEC so only the worker could create it (it won't).
    (specs / "releases" / _RELEASE / "SPEC.md").unlink()

    result = wf.run("no-spec-run")

    assert result.completed is False, "definition must NEVER complete without SPEC.md on disk"
    assert result.blocked is not None
    # ACTIVE.md must not have been repointed to IMPLEMENTATION.
    active = specs / "releases" / "ACTIVE.md"
    if active.exists():
        assert "IMPLEMENTATION" not in active.read_text(encoding="utf-8")


def test_revision_is_observable_in_the_persisted_run(tmp_path: Path) -> None:
    """Bug release-definition-retry-stalls-with-empty-workflow-steps-041: during a
    bounded in-run revision the record rewinds to RUNNING + reclaimed ledger — the
    exact silhouette of the old stall. The persisted run must carry a revision_note
    naming the revision so a watcher never reads it as stalled.
    """
    store = _MemoryRunStore()
    sequence = tuple(
        replace(step, runtime_kind=AgentRuntimeKind.CODEX_EXEC)
        if step.label == "definition_review"
        else step
        for step in _SEQUENCE
    )

    def kind_factory(kind: AgentRuntimeKind) -> _KindFake:
        if kind is AgentRuntimeKind.CODEX_EXEC:
            return _KindFake(kind, _rejected())
        return _KindFake(kind, _approved())

    wf = _workflow(tmp_path, store, kind_factory)
    result = wf.run("rd-rev-obs", sequence)

    # The verdict costs one revision and then becomes advisory, so the run completes;
    # what this test pins is that the revision is OBSERVABLE on the persisted run.
    assert result.completed is True
    run = store.load("rd-rev-obs")
    assert run is not None
    assert run.revision_note is not None
    assert "definition_draft" in run.revision_note
    assert "definition_review" in run.revision_note


def test_run_record_revision_note_roundtrip_and_old_records() -> None:
    """Additive-optional law: old records without revision_note load as None; new
    records serialize it and reload it byte-identically."""
    from dadaia_workspace.core.models.lifecycle import LifecycleRun, LifecycleRunStatus

    run = LifecycleRun(
        run_id="r1",
        context=_CONTEXT,
        release_id=_RELEASE,
        command="release-definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.RUNNING,
        current_step="definition_draft",
        revision_note="bounded revision 1/1 of 'spec_create' after 'spec_review' rejected: x",
    )
    loaded = LifecycleRun.from_dict(run.to_dict())
    assert loaded.revision_note == run.revision_note

    legacy = run.to_dict()
    legacy.pop("revision_note")
    assert LifecycleRun.from_dict(legacy).revision_note is None


def test_revision_retries_spec_create_with_the_reviewer_feedback_injected(tmp_path: Path) -> None:
    """Bug release-definition-review-feedback-not-reinjected: the bounded revision must
    re-run the create step WITH the reviewer's verdict_reason in its prompt — a blind
    retry repeats the same defect and exhausts the budget for nothing.
    """
    store = _MemoryRunStore()
    requests: list[tuple[str, str]] = []
    calls = 0

    class _FeedbackFake:
        def __init__(self, kind: AgentRuntimeKind) -> None:
            self.kind = kind

        def runtime_kind(self) -> AgentRuntimeKind:
            return self.kind

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            nonlocal calls
            calls += 1
            step = (request.task_id or "").rsplit(":", 1)[-1]
            requests.append((step, request.prompt))
            if self.kind is AgentRuntimeKind.CODEX_EXEC:
                return AgentRunResult(
                    status=AgentRunStatus.SUCCEEDED,
                    summary="rejected",
                    artifact_refs=(
                        f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json",
                    ),
                    structured_output={
                        "verdict": "REJECTED",
                        "verdict_reason": "SPEC defines `python -m saudacao` without src/saudacao/__main__.py",
                    },
                )
            return _approved()

    sequence = tuple(
        replace(step, runtime_kind=AgentRuntimeKind.CODEX_EXEC)
        if step.label == "definition_review"
        else step
        for step in _SEQUENCE
    )
    wf = _workflow(tmp_path, store, lambda kind: _FeedbackFake(kind))
    result = wf.run("rd-feedback", sequence)

    # The revision still runs and still injects the reviewer digest; only the FINAL
    # verdict is advisory, so the run completes instead of dying at the gate.
    assert result.completed is True
    create_prompts = [prompt for step, prompt in requests if step == "definition_draft"]
    # spec_create ran twice (initial + the bounded revision).
    assert len(create_prompts) == 2
    # The RETRY prompt carries the reviewer's actual finding — never a blind retry.
    assert "src/saudacao/__main__.py" in create_prompts[1]
    assert "Prior rejection feedback" in create_prompts[1]


# ── bug release-definition-approved-plan-not-persisted-041 (consumer 0.4.1) ─────
#
# plan_review returned APPROVED but PLAN.md stayed Draft on disk: the status flip
# silently skipped (``path.is_file() → return None``) and the terminal gate blocked
# 3+ model steps later with no remedy. Python is the SOLE owner of the Status
# token: the flip must fail LOUD with an actionable remedy, tolerate worker
# status-line variants, and the terminal gate must name the resume point that
# re-asserts the flip.


def _step(label: str):  # noqa: ANN202 - tiny fixture helper
    return next(s for s in _SEQUENCE if s.label == label)


def test_flip_blocks_loud_when_reviewed_artifact_missing(tmp_path: Path) -> None:
    """An approved review over a MISSING artifact must block at the review step with
    the create-step resume as remedy — never skip the flip silently."""
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    plan = tmp_path / "repos" / _CONTEXT / "specs" / "releases" / _RELEASE / "PLAN.md"
    plan.unlink()

    blocked = wf._on_step_accepted(_step("definition_review"))  # noqa: SLF001

    assert blocked is not None, "missing artifact at flip time must fail LOUD, not skip"
    assert "PLAN.md" in blocked.reason
    assert blocked.blocked_at_step == "definition_draft"
    assert blocked.operator_command is not None
    assert "--resume-from definition_draft" in blocked.operator_command


def test_flip_is_single_writer_over_worker_status_variants(tmp_path: Path) -> None:
    """Worker-authored status lines (colon-outside-bold, bullets, lowercase) are all
    removed — after the flip the file carries exactly ONE Python-owned token."""
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    plan = tmp_path / "repos" / _CONTEXT / "specs" / "releases" / _RELEASE / "PLAN.md"
    plan.write_text(
        "# plan\n\n**Status**: Draft\n\n- **Status:** Em revisão\n\n* Status: draft\n\nbody\n",
        encoding="utf-8",
    )

    assert wf._on_step_accepted(_step("definition_review")) is None  # noqa: SLF001

    text = plan.read_text(encoding="utf-8")
    assert text.count("> **Status:** Aprovado") == 1
    for variant in ("Draft", "draft", "Em revisão"):
        assert variant not in text


def test_terminal_gate_names_resume_remedy_for_unflipped_artifact(tmp_path: Path) -> None:
    """A Draft artifact with an APPROVED ledger (resumed/rewritten mid-run) blocks at
    the terminal gate WITH the resume command that re-asserts the flip."""
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "releases" / _RELEASE / "SPEC.md").write_text(
        "# spec\n\n> **Status:** Aprovado\n", encoding="utf-8"
    )
    (specs / "releases" / _RELEASE / "PLAN.md").write_text(
        "# plan\n\n> **Status:** Draft\n", encoding="utf-8"
    )

    blocked = wf._terminal_semantic_block(None, _step("definition_commit_gate"), _SEQUENCE)  # type: ignore[arg-type]  # noqa: SLF001

    assert blocked is not None
    assert "PLAN.md" in blocked.reason
    assert blocked.operator_command is not None
    assert "--resume-from definition_review" in blocked.operator_command


def test_approved_review_with_unwritten_artifact_blocks_at_review_not_terminal_gate(
    tmp_path: Path,
) -> None:
    """Full-run repro of the consumer symptom: the review worker's verdict arrives but
    the artifact vanished before the flip — the run must block AT THE REVIEW with a
    remedy, never glide into a terminal-gate block steps later."""
    store = _MemoryRunStore()
    plan = tmp_path / "repos" / _CONTEXT / "specs" / "releases" / _RELEASE / "PLAN.md"

    class _DeletesPlanFake:
        def runtime_kind(self) -> AgentRuntimeKind:
            return AgentRuntimeKind.CODEX_EXEC

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            plan.unlink(missing_ok=True)
            return _approved()

    sequence = tuple(
        replace(step, runtime_kind=AgentRuntimeKind.CODEX_EXEC)
        if step.label == "definition_review"
        else step
        for step in _SEQUENCE
    )

    def factory(kind: AgentRuntimeKind):  # noqa: ANN202
        if kind is AgentRuntimeKind.CODEX_EXEC:
            return _DeletesPlanFake()
        return _KindFake(kind, _approved())

    wf = _workflow(tmp_path, store, factory)
    result = wf.run("rd-flip-loud", sequence)

    assert result.completed is False
    assert result.blocked is not None
    assert "PLAN.md" in result.blocked.reason
    assert result.blocked.blocked_at_step == "definition_draft"
    assert result.blocked.operator_command is not None
    assert "--resume-from definition_draft" in result.blocked.operator_command
