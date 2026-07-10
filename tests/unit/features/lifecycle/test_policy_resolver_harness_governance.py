"""Unit tests for v0.1.29 Wave A — harness as a first-class governed dimension.

Covers the effective-harness precedence (D-1), auto-profile-on-harness-override (D-1),
validation against the *effective* harness (the ``policy_resolver.py:288`` fix), and the
default-first byte-identical back-compat (AC-10), all against the shared resolver. These
sit alongside the v0.1.28 ``test_policy_resolver.py`` suite, which still pins the
no-override default path — the AC-10 default-first pair is byte-identical to that suite's
library-default fn and is not repeated here.

CRITICAL: Layer-2 residue rejection + precedence order (CLI > overlay-step >
overlay-default > catalog).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.workflow_execution import (
    WorkflowModelPolicyOverlay,
)
from dadaia_workspace.features.lifecycle.policy_resolver import (
    PolicyResolutionError,
    StepHarnessOverride,
    StepOverride,
    WorkflowExecutionPolicyResolver,
)
from tests.unit.features.lifecycle._workflow_catalog import library_workflow_catalog

_WORKFLOW = "implementation"


def _resolver(overlay: WorkflowModelPolicyOverlay | None = None) -> WorkflowExecutionPolicyResolver:
    return WorkflowExecutionPolicyResolver(catalog=library_workflow_catalog(), overlay=overlay)


# ---------------------------------------------------------------------------
# ① T-29-A-01/A-02 — CatalogStep per-harness default profiles + effective-harness
# precedence matrix (AC-1)
# ---------------------------------------------------------------------------


def test_effective_harness_precedence_matrix() -> None:
    """T-29-A-01: CatalogStep carries a governed default profile per supported Layer-2
    harness. T-29-A-02: default->all-pi / step-only / CLI-step-beats-CLI-default /
    overlay-step / CLI-beats-overlay-step / overlay-step-beats-overlay-default /
    overlay-default-all — every layer of the precedence chain (CLI > overlay-step > overlay-default > catalog)
    as one param table."""
    catalog = library_workflow_catalog()
    workflow = catalog.workflow(_WORKFLOW)
    assert workflow is not None
    implement_step = workflow.step("implement")
    assert implement_step is not None
    # Every supported Layer-2 harness has a governed default profile for the step.
    assert implement_step.default_profiles["codex"] == "codex-implementation-standard"
    assert implement_step.default_profiles["pi"] == "pi-implementation-standard"
    review_step = workflow.step("review_qa")
    assert review_step is not None
    assert review_step.default_profiles["codex"] == "codex-review-deep"
    assert review_step.default_profiles["pi"] == "pi-reasoning-high"

    default_snapshot = _resolver().resolve(_WORKFLOW, context="default", default_harness="pi")
    for entry in default_snapshot.steps:
        assert entry.harness == "pi"

    step_only_snapshot = _resolver().resolve(
        _WORKFLOW,
        context="default",
        step_harness_overrides=(StepHarnessOverride(step="implement", harness="pi"),),
    )
    assert step_only_snapshot.step("implement").harness == "pi"  # type: ignore[union-attr]
    assert step_only_snapshot.step("review_qa").harness == "codex"  # type: ignore[union-attr]

    cli_beats_cli_default = _resolver().resolve(
        _WORKFLOW,
        context="default",
        default_harness="pi",
        step_harness_overrides=(StepHarnessOverride(step="implement", harness="codex"),),
    )
    assert cli_beats_cli_default.step("implement").harness == "codex"  # type: ignore[union-attr]
    assert cli_beats_cli_default.step("review_qa").harness == "pi"  # type: ignore[union-attr]

    overlay_step_only = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: {}}},
        default_harness_overlay={"default": {}},
        step_harness_overlay={"default": {_WORKFLOW: {"implement": "pi"}}},
    )
    overlay_step_snapshot = _resolver(overlay_step_only).resolve(_WORKFLOW, context="default")
    assert overlay_step_snapshot.step("implement").harness == "pi"  # type: ignore[union-attr]
    assert overlay_step_snapshot.step("review_qa").harness == "codex"  # type: ignore[union-attr]

    cli_beats_overlay_step = _resolver(overlay_step_only).resolve(
        _WORKFLOW,
        context="default",
        step_harness_overrides=(StepHarnessOverride(step="implement", harness="codex"),),
    )
    assert cli_beats_overlay_step.step("implement").harness == "codex"  # type: ignore[union-attr]

    overlay_step_beats_overlay_default = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: {}}},
        default_harness_overlay={"default": {_WORKFLOW: "codex"}},
        step_harness_overlay={"default": {_WORKFLOW: {"implement": "pi"}}},
    )
    overlay_layered_snapshot = _resolver(overlay_step_beats_overlay_default).resolve(
        _WORKFLOW, context="default"
    )
    assert overlay_layered_snapshot.step("implement").harness == "pi"  # type: ignore[union-attr]
    assert overlay_layered_snapshot.step("review_qa").harness == "codex"  # type: ignore[union-attr]

    overlay_default_all = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: {}}},
        default_harness_overlay={"default": {_WORKFLOW: "pi"}},
        step_harness_overlay={"default": {_WORKFLOW: {}}},
    )
    overlay_default_snapshot = _resolver(overlay_default_all).resolve(_WORKFLOW, context="default")
    for entry in overlay_default_snapshot.steps:
        assert entry.harness == "pi"


# ---------------------------------------------------------------------------
# ② T-29-A-03 — auto-profile-on-harness-override + explicit-not-overridden + pi-accepted
# ---------------------------------------------------------------------------


def test_auto_profile_on_harness_override_and_explicit_profile_not_overridden() -> None:
    auto = _resolver().resolve(_WORKFLOW, context="default", default_harness="pi")
    impl = auto.step("implement")
    assert impl is not None
    assert impl.harness == "pi"
    assert impl.model_profile == "pi-implementation-standard"
    review = auto.step("review_qa")
    assert review is not None
    assert review.model_profile == "pi-reasoning-high"

    # An explicit --step-model on a pi-resolved step keeps the explicit profile.
    explicit = _resolver().resolve(
        _WORKFLOW,
        context="default",
        default_harness="pi",
        cli_overrides=(StepOverride(step="implement", profile_id="pi-reasoning-low"),),
    )
    explicit_impl = explicit.step("implement")
    assert explicit_impl is not None
    assert explicit_impl.model_profile == "pi-reasoning-low"
    assert explicit_impl.harness == "pi"

    # The pre-fix policy_resolver.py:288 rejected a pi profile against a codex default
    # step; with the step resolved to pi, the pi profile is now valid.
    pi_on_pi = _resolver().resolve(
        _WORKFLOW,
        context="default",
        step_harness_overrides=(StepHarnessOverride(step="implement", harness="pi"),),
        cli_overrides=(StepOverride(step="implement", profile_id="pi-reasoning-high"),),
    )
    pi_on_pi_impl = pi_on_pi.step("implement")
    assert pi_on_pi_impl is not None
    assert pi_on_pi_impl.harness == "pi"
    assert pi_on_pi_impl.model_profile == "pi-reasoning-high"


def test_explicit_profile_conflicts_with_effective_harness_rejected() -> None:
    # --harness pi + a codex --step-model is a clean rejection (AC-2 conflict).
    with pytest.raises(PolicyResolutionError) as exc:
        _resolver().resolve(
            _WORKFLOW,
            context="default",
            default_harness="pi",
            cli_overrides=(
                StepOverride(step="implement", profile_id="codex-implementation-standard"),
            ),
        )
    msg = str(exc.value).lower()
    assert "harness" in msg
    assert "pi" in msg


def test_layer2_residue_harness_rejected() -> None:
    # AC-9: claude/opencode never accepted as a Layer-2 worker harness.
    for bad in ("claude", "opencode", "claude_sdk"):
        with pytest.raises(PolicyResolutionError) as exc:
            _resolver().resolve(_WORKFLOW, context="default", default_harness=bad)
        msg = str(exc.value).lower()
        assert "codex" in msg or "pi" in msg
