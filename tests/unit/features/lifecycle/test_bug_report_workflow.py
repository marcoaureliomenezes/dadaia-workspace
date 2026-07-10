"""Bug-report workflow-specific behavior beyond the shared suite (v0.1.30 / T-30-E-03).

The shared e2e-completion / exact-consumption / block-on-missing / no-resolver behaviors are
covered generically for this workflow in ``test_fragment_workflow_bodies.py``. This file keeps
only what is bug_report-specific: A29's ``bug_write`` worker scope allows ONLY the ADDITIVE
``specs/bugs/`` path class (both the positive scope-assertion and the negative every-other-step
assertion), and the out-of-scope BLOCK when a worker writes outside that channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.features.lifecycle.workflows.bug_report import (
    _BUG_WRITE_STEP,
    _SEQUENCE,
    BugReportWorkflow,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.30"


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
    from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

    return WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-06-27T12:00:00Z",
    )


def _selector(tmp_path: Path) -> ContextSelector:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    return ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )


def test_bug_write_scope_is_additive_specs_bugs_only(tmp_path: Path) -> None:
    _workspace(tmp_path)

    @dataclass(frozen=True)
    class _StepAwareFake:
        kind: AgentRuntimeKind

        def runtime_kind(self) -> AgentRuntimeKind:
            return self.kind

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            ref = (
                f"repos/{_CONTEXT}/specs/bugs/new-symptom.md"
                if request.task_id.endswith(f":{_BUG_WRITE_STEP}")
                else f".dadaia/handoff/{_CONTEXT}/step.handoff.json"
            )
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="bug step ok",
                artifact_refs=(ref,),
                structured_output={"verdict": "APPROVED"},
            )

    wf = BugReportWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _StepAwareFake(kind),  # type: ignore[arg-type]
        context_selector=_selector(tmp_path),
        handoff_resolver=_resolver(tmp_path),
    )

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

    wf = BugReportWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _OutOfScopeWrite(kind),  # type: ignore[arg-type]
        context_selector=_selector(tmp_path),
        handoff_resolver=_resolver(tmp_path),
    )
    result = wf.run("bug-oos")

    assert result.completed is False
    assert result.blocked is not None
    assert "out-of-scope" in result.blocked.reason
