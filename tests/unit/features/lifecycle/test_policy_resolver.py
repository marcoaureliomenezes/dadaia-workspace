"""Unit tests for the WorkflowExecutionPolicyResolver (T-28-A-04).

The single shared resolver consumed by CLI and panel. Precedence:
``CLI > context overlay > default overlay > library default`` (only the ``default``
context overlay is honored — D-2). It validates every override against the catalog's
step ids + the profile registry + the step's harness, and returns a
``WorkflowPolicySnapshot``. M3: library step defaults come from ``model_profiles``
directly, not the Wave-B catalog — Wave A is independently green.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.workflow_execution import (
    PolicySource,
    WorkflowModelPolicyOverlay,
)
from dadaia_workspace.features.lifecycle.policy_resolver import (
    PolicyResolutionError,
    StepOverride,
    WorkflowExecutionPolicyResolver,
)
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
)
from tests.unit.features.lifecycle._workflow_catalog import library_workflow_catalog

_WORKFLOW = "implementation"


def _resolver(overlay: WorkflowModelPolicyOverlay | None = None) -> WorkflowExecutionPolicyResolver:
    return WorkflowExecutionPolicyResolver(catalog=library_workflow_catalog(), overlay=overlay)


def _overlay(steps: dict[str, str]) -> WorkflowModelPolicyOverlay:
    return WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: dict(steps)}},
    )


def test_library_default_resolves_every_step() -> None:
    snapshot = _resolver().resolve(_WORKFLOW, context="default")
    labels = [entry.step for entry in snapshot.steps]
    assert labels == ["implement", "review_qa", "review_security", "review_code"]
    for entry in snapshot.steps:
        assert entry.source is PolicySource.LIBRARY_DEFAULT
        assert entry.model  # concrete model id resolved
        assert entry.reasoning


def test_default_implement_step_uses_implementation_profile() -> None:
    snapshot = _resolver().resolve(_WORKFLOW, context="default")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "codex-implementation-standard"
    assert impl.harness == "codex"
    assert impl.model == "gpt-5.5"
    assert impl.reasoning == "medium"


def test_default_review_step_uses_deep_profile() -> None:
    snapshot = _resolver().resolve(_WORKFLOW, context="default")
    qa = snapshot.step("review_qa")
    assert qa is not None
    assert qa.model_profile == "codex-review-deep"
    assert qa.reasoning == "high"


def test_overlay_overrides_default() -> None:
    overlay = _overlay({"implement": "codex-review-deep"})
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="default")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "codex-review-deep"
    assert impl.source is PolicySource.DEFAULT_OVERLAY
    # untouched steps stay library default
    assert snapshot.step("review_qa").source is PolicySource.LIBRARY_DEFAULT  # type: ignore[union-attr]


def test_cli_override_beats_overlay() -> None:
    overlay = _overlay({"implement": "codex-review-deep"})
    snapshot = _resolver(overlay).resolve(
        _WORKFLOW,
        context="default",
        cli_overrides=(StepOverride(step="implement", profile_id="codex-implementation-standard"),),
    )
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "codex-implementation-standard"
    assert impl.source is PolicySource.CLI


def test_non_default_context_overlay_now_honored() -> None:
    # WS-OVERLAYS (replaces the D-2 collapse, A15): an overlay keyed on a non-default
    # context IS honored. The override must be harness-consistent — here 'other' sets both
    # the per-step harness to pi and a pi profile, so resolution succeeds.
    overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"other": {_WORKFLOW: {"implement": "pi-reasoning-high"}}},
        step_harness_overlay={"other": {_WORKFLOW: {"implement": "pi"}}},
    )
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="other")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "pi-reasoning-high"
    assert impl.harness == "pi"
    assert impl.source is PolicySource.DEFAULT_OVERLAY


def test_non_default_context_unknown_falls_back_to_library_default() -> None:
    # A non-default context with NO override anywhere in its chain inherits the library
    # default (the chain tail is 'default', which here carries no overlay).
    overlay = WorkflowModelPolicyOverlay(policy_id="default", contexts={})
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="unmapped")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "codex-implementation-standard"
    assert impl.source is PolicySource.LIBRARY_DEFAULT


def test_unknown_workflow_raises() -> None:
    with pytest.raises(PolicyResolutionError):
        _resolver().resolve("no-such-workflow", context="default")


def test_overlay_unknown_step_raises() -> None:
    overlay = _overlay({"no-such-step": "codex-review-deep"})
    with pytest.raises(PolicyResolutionError) as exc:
        _resolver(overlay).resolve(_WORKFLOW, context="default")
    assert "no-such-step" in str(exc.value)


def test_overlay_unknown_profile_raises() -> None:
    overlay = _overlay({"implement": "no-such-profile"})
    with pytest.raises(PolicyResolutionError) as exc:
        _resolver(overlay).resolve(_WORKFLOW, context="default")
    assert "no-such-profile" in str(exc.value)


def test_cli_override_harness_mismatch_raises() -> None:
    # implement defaults to codex; a pi profile mismatches the step harness.
    with pytest.raises(PolicyResolutionError) as exc:
        _resolver().resolve(
            _WORKFLOW,
            context="default",
            cli_overrides=(StepOverride(step="implement", profile_id="pi-reasoning-high"),),
        )
    assert "harness" in str(exc.value).lower()


def test_cli_override_unknown_step_raises() -> None:
    with pytest.raises(PolicyResolutionError):
        _resolver().resolve(
            _WORKFLOW,
            context="default",
            cli_overrides=(StepOverride(step="ghost", profile_id="codex-review-deep"),),
        )


def test_snapshot_records_precedence_and_fragments() -> None:
    snapshot = _resolver().resolve(_WORKFLOW, context="default")
    assert snapshot.workflow_id == _WORKFLOW
    assert "library-default" in snapshot.source_precedence
    impl = snapshot.step("implement")
    assert impl is not None
    assert "implementation.implement_tdd" in impl.fragments


def test_resolver_from_store_overlay(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / ".dadaia").mkdir()
    store = JsonWorkflowModelPolicyStore(tmp_path)
    store.save(store.parse(_overlay({"implement": "codex-review-deep"}).to_dict()))
    resolver = WorkflowExecutionPolicyResolver(
        catalog=library_workflow_catalog(), overlay=store.load()
    )
    impl = resolver.resolve(_WORKFLOW, context="default").step("implement")
    assert impl is not None
    assert impl.model_profile == "codex-review-deep"
