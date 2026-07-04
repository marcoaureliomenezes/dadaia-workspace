"""W1-3 (T-47-12) — persona injection on ALL verbs, not just the pipeline.

Before this fix, role→persona resolution existed only in ``LifecyclePipeline._scope``. The
five fragment workflow bodies (release_definition / audit / research / bug_report /
backlog_definition) and the CLI single-step path (``_run_phase_step``) built their
``PromptScope`` WITHOUT a persona, so every model step reached the worker with no operative
role directive on those verbs.

These tests prove that every model step's assembled prompt — on each of the five workflow
bodies AND the CLI step path — now carries the resolved persona body wrapped in the
operative directive, using the shared ``resolve_persona_for_role`` helper (the single
source pipeline also uses).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.personas.loader import resolve_persona_for_role
from dadaia_workspace.features.lifecycle.phase_workflow import LifecyclePhaseWorkflow
from dadaia_workspace.features.lifecycle.prompt_builder import LifecyclePromptBuilder
from dadaia_workspace.infrastructure.headless_adapter_base import build_prompt_envelope

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.47"


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


def _selector(tmp_path: Path) -> ContextSelector:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    return ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia")
    )


def _envelope_persona(request: AgentRunRequest) -> str:
    """The ``persona`` field of the built worker envelope (raises if absent)."""
    payload = json.loads(build_prompt_envelope(request))
    return str(payload["persona"])


# --- the five fragment workflow bodies ---------------------------------------------


def _first_persona_step(sequence: object) -> object:
    """Return the first step in a workflow sequence whose role resolves to a persona."""
    for step in sequence:  # type: ignore[attr-defined]
        if getattr(step, "fragment_id", None) is None:
            continue
        if resolve_persona_for_role(step.role) is not None:
            return step
    raise AssertionError("no persona-bearing model step in sequence")


def test_release_definition_scope_carries_persona(tmp_path: Path) -> None:
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        _SEQUENCE,
        ReleaseDefinitionWorkflow,
    )

    wf = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=_MemoryRunStore(),  # type: ignore[arg-type]
        runtime_factory=lambda kind: None,  # type: ignore[arg-type,return-value]
        context_selector=_selector(tmp_path),
    )
    step = _first_persona_step(_SEQUENCE)
    scope = wf._scope(step, "run1", "suffix body")  # type: ignore[arg-type]
    expected = resolve_persona_for_role(step.role)  # type: ignore[attr-defined]
    assert expected is not None
    assert scope.persona == expected

    built = LifecyclePromptBuilder().build(scope, runtime=AgentRuntimeKind.FAKE)
    persona_field = _envelope_persona(built.request)
    assert "OPERATIVE DIRECTIVE" in persona_field
    assert expected in persona_field


def test_audit_scope_carries_persona(tmp_path: Path) -> None:
    from dadaia_workspace.features.lifecycle.workflows.audit import _SEQUENCE, AuditWorkflow

    wf = AuditWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=_MemoryRunStore(),  # type: ignore[arg-type]
        runtime_factory=lambda kind: None,  # type: ignore[arg-type,return-value]
        context_selector=_selector(tmp_path),
    )
    step = _first_persona_step(_SEQUENCE)
    scope = wf._scope(step, "run1", "suffix body")  # type: ignore[arg-type]
    expected = resolve_persona_for_role(step.role)  # type: ignore[attr-defined]
    assert expected is not None
    assert scope.persona == expected
    assert expected in _envelope_persona(
        LifecyclePromptBuilder().build(scope, runtime=AgentRuntimeKind.FAKE).request
    )


def test_research_scope_carries_persona(tmp_path: Path) -> None:
    from dadaia_workspace.features.lifecycle.workflows.research import _SEQUENCE, ResearchWorkflow

    wf = ResearchWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=_MemoryRunStore(),  # type: ignore[arg-type]
        runtime_factory=lambda kind: None,  # type: ignore[arg-type,return-value]
        context_selector=_selector(tmp_path),
    )
    step = _first_persona_step(_SEQUENCE)
    scope = wf._scope(step, "run1", "suffix body")  # type: ignore[arg-type]
    expected = resolve_persona_for_role(step.role)  # type: ignore[attr-defined]
    assert expected is not None
    assert scope.persona == expected
    assert expected in _envelope_persona(
        LifecyclePromptBuilder().build(scope, runtime=AgentRuntimeKind.FAKE).request
    )


def test_bug_report_scope_carries_persona(tmp_path: Path) -> None:
    from dadaia_workspace.features.lifecycle.workflows.bug_report import (
        _SEQUENCE,
        BugReportWorkflow,
    )

    wf = BugReportWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=_MemoryRunStore(),  # type: ignore[arg-type]
        runtime_factory=lambda kind: None,  # type: ignore[arg-type,return-value]
        context_selector=_selector(tmp_path),
    )
    step = _first_persona_step(_SEQUENCE)
    scope = wf._scope(step, "run1", "suffix body")  # type: ignore[arg-type]
    expected = resolve_persona_for_role(step.role)  # type: ignore[attr-defined]
    assert expected is not None
    assert scope.persona == expected
    assert expected in _envelope_persona(
        LifecyclePromptBuilder().build(scope, runtime=AgentRuntimeKind.FAKE).request
    )


def test_backlog_definition_scope_carries_persona(tmp_path: Path) -> None:
    from dadaia_workspace.features.backlog.subject_registry import Registry
    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
        _SEQUENCE,
        BacklogDefinitionWorkflow,
    )

    wf = BacklogDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=_MemoryRunStore(),  # type: ignore[arg-type]
        runtime_factory=lambda kind: None,  # type: ignore[arg-type,return-value]
        context_selector=_selector(tmp_path),
        registry=Registry(anchors={}, aliases={}),
    )
    step = _first_persona_step(_SEQUENCE)
    scope = wf._scope(step, "run1", "suffix body")  # type: ignore[arg-type]
    expected = resolve_persona_for_role(step.role)  # type: ignore[attr-defined]
    assert expected is not None
    assert scope.persona == expected
    assert expected in _envelope_persona(
        LifecyclePromptBuilder().build(scope, runtime=AgentRuntimeKind.FAKE).request
    )


# --- the CLI single-step path (_run_phase_step) ------------------------------------


class _RecordingRuntime:
    """A FAKE-kind runtime that records every request it receives (blocks the gate)."""

    def __init__(self) -> None:
        self.received: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received.append(request)
        return AgentRunResult(status=AgentRunStatus.SUCCEEDED, summary="fake no-op")


def test_cli_run_phase_step_injects_persona(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI single-step path (close/qa/security/code/implement/define) injects persona."""
    from dadaia_workspace import container
    from dadaia_workspace.cli.commands import lifecycle as lifecycle_cli
    from dadaia_workspace.features.lifecycle.governed_catalog import governed_workflow_catalog
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowExecutionPolicyResolver,
    )

    recording = _RecordingRuntime()

    def _fake_phase_workflow(*_args: object, **_kwargs: object) -> LifecyclePhaseWorkflow:
        return LifecyclePhaseWorkflow(runtime=recording, run_store=_MemoryRunStore())  # type: ignore[arg-type]

    monkeypatch.setattr(lifecycle_cli, "resolve_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(container, "build_lifecycle_phase_workflow", _fake_phase_workflow)
    # v0.1.56 FR1: the CLI phase path resolves a governed snapshot first; back it with the
    # code-only governed catalog so no initialized workspace is needed for this unit test.
    monkeypatch.setattr(
        container,
        "build_workflow_policy_resolver",
        lambda *a, **k: WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog()),
    )

    # The FAKE worker emits no artifact_refs → the create-step gate blocks → typer.Exit.
    with pytest.raises(typer.Exit):
        lifecycle_cli._run_phase_step(
            label="close",
            role="product-engineer",
            from_phase=LifecyclePhase.CODE_REVIEW,
            target_phase=LifecyclePhase.CLOSURE,
            context=_CONTEXT,
            release_id=_RELEASE,
            run_id="close-run",
            harness="fake",
            workflow_id="closure",
            catalog_step_label="close",
            json_output=True,
        )

    assert recording.received, "worker was never called"
    persona = recording.received[0].persona
    expected = resolve_persona_for_role("product-engineer")
    assert expected is not None
    assert persona == expected
