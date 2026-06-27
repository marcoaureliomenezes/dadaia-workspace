"""Research workflow body × fragment+gate engine + Wave-D ledger (v0.1.30 / T-30-E-02).

A fake research run wired with a real ``WorkflowHandoffResolver`` (real run store + real
filesystem step-payload writer under ``tmp_path``) exercises the body end-to-end: role →
fragments → dynamic selector → output schema → Python gate, proving it consumes the
Wave-D ledger (an upstream payload is consumed by a downstream step; a missing required
one BLOCKS).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
)
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.features.lifecycle.workflows.research import (
    _SEQUENCE,
    ResearchStep,
    ResearchWorkflow,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.30"


@dataclass(frozen=True)
class _KindFake:
    kind: AgentRuntimeKind
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return self.result


def _approved() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="research step ok",
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    (tmp_path / "dadaia_workspace").mkdir()  # source-map / source-summary root
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# c\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text("# a\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    return tmp_path


def _resolver(tmp_path: Path) -> WorkflowHandoffResolver:
    return WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-06-27T12:00:00Z",
    )


def _workflow(tmp_path: Path, resolver: WorkflowHandoffResolver | None) -> ResearchWorkflow:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )
    return ResearchWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _KindFake(kind, _approved()),  # type: ignore[arg-type]
        context_selector=selector,
        handoff_resolver=resolver,
    )


# --- A28: the body runs as a real fragment+gate workflow, no NotImplementedError ----


def test_research_body_runs_end_to_end_on_fake_runtime(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))

    result = wf.run("res-run")  # must not raise NotImplementedError

    assert result.completed is True
    labels = [s.label for s in result.steps]
    assert labels == ["research_scope", "investigate", "synthesis", "research_synthesis_gate"]
    assert result.steps[-1].is_gate is True


def test_research_body_records_injected_fragments_and_context(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))
    wf.run("res-audit")

    run = JsonLifecycleRunStore(tmp_path).load("res-audit")
    assert run is not None
    by_step = {ic.step: ic for ic in run.injected_context}
    assert "research.research_scope" in by_step["research_scope"].fragment_ids
    assert "research.investigate" in by_step["investigate"].fragment_ids
    assert "research.synthesis" in by_step["synthesis"].fragment_ids


# --- ledger consume: investigate consumes the exact research_scope payload -----------


def test_investigate_consumes_exact_research_scope_payload(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))
    wf.run("res-consume")

    run = JsonLifecycleRunStore(tmp_path).load("res-consume")
    assert run is not None
    scope_record = run.workflow_steps.find("research_scope", 0)
    assert scope_record is not None
    consumers = {(c.consumer_step, c.consumer_attempt) for c in scope_record.consumptions}
    assert ("investigate", 0) in consumers


# --- ledger BLOCK-on-missing: a missing required upstream BLOCKS --------------------


def test_missing_required_upstream_blocks_research(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))

    broken = (
        ResearchStep(
            label="investigate",
            role="software-architect",
            fragment_id="research.investigate",
            produces="research-findings-handoff-v1",
            consumes=("research_scope",),  # research_scope never produced in this sequence
        ),
        ResearchStep(label="research_synthesis_gate", role="python", fragment_id=None),
    )
    result = wf.run("res-block", sequence=broken)

    assert result.completed is False
    assert result.final_phase is LifecyclePhase.BLOCKED
    assert result.blocked is not None
    assert "required upstream handoff unavailable" in result.blocked.reason


# --- back-compat: no resolver wired => still runs, no ledger ------------------------


def test_research_without_resolver_runs_and_writes_no_ledger(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, resolver=None)

    result = wf.run("res-nores")

    assert result.completed is True
    run = JsonLifecycleRunStore(tmp_path).load("res-nores")
    assert run is not None
    assert len(run.workflow_steps) == 0
    assert [s.label for s in _SEQUENCE if s.produces][0] == "research_scope"
