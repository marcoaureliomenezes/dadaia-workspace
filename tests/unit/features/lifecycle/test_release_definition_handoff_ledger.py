"""Release-definition × workflow-step handoff ledger integration (v0.1.30 / T-30-D-05).

A fake release-definition run wired with a real ``WorkflowHandoffResolver`` (real run
store + real filesystem step-payload writer under ``tmp_path``) exercises the data-plane
edges end-to-end:

- A18 — every producing step writes one immutable payload artifact under
  ``.dadaia/runs/lifecycle/<run_id>/steps/`` and records a ledger entry.
- A19/A25 — ``spec_create`` consumes the EXACT ``release_scope`` payload by (run, step,
  attempt); consumption is recorded against the producer's ledger record.
- A20 — a missing/malformed required upstream BLOCKS the step before its prompt runs.
- A22 — consumption transitions are recorded; the terminal gate validates graph
  completeness.
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
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    _SEQUENCE,
    ReleaseDefinitionWorkflow,
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
        summary="step ok",
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
    (specs / "memory" / "quality-assurance.md").write_text("# q\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    for art in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (specs / "releases" / _RELEASE / art).write_text(f"# {art}\n", encoding="utf-8")
    return tmp_path


def _resolver(tmp_path: Path) -> WorkflowHandoffResolver:
    return WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-06-27T12:00:00Z",
    )


def _workflow(
    tmp_path: Path, resolver: WorkflowHandoffResolver | None
) -> ReleaseDefinitionWorkflow:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )
    return ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _KindFake(kind, _approved()),  # type: ignore[arg-type]
        context_selector=selector,
        handoff_resolver=resolver,
    )


# --- A18: a producing step writes a payload artifact + ledger entry ----------------


def test_fake_run_records_ledger_and_writes_step_payload_artifacts(tmp_path: Path) -> None:
    _workspace(tmp_path)
    resolver = _resolver(tmp_path)
    wf = _workflow(tmp_path, resolver)

    result = wf.run("rd-led")

    assert result.completed is True
    assert result.final_phase is LifecyclePhase.IMPLEMENTATION

    store = JsonLifecycleRunStore(tmp_path)
    run = store.load("rd-led")
    assert run is not None
    # One ledger entry per producing model step.
    producing = [s.label for s in _SEQUENCE if s.fragment_id is not None and s.produces is not None]
    for label in producing:
        record = run.workflow_steps.find(label, 0)
        assert record is not None, f"no ledger entry for {label}"
        # The immutable payload artifact lands under the WORKSPACE-ROOT runs/lifecycle zone.
        assert record.payload_ref.startswith(".dadaia/runs/lifecycle/rd-led/steps/")
        assert (tmp_path / record.payload_ref).is_file()


# --- A19/A25: exact-by-(run, step, attempt) consumption ---------------------------


def test_spec_create_consumes_exact_release_scope_payload(tmp_path: Path) -> None:
    _workspace(tmp_path)
    resolver = _resolver(tmp_path)
    wf = _workflow(tmp_path, resolver)
    wf.run("rd-consume")

    run = JsonLifecycleRunStore(tmp_path).load("rd-consume")
    assert run is not None
    scope_record = run.workflow_steps.find("release_scope", 0)
    assert scope_record is not None
    # spec_create recorded a consumption of release_scope#0 (exact attempt, ledger key —
    # NOT a latest-handoff-by-filename lookup).
    consumers = {(c.consumer_step, c.consumer_attempt) for c in scope_record.consumptions}
    assert ("spec_create", 0) in consumers


# --- A20: a missing required upstream BLOCKS --------------------------------------


def test_missing_required_upstream_blocks_the_workflow(tmp_path: Path) -> None:
    _workspace(tmp_path)
    resolver = _resolver(tmp_path)
    wf = _workflow(tmp_path, resolver)

    # A sequence whose first model step CONSUMES a producer that never ran — the resolver
    # cannot resolve it, so the step blocks before its prompt runs.
    from dadaia_workspace.features.lifecycle.workflows.release_definition import ReleaseStep

    broken = (
        ReleaseStep(
            label="spec_create",
            role="product-engineer",
            fragment_id="release_definition.spec_create",
            shared_fragment_ids=("shared.output_handoff",),
            produces="generic-step-handoff-v1",
            consumes=("release_scope",),  # release_scope never produced in this sequence
        ),
        ReleaseStep(label="definition_commit_gate", role="python", fragment_id=None),
    )
    result = wf.run("rd-block", sequence=broken)

    assert result.completed is False
    assert result.final_phase is LifecyclePhase.BLOCKED
    assert result.blocked is not None
    assert "required upstream handoff unavailable" in result.blocked.reason


# --- back-compat: no resolver wired => unchanged behavior -------------------------


def test_without_resolver_no_ledger_is_written(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, resolver=None)

    result = wf.run("rd-nores")

    assert result.completed is True
    run = JsonLifecycleRunStore(tmp_path).load("rd-nores")
    assert run is not None
    assert len(run.workflow_steps) == 0
