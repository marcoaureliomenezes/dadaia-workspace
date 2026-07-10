"""Audit workflow-specific behavior beyond the shared suite (v0.1.30 / T-30-E-01).

The shared e2e-completion / exact-consumption / block-on-missing / no-resolver behaviors are
covered generically for this workflow in ``test_fragment_workflow_bodies.py``. This file keeps
only what is audit-specific: the terminal gate's graph-completeness BLOCK branch (proving the
advance-vs-block gate logic, not just the upstream-resolve block path — and degrading to a
no-op with no resolver wired), and A29's disposition-ready ``triage`` output schema.
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
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.features.lifecycle.workflows.audit import _SEQUENCE, AuditWorkflow
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
        summary="audit step ok",
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
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


def _workflow(tmp_path: Path, resolver: WorkflowHandoffResolver | None) -> AuditWorkflow:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )
    return AuditWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _KindFake(kind, _approved()),  # type: ignore[arg-type]
        context_selector=selector,
        handoff_resolver=resolver,
    )


def test_audit_disposition_gate_blocks_on_incomplete_handoff_graph(tmp_path: Path) -> None:
    """The terminal gate's graph-completeness BLOCK branch (A26/A28): a run that reached the
    gate un-blocked but whose ledger is missing a declared producer edge must BLOCK — proves
    the advance-vs-block gate logic, not just the upstream-resolve block path."""
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))
    gate_step = _SEQUENCE[-1]
    # blocked is None (no prior gate fired) but workflow_steps is empty: the producing
    # steps declared `produces` yet wrote no ledger payload → graph incomplete.
    run = LifecycleRun(
        run_id="aud-incomplete",
        context=_CONTEXT,
        release_id=_RELEASE,
        command="audit",
        phase=LifecyclePhase.QA_REVIEW,
        status=LifecycleRunStatus.RUNNING,
        current_step="triage",
        blocked=None,
    )
    # v0.1.57 FR1: the base iterates the RUN-SCOPED sequence (threaded), never a module-global.
    block = wf._graph_completeness_block(run, gate_step, _SEQUENCE)
    assert block is not None
    assert "graph incomplete" in block.reason
    # And with no resolver wired, the gate degrades to a no-op (no ledger to check).
    wf_no_resolver = _workflow(tmp_path, None)
    assert wf_no_resolver._graph_completeness_block(run, gate_step, _SEQUENCE) is None


def test_triage_produces_disposition_ready_output(tmp_path: Path) -> None:
    """A29 — the ``triage`` step produces disposition-ready output (``audit-disposition-handoff-v1``)."""
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))
    wf.run("aud-disp")

    run = JsonLifecycleRunStore(tmp_path).load("aud-disp")
    assert run is not None
    triage_record = run.workflow_steps.find("triage", 0)
    assert triage_record is not None
    assert triage_record.output_schema == "audit-disposition-handoff-v1"
    assert (tmp_path / triage_record.payload_ref).is_file()
