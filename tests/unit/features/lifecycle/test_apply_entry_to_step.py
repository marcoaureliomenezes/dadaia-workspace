"""AC-2(i) — ``apply_entry_to_step`` is the single FAKE-preserving per-step author (v0.1.56).

A **non-fake** unit test of the harness→kind mapping (``codex -> CODEX_EXEC``,
``pi -> PI_HEADLESS``) + FAKE preservation, plus structural proof that ``ReleaseStep`` and
``BacklogStep`` satisfy the ``PolicyApplicableStep`` Protocol so the ONE generic
``apply_resolved_policy`` governs them with no per-type union.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.core.models.workflow_execution import (
    PolicySource,
    WorkflowPolicySnapshot,
    WorkflowPolicyStepEntry,
)
from dadaia_workspace.features.lifecycle.pipeline import (
    apply_entry_to_step,
    apply_resolved_policy,
)
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    BacklogStep,
    BacklogStepKind,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import ReleaseStep


def _entry(step: str, harness: str, profile: str) -> WorkflowPolicyStepEntry:
    return WorkflowPolicyStepEntry(
        step=step,
        harness=harness,
        model_profile=profile,
        model="gpt-5.5",
        reasoning="high",
        source=PolicySource.LIBRARY_DEFAULT,
    )


def test_apply_entry_to_step_codex_maps_to_codex_exec() -> None:
    entry = _entry("implement", "codex", "codex-implementation-standard")

    kind, resolved = apply_entry_to_step(
        entry, base_kind=AgentRuntimeKind.CODEX_EXEC, preserve_fake=False
    )

    assert kind is AgentRuntimeKind.CODEX_EXEC
    assert resolved.harness == "codex"
    assert resolved.profile_id == "codex-implementation-standard"
    assert resolved.model == "gpt-5.5"
    assert resolved.reasoning == "high"


def test_apply_entry_to_step_pi_maps_to_pi_headless() -> None:
    entry = _entry("implement", "pi", "pi-implementation-standard")

    kind, resolved = apply_entry_to_step(
        entry, base_kind=AgentRuntimeKind.PI_HEADLESS, preserve_fake=False
    )

    assert kind is AgentRuntimeKind.PI_HEADLESS
    assert resolved.harness == "pi"
    assert resolved.profile_id == "pi-implementation-standard"


def test_apply_entry_to_step_preserves_fake_but_threads_governed_model() -> None:
    # AC-2(a/b): a fake base keeps FAKE (drives the fake adapter) while the snapshot's
    # governed harness/model is still threaded for auditability — NOT ``FAKE == codex``.
    entry = _entry("implement", "codex", "codex-review-deep")

    kind, resolved = apply_entry_to_step(entry, base_kind=AgentRuntimeKind.FAKE, preserve_fake=True)

    assert kind is AgentRuntimeKind.FAKE
    assert resolved.harness == "codex"
    assert resolved.profile_id == "codex-review-deep"


def test_apply_entry_to_step_unknown_harness_is_hard_error() -> None:
    entry = _entry("implement", "opencode", "codex-implementation-standard")

    with pytest.raises(ValueError, match="has no.*runtime kind"):
        apply_entry_to_step(entry, base_kind=AgentRuntimeKind.CODEX_EXEC, preserve_fake=False)


def test_release_step_structurally_satisfies_policy_applicable_step() -> None:
    # Proof the SAME generic applier governs a ReleaseStep (no PipelineStep type-union).
    step = ReleaseStep(
        label="release_scope",
        role="product-engineer",
        fragment_id="release_definition.release_scope",
        runtime_kind=AgentRuntimeKind.CODEX_EXEC,
    )
    snapshot = WorkflowPolicySnapshot(
        workflow_id="release_definition",
        policy_id="default",
        resolved_at="2026-07-03T00:00:00Z",
        steps=(_entry("release_scope", "pi", "pi-implementation-standard"),),
    )

    out = apply_resolved_policy((step,), snapshot)

    assert out[0].runtime_kind is AgentRuntimeKind.PI_HEADLESS
    assert out[0].resolved_model is not None
    assert out[0].resolved_model.profile_id == "pi-implementation-standard"
    assert out[0].model_profile == "pi-implementation-standard"


def test_backlog_step_structurally_satisfies_and_preserves_fake() -> None:
    step = BacklogStep(
        label="intake_grill",
        role="product-engineer",
        kind=BacklogStepKind.MODEL,
        fragment_id="backlog_definition.intake_grill",
        runtime_kind=AgentRuntimeKind.FAKE,
    )
    snapshot = WorkflowPolicySnapshot(
        workflow_id="backlog_definition",
        policy_id="default",
        resolved_at="2026-07-03T00:00:00Z",
        steps=(_entry("intake_grill", "codex", "codex-implementation-standard"),),
    )

    out = apply_resolved_policy((step,), snapshot)

    # FAKE preserved for the dry-run base; governed model still threaded.
    assert out[0].runtime_kind is AgentRuntimeKind.FAKE
    assert out[0].resolved_model is not None
    assert out[0].resolved_model.harness == "codex"
    assert out[0].model_profile == "codex-implementation-standard"
