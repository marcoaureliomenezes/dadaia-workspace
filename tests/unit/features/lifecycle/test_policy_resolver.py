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

_WORKFLOW = "implementation_reviews"


def _resolver(overlay: WorkflowModelPolicyOverlay | None = None) -> WorkflowExecutionPolicyResolver:
    return WorkflowExecutionPolicyResolver(catalog=library_workflow_catalog(), overlay=overlay)


def _overlay(steps: dict[str, str]) -> WorkflowModelPolicyOverlay:
    return WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"default": {_WORKFLOW: dict(steps)}},
    )


# --- ① library-default resolution + overlay-overrides-default --------------------------


def test_library_default_resolution_and_overlay_override() -> None:
    snapshot = _resolver().resolve(_WORKFLOW, context="default")
    labels = [entry.step for entry in snapshot.steps]
    assert labels == ["implement", "review_qa", "review_security", "review_code", "close"]
    for entry in snapshot.steps:
        assert entry.source is PolicySource.LIBRARY_DEFAULT
        assert entry.model  # concrete model id resolved
        assert entry.reasoning

    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "codex-implementation-standard"
    assert impl.harness == "codex"
    assert impl.model == "gpt-5.5"
    assert impl.reasoning == "medium"

    qa = snapshot.step("review_qa")
    assert qa is not None
    assert qa.model_profile == "codex-review-deep"
    assert qa.reasoning == "high"

    assert snapshot.workflow_id == _WORKFLOW
    assert "library-default" in snapshot.source_precedence
    assert "implementation.implement_tdd" in impl.fragments

    overlay = _overlay({"implement": "codex-review-deep"})
    overridden = _resolver(overlay).resolve(_WORKFLOW, context="default")
    overridden_impl = overridden.step("implement")
    assert overridden_impl is not None
    assert overridden_impl.model_profile == "codex-review-deep"
    assert overridden_impl.source is PolicySource.DEFAULT_OVERLAY
    # untouched steps stay library default
    assert overridden.step("review_qa").source is PolicySource.LIBRARY_DEFAULT  # type: ignore[union-attr]

    # CLI beats overlay: the same overlay override is superseded by an explicit CLI pin.
    cli_snapshot = _resolver(overlay).resolve(
        _WORKFLOW,
        context="default",
        cli_overrides=(StepOverride(step="implement", profile_id="codex-implementation-standard"),),
    )
    cli_impl = cli_snapshot.step("implement")
    assert cli_impl is not None
    assert cli_impl.model_profile == "codex-implementation-standard"
    assert cli_impl.source is PolicySource.CLI

    # WS-OVERLAYS (replaces the D-2 collapse, A15): an overlay keyed on a non-default
    # context IS honored. The override must be harness-consistent — here 'other' sets both
    # the per-step harness to pi and a pi profile, so resolution succeeds.
    non_default_overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={"other": {_WORKFLOW: {"implement": "pi-reasoning-high"}}},
        step_harness_overlay={"other": {_WORKFLOW: {"implement": "pi"}}},
    )
    other_snapshot = _resolver(non_default_overlay).resolve(_WORKFLOW, context="other")
    other_impl = other_snapshot.step("implement")
    assert other_impl is not None
    assert other_impl.model_profile == "pi-reasoning-high"
    assert other_impl.harness == "pi"
    assert other_impl.source is PolicySource.DEFAULT_OVERLAY


# --- ② error matrix param ---------------------------------------------------------------

_ERROR_CASES = (
    (
        "unknown-workflow",
        lambda: _resolver().resolve("no-such-workflow", context="default"),
        None,
    ),
    (
        "overlay-unknown-step",
        lambda: _resolver(_overlay({"no-such-step": "codex-review-deep"})).resolve(
            _WORKFLOW, context="default"
        ),
        "no-such-step",
    ),
    (
        "overlay-unknown-profile",
        lambda: _resolver(_overlay({"implement": "no-such-profile"})).resolve(
            _WORKFLOW, context="default"
        ),
        "no-such-profile",
    ),
    (
        "cli-harness-mismatch",
        lambda: _resolver().resolve(
            _WORKFLOW,
            context="default",
            cli_overrides=(StepOverride(step="implement", profile_id="pi-reasoning-high"),),
        ),
        "harness",
    ),
    (
        "cli-unknown-step",
        lambda: _resolver().resolve(
            _WORKFLOW,
            context="default",
            cli_overrides=(StepOverride(step="ghost", profile_id="codex-review-deep"),),
        ),
        None,
    ),
)


@pytest.mark.parametrize(
    "action,expected_substring",
    [c[1:] for c in _ERROR_CASES],
    ids=[c[0] for c in _ERROR_CASES],
)
def test_error_matrix(action, expected_substring: str | None) -> None:
    with pytest.raises(PolicyResolutionError) as exc:
        action()
    if expected_substring is not None:
        assert expected_substring in str(exc.value).lower() or expected_substring in str(exc.value)


# --- ③ unmapped-context falls back + from-store overlay round-trip ---------------------


def test_unmapped_context_falls_back_and_from_store_overlay_round_trips(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # A non-default context with NO override anywhere in its chain inherits the library
    # default (the chain tail is 'default', which here carries no overlay).
    overlay = WorkflowModelPolicyOverlay(policy_id="default", contexts={})
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="unmapped")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "codex-implementation-standard"
    assert impl.source is PolicySource.LIBRARY_DEFAULT

    (tmp_path / ".dadaia").mkdir()
    store = JsonWorkflowModelPolicyStore(tmp_path)
    store.save(store.parse(_overlay({"implement": "codex-review-deep"}).to_dict()))
    resolver = WorkflowExecutionPolicyResolver(
        catalog=library_workflow_catalog(), overlay=store.load()
    )
    from_store_impl = resolver.resolve(_WORKFLOW, context="default").step("implement")
    assert from_store_impl is not None
    assert from_store_impl.model_profile == "codex-review-deep"
