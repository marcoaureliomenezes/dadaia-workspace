"""AC-2(i) — ``apply_entry_to_step`` is the single FAKE-preserving per-step author (v0.1.56).

A **non-fake** unit test of the harness->kind mapping (``codex -> CODEX_EXEC``,
``pi -> PI_HEADLESS``) + FAKE preservation, plus structural proof that ``ReleaseStep``,
``BacklogStep`` and ``AuditStep`` all satisfy the
``PolicyApplicableStep`` Protocol so the ONE generic ``apply_resolved_policy`` governs them
with no per-type union — FAKE-preserve (dry-run keeps FAKE while threading the governed
model) is harness-sandbox governance.
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
from dadaia_workspace.features.lifecycle.workflows.audit import AuditStep
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


def test_apply_entry_to_step_unknown_harness_is_hard_error() -> None:
    entry = _entry("implement", "opencode", "codex-implementation-standard")

    with pytest.raises(ValueError, match="has no.*runtime kind"):
        apply_entry_to_step(entry, base_kind=AgentRuntimeKind.CODEX_EXEC, preserve_fake=False)


# -- ① harness->kind mapping param + FAKE-preserve special case -------------------------

_MAPPING_CASES = (
    (
        "codex-maps-to-codex-exec",
        AgentRuntimeKind.CODEX_EXEC,
        False,
        "codex",
        "codex-implementation-standard",
        AgentRuntimeKind.CODEX_EXEC,
    ),
    (
        "pi-maps-to-pi-headless",
        AgentRuntimeKind.PI_HEADLESS,
        False,
        "pi",
        "pi-implementation-standard",
        AgentRuntimeKind.PI_HEADLESS,
    ),
    (
        "fake-preserved-with-model-threaded",
        AgentRuntimeKind.FAKE,
        True,
        "codex",
        "codex-review-deep",
        AgentRuntimeKind.FAKE,
    ),
)


@pytest.mark.parametrize(
    "base_kind,preserve_fake,harness,profile,expect_kind",
    [c[1:] for c in _MAPPING_CASES],
    ids=[c[0] for c in _MAPPING_CASES],
)
def test_apply_entry_to_step_mapping_matrix(
    base_kind: AgentRuntimeKind,
    preserve_fake: bool,
    harness: str,
    profile: str,
    expect_kind: AgentRuntimeKind,
) -> None:
    entry = _entry("implement", harness, profile)

    kind, resolved = apply_entry_to_step(entry, base_kind=base_kind, preserve_fake=preserve_fake)

    assert kind is expect_kind
    assert resolved.harness == harness
    assert resolved.profile_id == profile
    if harness == "codex" and profile == "codex-implementation-standard":
        assert resolved.model == "gpt-5.5"
        assert resolved.reasoning == "high"


# -- ② structural PolicyApplicableStep Protocol param over 5 step types -----------------

_STRUCTURAL_CASES = (
    (
        "release_definition",
        ReleaseStep(
            label="release_scope",
            role="product-engineer",
            fragment_id="release_definition.definition_draft",
            runtime_kind=AgentRuntimeKind.CODEX_EXEC,
        ),
        "release_scope",
        "pi",
        "pi-implementation-standard",
        AgentRuntimeKind.PI_HEADLESS,
    ),
    (
        "backlog_definition",
        BacklogStep(
            label="intake_grill",
            role="product-engineer",
            kind=BacklogStepKind.MODEL,
            fragment_id="backlog_definition.intake_grill",
            runtime_kind=AgentRuntimeKind.FAKE,
        ),
        "intake_grill",
        "codex",
        "codex-implementation-standard",
        AgentRuntimeKind.FAKE,  # FAKE preserved (dry-run base)
    ),
    (
        "audit",
        AuditStep(
            label="audit_scope",
            role="project-auditor",
            fragment_id="audit.audit_scope",
            runtime_kind=AgentRuntimeKind.FAKE,
        ),
        "audit_scope",
        "codex",
        "codex-implementation-standard",
        AgentRuntimeKind.FAKE,
    ),
)


@pytest.mark.parametrize(
    "step,step_label,harness,profile,expect_kind",
    [c[1:] for c in _STRUCTURAL_CASES],
    ids=[c[0] for c in _STRUCTURAL_CASES],
)
def test_step_types_structurally_satisfy_policy_applicable_step(
    step: object,
    step_label: str,
    harness: str,
    profile: str,
    expect_kind: AgentRuntimeKind,
) -> None:
    """The SAME generic ``apply_resolved_policy`` governs every step type with NO
    ``pipeline.py`` edit — the whole point of binding a structural ``PolicyApplicableStep``
    Protocol rather than an enumerated type-union (W2/R-2 decoupling)."""
    snapshot = WorkflowPolicySnapshot(
        workflow_id="wave-e",
        policy_id="default",
        resolved_at="2026-07-03T00:00:00Z",
        steps=(_entry(step_label, harness, profile),),
    )

    out = apply_resolved_policy((step,), snapshot)  # type: ignore[arg-type]

    assert out[0].runtime_kind is expect_kind
    assert out[0].resolved_model is not None
    assert out[0].resolved_model.harness == harness
    assert out[0].model_profile == profile
