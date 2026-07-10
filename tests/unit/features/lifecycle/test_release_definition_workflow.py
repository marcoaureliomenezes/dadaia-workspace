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
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _rejected() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="rejected",
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/step.handoff.json",),
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
    (specs / "releases" / _RELEASE / "PLAN.md").write_text("# plan\n", encoding="utf-8")
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
