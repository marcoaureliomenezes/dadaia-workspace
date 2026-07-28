"""A persisted overlay naming a removed step must not brick the workspace.

Bug ``r13-release-definition-rejects-legacy-overlay`` (consumer-side validator, R13).
Four of the round's five failures — F-26, R-01, R-02, R-05 — collapse to this one cause:
``release-definition`` exited 2 before creating a run because the persisted
``workflow_model_policy`` overlay still targeted ``tasks_create``, a step this library
removed when release-definition was collapsed from seven steps to three.

That is a migration cliff. The operator upgrades, and every release-definition run dies
with no path forward but hand-editing JSON — the whole chain the product exists for
becomes unreachable.

The two sources are NOT the same and must not be treated the same:

* a ``--step-model`` / ``--step-harness`` override names a step the operator JUST typed;
  an unknown one is a typo and stays a hard, immediate rejection;
* a PERSISTED overlay is state written against an older version. Finding a step the
  current library no longer has means the library moved, not that the operator erred.

Ignoring it silently would be the other failure mode, so the entry is dropped WITH a
named advisory. Surfaced, not fatal; the anti-silent-no-op intent is kept.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.lifecycle.policy_resolver import PolicyResolutionError

pytestmark = pytest.mark.unit


def _resolver(overlay_steps: dict[str, str]):
    """A resolver whose persisted overlay targets *overlay_steps* for release_definition."""
    from dadaia_workspace.core.models.workflow_execution import WorkflowModelPolicyOverlay
    from dadaia_workspace.features.lifecycle.governed_catalog import governed_workflow_catalog
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowExecutionPolicyResolver,
    )

    overlay = WorkflowModelPolicyOverlay(
        policy_id="test-overlay",
        contexts={"default": {"release_definition": dict(overlay_steps)}},
        step_harness_overlay={},
    )
    return WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog(), overlay=overlay)


def test_a_persisted_overlay_naming_a_removed_step_does_not_abort() -> None:
    snapshot = _resolver({"tasks_create": "balanced"}).resolve(
        workflow_id="release_definition", context="default"
    )
    assert snapshot is not None, "a stale persisted overlay bricked the workflow"
    labels = {entry.step for entry in snapshot.steps}
    assert "tasks_create" not in labels, "the removed step must not be resurrected"
    assert "definition_draft" in labels, "the real steps must still resolve"


def test_the_dropped_overlay_entry_is_named_not_swallowed() -> None:
    snapshot = _resolver({"tasks_create": "balanced"}).resolve(
        workflow_id="release_definition", context="default"
    )
    warnings = " ".join(getattr(snapshot, "warnings", ()))
    assert "tasks_create" in warnings, (
        f"the stale entry was dropped silently — surfaced, not fatal, is the contract. "
        f"warnings were: {warnings!r}"
    )


def test_an_overlay_naming_a_live_step_still_applies() -> None:
    """Guard: dropping stale entries must not become dropping every entry."""
    snapshot = _resolver({"definition_draft": "codex-implementation-standard"}).resolve(
        workflow_id="release_definition", context="default"
    )
    assert not getattr(snapshot, "warnings", ()), "a valid overlay must warn about nothing"


def test_a_cli_override_naming_an_unknown_step_is_still_a_hard_error() -> None:
    """The operator just typed it; a typo must be loud and immediate."""
    from dadaia_workspace.features.lifecycle.governed_catalog import governed_workflow_catalog
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        StepOverride,
        WorkflowExecutionPolicyResolver,
    )

    resolver = WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog(), overlay=None)
    with pytest.raises(PolicyResolutionError, match="tasks_create"):
        resolver.resolve(
            workflow_id="release_definition",
            context="default",
            cli_overrides=(StepOverride(step="tasks_create", profile_id="balanced"),),
        )
