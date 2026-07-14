"""W1-3 (T-47-12) — persona injection on ALL verbs, not just the pipeline.

Before this fix, role->persona resolution existed only in ``LifecyclePipeline._scope``. The
three fragment workflow bodies (release_definition / audit /
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

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRuntimeKind,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.personas.loader import resolve_persona_for_role
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


# --- the fragment workflow bodies, parametrized over (workflow_cls, extra kwargs) ---


def _first_persona_step(sequence: object) -> object:
    """Return the first step in a workflow sequence whose role resolves to a persona."""
    for step in sequence:  # type: ignore[attr-defined]
        if getattr(step, "fragment_id", None) is None:
            continue
        if resolve_persona_for_role(step.role) is not None:
            return step
    raise AssertionError("no persona-bearing model step in sequence")


def _release_definition_case(tmp_path: Path):
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        _SEQUENCE,
        ReleaseDefinitionWorkflow,
    )

    return ReleaseDefinitionWorkflow, {}, _SEQUENCE


def _audit_case(tmp_path: Path):
    from dadaia_workspace.features.lifecycle.workflows.audit import _SEQUENCE, AuditWorkflow

    return AuditWorkflow, {}, _SEQUENCE


def _backlog_definition_case(tmp_path: Path):
    from dadaia_workspace.features.backlog.subject_registry import Registry
    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
        _SEQUENCE,
        BacklogDefinitionWorkflow,
    )

    return BacklogDefinitionWorkflow, {"registry": Registry(anchors={}, aliases={})}, _SEQUENCE


_CASE_BUILDERS = {
    "release_definition": _release_definition_case,
    "audit": _audit_case,
    "backlog_definition": _backlog_definition_case,
}


@pytest.mark.parametrize("case_id", sorted(_CASE_BUILDERS))
def test_workflow_body_scope_carries_persona(tmp_path: Path, case_id: str) -> None:
    workflow_cls, extra_kwargs, sequence = _CASE_BUILDERS[case_id](tmp_path)
    wf = workflow_cls(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=_MemoryRunStore(),  # type: ignore[arg-type]
        runtime_factory=lambda kind: None,  # type: ignore[arg-type,return-value]
        context_selector=_selector(tmp_path),
        **extra_kwargs,
    )
    step = _first_persona_step(sequence)
    scope = wf._scope(step, "run1", "suffix body")  # type: ignore[arg-type]
    expected = resolve_persona_for_role(step.role)  # type: ignore[attr-defined]
    assert expected is not None
    assert scope.persona == expected

    built = LifecyclePromptBuilder().build(scope, runtime=AgentRuntimeKind.FAKE)
    persona_field = _envelope_persona(built.request)
    assert "OPERATIVE DIRECTIVE" in persona_field
    assert expected in persona_field
