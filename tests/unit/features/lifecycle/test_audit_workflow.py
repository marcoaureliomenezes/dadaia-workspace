"""Audit workflow-specific behavior beyond the shared suite (collapsed single-step body).

The shared e2e-completion / block-on-missing / no-resolver behaviors are covered
generically for this workflow in ``test_fragment_workflow_bodies.py``. This file keeps
only what is audit-specific: the terminal disposition gate's REFERENTIAL-INTEGRITY
branch (every finding routed exactly once; no phantom disposition; a copy mismatch can
no longer exist because Python derives severity/lens by finding id), routed findings
completing the run, and ``resume_from`` after a block.
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
from dadaia_workspace.features.lifecycle.workflows.audit import _SEQUENCE, AuditWorkflow
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.30"


def _report_payload(
    *, with_finding: bool = False, drop_disposition: bool = False, phantom: bool = False
) -> dict[str, object]:
    findings: list[dict[str, object]] = []
    dispositions: list[dict[str, object]] = []
    if with_finding:
        findings.append(
            {
                "id": "architecture-drift",
                "severity": "HIGH",
                "lens": "architecture",
                "summary": "Implementation differs from memory.",
                "evidence": "src/games.py:1",
            }
        )
        if not drop_disposition:
            dispositions.append(
                {
                    "finding_id": "architecture-drift",
                    "route": "bug",
                    "reason": "Real contract violation; file additively.",
                }
            )
    if phantom:
        dispositions.append(
            {
                "finding_id": "ghost-finding",
                "route": "backlog",
                "reason": "References a finding that does not exist.",
            }
        )
    return {
        "summary": "One drift found." if with_finding else "No drift found.",
        "question": "Does implementation match architecture memory?",
        "lenses": ["architecture"],
        "findings": findings,
        "dispositions": dispositions,
    }


@dataclass(frozen=True)
class _ReportFake:
    kind: AgentRuntimeKind
    with_finding: bool = False
    drop_disposition: bool = False
    phantom: bool = False

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        step = (request.task_id or "").rsplit(":", 1)[-1]
        artifact_ref = f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/{step}.step-output.json"
        payload = _report_payload(
            with_finding=self.with_finding,
            drop_disposition=self.drop_disposition,
            phantom=self.phantom,
        )
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=str(payload["summary"]),
            artifact_refs=(artifact_ref,),
            structured_output={},
            domain_payload=payload,
        )


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory").mkdir(parents=True)
    (specs / "bugs").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# c\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text("# a\n", encoding="utf-8")
    return tmp_path


def _selector(tmp_path: Path) -> ContextSelector:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    return ContextSelector(
        SpecContext(
            specs_dir=specs,
            release_id=_RELEASE,
            handoff_dir=tmp_path / ".dadaia" / "handoff",
        )
    )


def _resolver(tmp_path: Path) -> WorkflowHandoffResolver:
    return WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-14T12:00:00Z",
    )


def _workflow(tmp_path: Path, fake: object) -> AuditWorkflow:
    _workspace(tmp_path)
    return AuditWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=_selector(tmp_path),
        handoff_resolver=_resolver(tmp_path),
    )


def test_single_step_happy_path_completes_and_persists_release_zone_payload(
    tmp_path: Path,
) -> None:
    wf = _workflow(tmp_path, _ReportFake(AgentRuntimeKind.FAKE))

    result = wf.run("audit-one")

    assert result.completed is True
    assert [s.label for s in result.steps] == ["audit_report", "audit_disposition_gate"]
    run = JsonLifecycleRunStore(tmp_path).load("audit-one")
    assert run is not None
    record = run.workflow_steps.find("audit_report", 0)
    assert record is not None
    # Operator mandate: the payload lands in the release folder, not under .dadaia.
    assert record.payload_ref.startswith(
        f"repos/{_CONTEXT}/specs/releases/{_RELEASE}/handoffs/audit-one/steps/"
    )
    assert (tmp_path / record.payload_ref).is_file()


def test_routed_finding_completes_without_byte_copy_ceremony(tmp_path: Path) -> None:
    """A finding routed to ``bug`` completes — the disposition carries no severity copy
    for Python to re-verify; severity lives on the finding only."""
    wf = _workflow(tmp_path, _ReportFake(AgentRuntimeKind.FAKE, with_finding=True))

    result = wf.run("audit-routed")

    assert result.completed is True
    assert result.blocked is None


def test_undisposed_finding_blocks_with_precise_reason(tmp_path: Path) -> None:
    wf = _workflow(
        tmp_path,
        _ReportFake(AgentRuntimeKind.FAKE, with_finding=True, drop_disposition=True),
    )

    result = wf.run("audit-undisposed")

    assert result.completed is False
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "audit_disposition_gate"
    assert "architecture-drift" in result.blocked.detail.get("violations", "")


def test_phantom_disposition_blocks(tmp_path: Path) -> None:
    wf = _workflow(tmp_path, _ReportFake(AgentRuntimeKind.FAKE, phantom=True))

    result = wf.run("audit-phantom")

    assert result.completed is False
    assert result.blocked is not None
    assert "ghost-finding" in result.blocked.detail.get("violations", "")


class _FlippableFake:
    """Drops the disposition until flipped — drives the block-then-resume path."""

    def __init__(self) -> None:
        self.drop_disposition = True

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        step = (request.task_id or "").rsplit(":", 1)[-1]
        artifact_ref = f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/{step}.step-output.json"
        payload = _report_payload(with_finding=True, drop_disposition=self.drop_disposition)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=str(payload["summary"]),
            artifact_refs=(artifact_ref,),
            structured_output={},
            domain_payload=payload,
        )


def test_resume_from_reruns_the_report_step_after_a_block(tmp_path: Path) -> None:
    fake = _FlippableFake()
    wf = _workflow(tmp_path, fake)

    first = wf.run("audit-resume")
    assert first.completed is False

    fake.drop_disposition = False
    resumed = wf.run("audit-resume", resume_from="audit_report")
    assert resumed.completed is True
    assert resumed.final_phase is LifecyclePhase.QA_REVIEW


def test_sequence_shape_is_one_model_step_plus_python_gate() -> None:
    labels = [(s.label, s.fragment_id) for s in _SEQUENCE]
    assert labels == [
        ("audit_report", "audit.audit_report"),
        ("audit_disposition_gate", None),
    ]


def test_build_audit_workflow_rejects_undefined_release_id(tmp_path: Path) -> None:
    """Bug audit-accepts-undefined-release-and-creates-release-tree: `lifecycle audit`
    with a release id that has no `specs/releases/<id>/` directory must be rejected
    BEFORE the run, so it never synthesizes a bogus release tree by writing its
    handoff step-payload under `specs/releases/<bogus>/handoffs/`. The audit runs
    against an EXISTING release (the happy-path test pre-creates releases/<id>)."""
    import pytest

    from dadaia_workspace import container
    from dadaia_workspace.core.exceptions import ReleaseNotFoundError

    _workspace(tmp_path)  # creates releases/v0.1.30 only
    specs = tmp_path / "repos" / _CONTEXT / "specs"

    # An existing release builds fine.
    container.build_audit_workflow(tmp_path, context=_CONTEXT, release_id=_RELEASE)

    # A release id with no directory is rejected, and nothing is synthesized.
    bogus = "canary-does-not-exist-20260716"
    with pytest.raises(ReleaseNotFoundError):
        container.build_audit_workflow(tmp_path, context=_CONTEXT, release_id=bogus)
    assert not (specs / "releases" / bogus).exists(), "audit must not create a bogus release dir"
