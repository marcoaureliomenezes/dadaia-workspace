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

    # Run the first review step (spec_arch_review) on a distinct harness kind so the
    # factory can return a REJECTED verdict for exactly that step while every other step
    # (the create steps) approves. Python — not the model — decides this blocks.
    sequence = tuple(
        replace(step, runtime_kind=AgentRuntimeKind.CODEX_EXEC)
        if step.label == "spec_arch_review"
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
    assert labels[-1] == "spec_arch_review"
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
    assert result.blocked.blocked_at_step == "plan_dependency_gate"
    assert "depends on later workstream" in result.blocked.reason
    assert [step.label for step in result.steps][-2:] == [
        "plan_create",
        "plan_dependency_gate",
    ]


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
    assert result.blocked.blocked_at_step == "tasks_command_hygiene_gate"
    assert "missing '-p no:cacheprovider'" in result.blocked.reason
    assert [step.label for step in result.steps][-2:] == [
        "tasks_create",
        "tasks_command_hygiene_gate",
    ]


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
