"""Unit tests for v0.1.29 Wave A — harness as a first-class governed dimension.

Covers the effective-harness precedence (D-1), auto-profile-on-harness-override (D-1),
validation against the *effective* harness (the ``policy_resolver.py:288`` fix), and the
default-first byte-identical back-compat (AC-10), all against the shared resolver. These
sit alongside the v0.1.28 ``test_policy_resolver.py`` suite, which still pins the
no-override default path.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.workflow_execution import PolicySource
from dadaia_workspace.features.lifecycle.policy_resolver import (
    PolicyResolutionError,
    StepHarnessOverride,
    StepOverride,
    WorkflowExecutionPolicyResolver,
    library_workflow_catalog,
)
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    WorkflowModelPolicyOverlay,
)

_WORKFLOW = "implementation"


def _resolver(overlay: WorkflowModelPolicyOverlay | None = None) -> WorkflowExecutionPolicyResolver:
    return WorkflowExecutionPolicyResolver(catalog=library_workflow_catalog(), overlay=overlay)


# ---------------------------------------------------------------------------
# T-29-A-01 — CatalogStep carries per-harness default profiles
# ---------------------------------------------------------------------------


def test_catalog_step_carries_default_profiles() -> None:
    catalog = library_workflow_catalog()
    workflow = catalog.workflow(_WORKFLOW)
    assert workflow is not None
    implement = workflow.step("implement")
    assert implement is not None
    # Every supported Layer-2 harness has a governed default profile for the step.
    assert implement.default_profiles["codex"] == "codex-implementation-standard"
    assert implement.default_profiles["pi"] == "pi-implementation-standard"
    review = workflow.step("review_qa")
    assert review is not None
    assert review.default_profiles["codex"] == "codex-review-deep"
    assert review.default_profiles["pi"] == "pi-reasoning-high"


# ---------------------------------------------------------------------------
# T-29-A-02 — effective-harness precedence (AC-1)
# ---------------------------------------------------------------------------


def test_default_harness_override_moves_every_step_to_pi() -> None:
    snapshot = _resolver().resolve(_WORKFLOW, context="default", default_harness="pi")
    for entry in snapshot.steps:
        assert entry.harness == "pi"


def test_step_harness_override_moves_only_that_step() -> None:
    snapshot = _resolver().resolve(
        _WORKFLOW,
        context="default",
        step_harness_overrides=(StepHarnessOverride(step="implement", harness="pi"),),
    )
    assert snapshot.step("implement").harness == "pi"  # type: ignore[union-attr]
    assert snapshot.step("review_qa").harness == "codex"  # type: ignore[union-attr]


def test_cli_step_harness_beats_cli_default_harness() -> None:
    snapshot = _resolver().resolve(
        _WORKFLOW,
        context="default",
        default_harness="pi",
        step_harness_overrides=(StepHarnessOverride(step="implement", harness="codex"),),
    )
    assert snapshot.step("implement").harness == "codex"  # type: ignore[union-attr]
    assert snapshot.step("review_qa").harness == "pi"  # type: ignore[union-attr]


def test_overlay_step_harness_resolves_pi() -> None:
    overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: {}}},
        default_harness_overlay={"default": {}},
        step_harness_overlay={"default": {_WORKFLOW: {"implement": "pi"}}},
    )
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="default")
    assert snapshot.step("implement").harness == "pi"  # type: ignore[union-attr]
    assert snapshot.step("review_qa").harness == "codex"  # type: ignore[union-attr]


def test_cli_step_harness_beats_overlay_step_harness() -> None:
    overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: {}}},
        default_harness_overlay={"default": {}},
        step_harness_overlay={"default": {_WORKFLOW: {"implement": "pi"}}},
    )
    snapshot = _resolver(overlay).resolve(
        _WORKFLOW,
        context="default",
        step_harness_overrides=(StepHarnessOverride(step="implement", harness="codex"),),
    )
    assert snapshot.step("implement").harness == "codex"  # type: ignore[union-attr]


def test_overlay_step_harness_beats_overlay_default_harness() -> None:
    overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: {}}},
        default_harness_overlay={"default": {_WORKFLOW: "codex"}},
        step_harness_overlay={"default": {_WORKFLOW: {"implement": "pi"}}},
    )
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="default")
    assert snapshot.step("implement").harness == "pi"  # type: ignore[union-attr]
    assert snapshot.step("review_qa").harness == "codex"  # type: ignore[union-attr]


def test_overlay_default_harness_resolves_every_step_to_pi() -> None:
    overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: {}}},
        default_harness_overlay={"default": {_WORKFLOW: "pi"}},
        step_harness_overlay={"default": {_WORKFLOW: {}}},
    )
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="default")
    for entry in snapshot.steps:
        assert entry.harness == "pi"


# ---------------------------------------------------------------------------
# T-29-A-03 — auto-profile-on-harness-override + match effective harness
# ---------------------------------------------------------------------------


def test_harness_override_auto_selects_pi_default_profile() -> None:
    snapshot = _resolver().resolve(_WORKFLOW, context="default", default_harness="pi")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.harness == "pi"
    assert impl.model_profile == "pi-implementation-standard"
    review = snapshot.step("review_qa")
    assert review is not None
    assert review.model_profile == "pi-reasoning-high"


def test_explicit_profile_not_overridden_by_auto_selection() -> None:
    # An explicit --step-model on a pi-resolved step keeps the explicit profile.
    snapshot = _resolver().resolve(
        _WORKFLOW,
        context="default",
        default_harness="pi",
        cli_overrides=(StepOverride(step="implement", profile_id="pi-reasoning-low"),),
    )
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "pi-reasoning-low"
    assert impl.harness == "pi"


def test_pi_profile_accepted_on_pi_resolved_step() -> None:
    # The pre-fix policy_resolver.py:288 rejected a pi profile against a codex default
    # step; with the step resolved to pi, the pi profile is now valid.
    snapshot = _resolver().resolve(
        _WORKFLOW,
        context="default",
        step_harness_overrides=(StepHarnessOverride(step="implement", harness="pi"),),
        cli_overrides=(StepOverride(step="implement", profile_id="pi-reasoning-high"),),
    )
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.harness == "pi"
    assert impl.model_profile == "pi-reasoning-high"


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


# ---------------------------------------------------------------------------
# AC-10 — default-first / back-compat (byte-identical to v0.1.28)
# ---------------------------------------------------------------------------


def test_default_first_unchanged_no_flags_no_overlay() -> None:
    snapshot = _resolver().resolve(_WORKFLOW, context="default")
    for entry in snapshot.steps:
        assert entry.harness == "codex"
        assert entry.source is PolicySource.LIBRARY_DEFAULT
    assert snapshot.step("implement").model_profile == "codex-implementation-standard"  # type: ignore[union-attr]
    assert snapshot.step("review_qa").model_profile == "codex-review-deep"  # type: ignore[union-attr]


def test_back_compat_overlay_without_harness_resolves_catalog_default() -> None:
    # An overlay carrying only a profile override (v0.1.28 shape) resolves unchanged.
    overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: {"implement": "codex-review-deep"}}},
        default_harness_overlay={"default": {}},
        step_harness_overlay={"default": {_WORKFLOW: {}}},
    )
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="default")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.harness == "codex"
    assert impl.model_profile == "codex-review-deep"
