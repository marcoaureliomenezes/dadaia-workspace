"""T-44-6 — pipeline ``_scope`` resolves role → persona (single / multi-role / shared).

The pipeline gives every model-driven step's ``role`` the matching Layer-2 persona mandate,
threaded into the scope so the worker envelope carries an operative directive. A
``role: shared`` step (or any role with no persona atom) gets no persona block; a
comma-separated multi-role step (e.g. ``plan_review``) carries every named persona.
"""

from __future__ import annotations

import json

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline, PipelineStep
from dadaia_workspace.features.lifecycle.prompt_builder import LifecyclePromptBuilder
from dadaia_workspace.infrastructure.headless_adapter_base import build_prompt_envelope


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


def _pipeline() -> LifecyclePipeline:
    return LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.44",
        run_store=_MemoryRunStore(),
        runtime_factory=lambda kind: None,  # type: ignore[arg-type,return-value]
    )


def _step(label: str, role: str) -> PipelineStep:
    return PipelineStep(
        label=label,
        role=role,
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        runtime_kind=AgentRuntimeKind.FAKE,
    )


def _envelope_for(step: PipelineStep) -> str:
    pipe = _pipeline()
    scope = pipe._scope(step, "run1")
    built = LifecyclePromptBuilder().build(scope, runtime=AgentRuntimeKind.FAKE)
    return build_prompt_envelope(built.request)


def test_single_role_step_carries_persona_operative_directive() -> None:
    # spec_create's role is product-engineer — the envelope must carry the operative
    # directive plus the product-engineer mandate body.
    scope = _pipeline()._scope(_step("spec_create", "product-engineer"), "run1")
    assert scope.persona is not None

    payload = json.loads(_envelope_for(_step("spec_create", "product-engineer")))
    assert "persona" in payload
    assert "OPERATIVE DIRECTIVE" in payload["persona"]
    assert "act per the following role mandate" in payload["persona"]
    # The product-engineer mandate is the resolved body.
    assert "product-engineer" in payload["persona"]


def test_shared_role_step_has_no_persona_block() -> None:
    scope = _pipeline()._scope(_step("write_scope", "shared"), "run1")
    assert scope.persona is None

    payload = json.loads(_envelope_for(_step("write_scope", "shared")))
    assert "persona" not in payload


def test_unmapped_role_step_has_no_persona_block() -> None:
    # project-manager has no persona atom (D-1) → no persona block.
    scope = _pipeline()._scope(_step("orchestrate", "project-manager"), "run1")
    assert scope.persona is None


def test_multi_role_step_carries_both_mandates() -> None:
    # plan_review names "qa-engineer, software-architect" — both mandates must be carried,
    # each clearly delimited by a role header, and the operative directive applied.
    role = "qa-engineer, software-architect"
    scope = _pipeline()._scope(_step("plan_review", role), "run1")
    assert scope.persona is not None
    assert "### Persona — qa-engineer" in scope.persona
    assert "### Persona — software-architect" in scope.persona

    payload = json.loads(_envelope_for(_step("plan_review", role)))
    assert "OPERATIVE DIRECTIVE" in payload["persona"]
    assert "### Persona — qa-engineer" in payload["persona"]
    assert "### Persona — software-architect" in payload["persona"]
