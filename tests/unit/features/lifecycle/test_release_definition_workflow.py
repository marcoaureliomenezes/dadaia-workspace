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
        if step.label == "spec_review"
        else step
        for step in _SEQUENCE
    )

    def kind_factory(kind: AgentRuntimeKind) -> _KindFake:
        if kind is AgentRuntimeKind.CODEX_EXEC:
            return _KindFake(kind, _rejected())
        return _KindFake(kind, _approved())

    wf = _workflow(tmp_path, store, kind_factory)
    result = wf.run("rd-3", sequence)

    assert result.completed is False
    assert result.final_phase is LifecyclePhase.BLOCKED
    assert result.blocked is not None
    # The sequence stopped at the rejected review — the commit gate never ran.
    labels = [s.label for s in result.steps]
    assert labels[-1] == "spec_review"
    assert "definition_commit_gate" not in labels
    assert result.steps[-1].accepted is False
    # The release never advanced to IMPLEMENTATION.
    assert result.final_phase is not LifecyclePhase.IMPLEMENTATION


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

    assert result.completed is False
    assert result.blocked is not None
    # The lint anchors at the create step it revises; the bounded revision re-ran
    # plan_create once before blocking, and the resume advice names that step.
    assert result.blocked.blocked_at_step == "plan_create"
    assert "depends on later workstream" in result.blocked.reason
    assert "--resume-from plan_create" in (result.blocked.operator_command or "")
    assert [step.label for step in result.steps][-1] == "plan_create"


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
    assert result.blocked.blocked_at_step == "tasks_create"
    assert "missing '-p no:cacheprovider'" in result.blocked.reason
    assert "--resume-from tasks_create" in (result.blocked.operator_command or "")
    assert [step.label for step in result.steps][-1] == "tasks_create"


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
        deliverable = {"plan_create": "PLAN.md", "tasks_create": "TASKS.md"}.get(label)
        if deliverable is not None:
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
        if step.label == "spec_review"
        else step
        for step in _SEQUENCE
    )

    def kind_factory(kind: AgentRuntimeKind) -> _KindFake:
        if kind is AgentRuntimeKind.CODEX_EXEC:
            return _KindFake(kind, _rejected())
        return _KindFake(kind, _approved())

    wf = _workflow(tmp_path, store, kind_factory)
    result = wf.run("rd-rev-obs", sequence)

    assert result.completed is False
    run = store.load("rd-rev-obs")
    assert run is not None
    assert run.revision_note is not None
    assert "spec_create" in run.revision_note
    assert "spec_review" in run.revision_note


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
        current_step="spec_create",
        revision_note="bounded revision 1/1 of 'spec_create' after 'spec_review' rejected: x",
    )
    loaded = LifecycleRun.from_dict(run.to_dict())
    assert loaded.revision_note == run.revision_note

    legacy = run.to_dict()
    legacy.pop("revision_note")
    assert LifecycleRun.from_dict(legacy).revision_note is None
