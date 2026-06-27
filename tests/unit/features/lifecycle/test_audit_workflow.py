"""Audit workflow body × fragment+gate engine + Wave-D ledger (v0.1.30 / T-30-E-01).

A fake audit run wired with a real ``WorkflowHandoffResolver`` (real run store + real
filesystem step-payload writer under ``tmp_path``) exercises the body end-to-end:

- A28 — the body runs as a real fragment+gate workflow (no ``NotImplementedError``);
  each model step records injected fragments + dynamic context for auditability; the
  terminal Python gate completes the run.
- A29 — the ``triage`` step produces disposition-ready output (``audit-disposition-handoff-v1``).
- Ledger CONSUME — ``drift_scan`` consumes the exact ``audit_scope`` payload by
  (run, step, attempt); a missing required upstream BLOCKS before the prompt runs.
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
from dadaia_workspace.features.lifecycle.workflows.audit import (
    _SEQUENCE,
    AuditStep,
    AuditWorkflow,
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


# --- A28: the body runs as a real fragment+gate workflow, no NotImplementedError ----


def test_audit_body_runs_end_to_end_on_fake_runtime(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))

    result = wf.run("aud-run")  # must not raise NotImplementedError

    assert result.completed is True
    # role → fragments → selector → output schema → Python gate, all four model+gate steps.
    labels = [s.label for s in result.steps]
    assert labels == ["audit_scope", "drift_scan", "triage", "audit_disposition_gate"]
    assert result.steps[-1].is_gate is True


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
    block = wf._graph_completeness_block(run, gate_step)
    assert block is not None
    assert "graph incomplete" in block.reason
    # And with no resolver wired, the gate degrades to a no-op (no ledger to check).
    wf_no_resolver = _workflow(tmp_path, None)
    assert wf_no_resolver._graph_completeness_block(run, gate_step) is None


def test_audit_body_records_injected_fragments_and_context(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))
    wf.run("aud-audit")

    run = JsonLifecycleRunStore(tmp_path).load("aud-audit")
    assert run is not None
    # Each model step recorded its fragment ids (auditability / L4).
    by_step = {ic.step: ic for ic in run.injected_context}
    assert "audit.audit_scope" in by_step["audit_scope"].fragment_ids
    assert "audit.drift_scan" in by_step["drift_scan"].fragment_ids
    assert "audit.triage" in by_step["triage"].fragment_ids


# --- A29: triage produces disposition-ready output ---------------------------------


def test_triage_produces_disposition_ready_output(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))
    wf.run("aud-disp")

    run = JsonLifecycleRunStore(tmp_path).load("aud-disp")
    assert run is not None
    triage_record = run.workflow_steps.find("triage", 0)
    assert triage_record is not None
    assert triage_record.output_schema == "audit-disposition-handoff-v1"
    assert (tmp_path / triage_record.payload_ref).is_file()


# --- ledger consume: drift_scan consumes the exact audit_scope payload --------------


def test_drift_scan_consumes_exact_audit_scope_payload(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))
    wf.run("aud-consume")

    run = JsonLifecycleRunStore(tmp_path).load("aud-consume")
    assert run is not None
    scope_record = run.workflow_steps.find("audit_scope", 0)
    assert scope_record is not None
    consumers = {(c.consumer_step, c.consumer_attempt) for c in scope_record.consumptions}
    assert ("drift_scan", 0) in consumers


# --- ledger BLOCK-on-missing: a missing required upstream BLOCKS --------------------


def test_missing_required_upstream_blocks_audit(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))

    broken = (
        AuditStep(
            label="drift_scan",
            role="project-auditor",
            fragment_id="audit.drift_scan",
            is_review=True,
            produces="audit-findings-handoff-v1",
            consumes=("audit_scope",),  # audit_scope never produced in this sequence
        ),
        AuditStep(label="audit_disposition_gate", role="python", fragment_id=None),
    )
    result = wf.run("aud-block", sequence=broken)

    assert result.completed is False
    assert result.final_phase is LifecyclePhase.BLOCKED
    assert result.blocked is not None
    assert "required upstream handoff unavailable" in result.blocked.reason


# --- back-compat: no resolver wired => still runs, no ledger ------------------------


def test_audit_without_resolver_runs_and_writes_no_ledger(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, resolver=None)

    result = wf.run("aud-nores")

    assert result.completed is True
    run = JsonLifecycleRunStore(tmp_path).load("aud-nores")
    assert run is not None
    assert len(run.workflow_steps) == 0
    # Sanity: the deferred stub is gone — every producing step exists in the sequence.
    assert [s.label for s in _SEQUENCE if s.produces][0] == "audit_scope"
