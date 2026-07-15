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
    with_finding: bool = False
    drop_disposition: bool = False
    artifact_only_scope: bool = False

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        step = (request.task_id or "").rsplit(":", 1)[-1]
        artifact_ref = f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/{step}.step-output.json"
        if step == "audit_scope" and self.artifact_only_scope:
            payload: dict[str, object] = {
                "schema": "agent-run-result-v1",
                "artifact_refs": [artifact_ref],
            }
        elif step == "audit_scope":
            payload = {
                "summary": "Bound architecture drift.",
                "audit_question": "Does implementation match architecture memory?",
                "lenses": [{"name": "architecture", "rationale": "Contract fidelity."}],
                "surfaces": ["src/games.py"],
                "acceptance_criteria": [
                    {"lens": "architecture", "pass_condition": "No contract drift."}
                ],
            }
        elif step == "drift_scan":
            payload = {
                "summary": "One drift found." if self.with_finding else "No drift found.",
                "verdict": "REJECTED" if self.with_finding else "APPROVED",
                "verdict_reason": (
                    "Implementation differs from memory."
                    if self.with_finding
                    else "Every scoped lens passed."
                ),
                "lens_results": [
                    {
                        "lens": "architecture",
                        "status": "FAIL" if self.with_finding else "PASS",
                        "evidence": ["src/games.py:1"],
                    }
                ],
                "findings": (
                    [
                        {
                            "id": "architecture-drift",
                            "severity": "HIGH",
                            "message": "Implementation differs from memory.",
                            "surface": "src/games.py",
                            "evidence": "src/games.py:1",
                        }
                    ]
                    if self.with_finding
                    else []
                ),
            }
        else:
            payload = {
                "summary": "Routed audit findings.",
                "source_verdict": "REJECTED" if self.with_finding else "APPROVED",
                "dispositions": (
                    []
                    if self.drop_disposition or not self.with_finding
                    else [
                        {
                            "finding_id": "architecture-drift",
                            "disposition": "bug",
                            "route": "specs/bugs via dadaia bugs append",
                            "severity": "HIGH",
                            "evidence": "src/games.py:1",
                        }
                    ]
                ),
            }
        verdict = payload.get("verdict")
        structured: dict[str, str] = {"verdict": verdict} if isinstance(verdict, str) else {}
        if isinstance(payload.get("verdict_reason"), str):
            structured["verdict_reason"] = payload["verdict_reason"]
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=str(payload.get("summary", step)),
            artifact_refs=(artifact_ref,),
            structured_output=structured,
            domain_payload=payload,
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


def _workflow(
    tmp_path: Path,
    resolver: WorkflowHandoffResolver | None,
    *,
    with_finding: bool = False,
    drop_disposition: bool = False,
    artifact_only_scope: bool = False,
) -> AuditWorkflow:
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
        runtime_factory=lambda kind: _KindFake(
            kind,
            with_finding=with_finding,
            drop_disposition=drop_disposition,
            artifact_only_scope=artifact_only_scope,
        ),  # type: ignore[arg-type]
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


def test_artifact_only_scope_blocks_as_malformed_domain_output(tmp_path: Path) -> None:
    _workspace(tmp_path)
    result = _workflow(tmp_path, _resolver(tmp_path), artifact_only_scope=True).run(
        "aud-empty-scope"
    )

    assert not result.completed
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "audit_scope"
    assert "audit-scope-handoff-v1" in result.blocked.reason


def test_rejected_drift_is_triaged_and_can_complete(tmp_path: Path) -> None:
    _workspace(tmp_path)
    result = _workflow(tmp_path, _resolver(tmp_path), with_finding=True).run("aud-rejected")

    assert result.completed
    assert [step.label for step in result.steps] == [
        "audit_scope",
        "drift_scan",
        "triage",
        "audit_disposition_gate",
    ]


def test_disposition_gate_blocks_an_undisposed_finding(tmp_path: Path) -> None:
    _workspace(tmp_path)
    result = _workflow(
        tmp_path,
        _resolver(tmp_path),
        with_finding=True,
        drop_disposition=True,
    ).run("aud-undisposed")

    assert not result.completed
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "audit_disposition_gate"
    assert "dispose every finding" in result.blocked.detail["violations"]
