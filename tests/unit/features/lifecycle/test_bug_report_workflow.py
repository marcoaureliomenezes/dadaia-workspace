"""Bug-report workflow body × fragment+gate engine + Wave-D ledger (v0.1.30 / T-30-E-03).

A fake bug-report run wired with a real ``WorkflowHandoffResolver`` (real run store + real
filesystem step-payload writer under ``tmp_path``) exercises the body end-to-end: role →
fragments → dynamic selector → output schema → Python gate, proving it consumes the Wave-D
ledger. A29: the ``bug_write`` step's worker scope allows ONLY the ADDITIVE ``specs/bugs/``
path class; a write outside that channel is out-of-scope and BLOCKS.
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
from dadaia_workspace.features.lifecycle.workflows.bug_report import (
    _BUG_WRITE_STEP,
    _SEQUENCE,
    BugReportStep,
    BugReportWorkflow,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.30"


@dataclass(frozen=True)
class _StepAwareFake:
    """A fake runtime whose artifact ref depends on the step (so bug_write stays in-scope).

    The ``bug_write`` worker writes an ADDITIVE ``specs/bugs/`` record; every other step
    emits a handoff. The fake mirrors that so the typed gate's scope check passes for a
    correct run and would block a bug_write that wrote outside ``specs/bugs/``.
    """

    kind: AgentRuntimeKind

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if request.task_id.endswith(f":{_BUG_WRITE_STEP}"):
            ref = f"repos/{_CONTEXT}/specs/bugs/new-symptom.md"
        else:
            ref = f".dadaia/handoff/{_CONTEXT}/step.handoff.json"
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="bug step ok",
            artifact_refs=(ref,),
            structured_output={"verdict": "APPROVED"},
        )


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "bugs").mkdir(parents=True)
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


def _workflow(tmp_path: Path, resolver: WorkflowHandoffResolver | None) -> BugReportWorkflow:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )
    return BugReportWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _StepAwareFake(kind),  # type: ignore[arg-type]
        context_selector=selector,
        handoff_resolver=resolver,
    )


# --- A28: the body runs as a real fragment+gate workflow, no NotImplementedError ----


def test_bug_report_body_runs_end_to_end_on_fake_runtime(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))

    result = wf.run("bug-run")  # must not raise NotImplementedError

    assert result.completed is True
    labels = [s.label for s in result.steps]
    assert labels == ["bug_intake", "dedupe", "bug_write", "bug_record_gate"]
    assert result.steps[-1].is_gate is True


def test_bug_report_body_records_injected_fragments_and_context(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))
    wf.run("bug-audit")

    run = JsonLifecycleRunStore(tmp_path).load("bug-audit")
    assert run is not None
    by_step = {ic.step: ic for ic in run.injected_context}
    assert "bug_report.bug_intake" in by_step["bug_intake"].fragment_ids
    assert "bug_report.dedupe" in by_step["dedupe"].fragment_ids
    assert "bug_report.bug_write" in by_step["bug_write"].fragment_ids


# --- A29: bug_write writes ONLY specs/bugs/ (ADDITIVE) ------------------------------


def test_bug_write_scope_is_additive_specs_bugs_only(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))

    # Inspect the scope the bug_write step builds: it must allow only specs/bugs/.
    scope = wf._scope(  # noqa: SLF001 — white-box scope assertion is the point of A29.
        next(s for s in _SEQUENCE if s.label == _BUG_WRITE_STEP),
        "bug-scope",
        "suffix",
    )
    assert scope.allowed_paths == (
        f"repos/{_CONTEXT}/specs/bugs/**",
        "specs/bugs/**",
    )
    # Every other (non-writing) step emits only to the handoff dir, never specs/bugs.
    intake_scope = wf._scope(  # noqa: SLF001
        next(s for s in _SEQUENCE if s.label == "bug_intake"), "bug-scope", "suffix"
    )
    assert all("specs/bugs" not in p for p in intake_scope.allowed_paths)


def test_bug_write_blocks_when_worker_writes_outside_specs_bugs(tmp_path: Path) -> None:
    """A bug_write that writes outside the ADDITIVE bug channel is out-of-scope → BLOCKS."""
    _workspace(tmp_path)

    @dataclass(frozen=True)
    class _OutOfScopeWrite:
        kind: AgentRuntimeKind

        def runtime_kind(self) -> AgentRuntimeKind:
            return self.kind

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            # bug_write wrongly writes into memory — outside specs/bugs/.
            ref = (
                f"repos/{_CONTEXT}/specs/memory/architecture.md"
                if request.task_id.endswith(f":{_BUG_WRITE_STEP}")
                else f".dadaia/handoff/{_CONTEXT}/step.handoff.json"
            )
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="bug step",
                artifact_refs=(ref,),
                structured_output={"verdict": "APPROVED"},
            )

    specs = tmp_path / "repos" / _CONTEXT / "specs"
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )
    wf = BugReportWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _OutOfScopeWrite(kind),  # type: ignore[arg-type]
        context_selector=selector,
        handoff_resolver=_resolver(tmp_path),
    )
    result = wf.run("bug-oos")

    assert result.completed is False
    assert result.blocked is not None
    assert "out-of-scope" in result.blocked.reason


# --- ledger consume: dedupe consumes the exact bug_intake payload ------------------


def test_dedupe_consumes_exact_bug_intake_payload(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))
    wf.run("bug-consume")

    run = JsonLifecycleRunStore(tmp_path).load("bug-consume")
    assert run is not None
    intake_record = run.workflow_steps.find("bug_intake", 0)
    assert intake_record is not None
    consumers = {(c.consumer_step, c.consumer_attempt) for c in intake_record.consumptions}
    assert ("dedupe", 0) in consumers


# --- ledger BLOCK-on-missing: a missing required upstream BLOCKS --------------------


def test_missing_required_upstream_blocks_bug_report(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, _resolver(tmp_path))

    broken = (
        BugReportStep(
            label="dedupe",
            role="product-engineer",
            fragment_id="bug_report.dedupe",
            is_review=True,
            produces="bug-dedupe-handoff-v1",
            consumes=("bug_intake",),  # bug_intake never produced in this sequence
        ),
        BugReportStep(label="bug_record_gate", role="python", fragment_id=None),
    )
    result = wf.run("bug-block", sequence=broken)

    assert result.completed is False
    assert result.final_phase is LifecyclePhase.BLOCKED
    assert result.blocked is not None
    assert "required upstream handoff unavailable" in result.blocked.reason


# --- back-compat: no resolver wired => still runs, no ledger ------------------------


def test_bug_report_without_resolver_runs_and_writes_no_ledger(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _workflow(tmp_path, resolver=None)

    result = wf.run("bug-nores")

    assert result.completed is True
    run = JsonLifecycleRunStore(tmp_path).load("bug-nores")
    assert run is not None
    assert len(run.workflow_steps) == 0
    assert [s.label for s in _SEQUENCE if s.produces][0] == "bug_intake"
