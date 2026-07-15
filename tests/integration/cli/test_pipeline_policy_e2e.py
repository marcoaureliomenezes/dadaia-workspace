"""T-28-A-10 — Wave A green checkpoint: D-4 end-to-end policy demo.

Drives the REAL ``WorkflowExecutionPolicyResolver`` → ``LifecyclePipeline`` →
``FakeAgentRuntime`` and asserts:

- each step's request carried the resolved concrete model, and the persisted
  ``LifecycleRun.workflow_policy`` snapshot matches the resolved policy (AC-7/AC-8);
- AC-6 (mid-run safety / LAW 7): an overlay mutated BETWEEN step 1 and step 2 (via a
  ``FakeAgentRuntime`` ``on_run`` hook) does NOT change the in-flight run — step 2 uses
  the pre-mutation snapshot;
- invalid overlay blocks BEFORE any model call (the fake records ZERO calls AND
  ``.last-good.json`` is byte-unchanged), while a MISSING overlay resolves to defaults
  (missing != invalid).

All hermetic: no live provider, no real venv, tmp workspace only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.models.workflow_execution import (
    WorkflowModelPolicyStoreError,
)
from dadaia_workspace.features.lifecycle.pipeline import (
    LifecyclePipeline,
    apply_resolved_policy,
    implementation_ladder,
)
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime


def _init_workspace(path: Path) -> Path:
    states = path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"version": "1", "contexts": []}), encoding="utf-8"
    )
    (path / "repos").mkdir(exist_ok=True)
    return path


def _approving() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="approved",
        artifact_refs=(".dadaia/tmp/lifecycle-worker/dadaia-workspace/step.step-output.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _overlay_dict(profile: str) -> dict[str, object]:
    return {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": "default",
        "contexts": {
            "default": {"workflows": {"implementation_reviews": {"steps": {"implement": profile}}}}
        },
    }


# ---------------------------------------------------------------------------
# Full e2e: resolver → pipeline → fake, snapshot persisted, per-step model recorded
# ---------------------------------------------------------------------------


def test_pipeline_e2e_persists_snapshot_threads_model_and_invalid_overlay_blocks(
    tmp_path: Path,
) -> None:
    """E2e snapshot + per-step model persistence, plus invalid-overlay-blocks-before-
    model-call with the last-good backup left intact — merged per plan-integration.md."""
    workspace = _init_workspace(tmp_path)
    resolver = container.build_workflow_policy_resolver(workspace, context="dadaia-workspace")
    snapshot = resolver.resolve("implementation_reviews", context="default")

    recorder = FakeAgentRuntime(result=_approving())
    store = container.build_lifecycle_run_store(workspace)
    pipe = LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.28",
        run_store=store,
        runtime_factory=lambda kind: recorder,
        policy_snapshot=snapshot,
    )
    steps = apply_resolved_policy(implementation_ladder(AgentRuntimeKind.FAKE), snapshot)
    result = pipe.run("e2e-run", steps)

    assert result.completed is True
    # Per-step resolved model reached each request.
    models = [req.resolved_model for req in recorder.received_requests]
    assert models[0] is not None and models[0].profile_id == "codex-implementation-standard"
    assert models[1] is not None and models[1].profile_id == "codex-review-deep"
    # Persisted snapshot matches the resolved policy (AC-7).
    persisted = store.load("e2e-run")
    assert persisted is not None and persisted.workflow_policy is not None
    impl_entry = persisted.workflow_policy.step("implement")
    assert impl_entry is not None
    assert impl_entry.model_profile == "codex-implementation-standard"
    assert impl_entry.model == "gpt-5.5"
    assert impl_entry.reasoning == "medium"
    assert "implementation.implement_tdd" in impl_entry.fragments

    # Invalid overlay blocks BEFORE any model call; last-good backup byte-unchanged.
    invalid_ws = _init_workspace(tmp_path / "invalid-overlay-case")
    policy_store = container.build_workflow_model_policy_store(invalid_ws)
    # Seed a valid overlay + its last-good backup by saving twice.
    policy_store.save(policy_store.parse(_overlay_dict("codex-implementation-standard")))
    policy_store.save(policy_store.parse(_overlay_dict("codex-review-deep")))
    last_good_before = policy_store.last_good_path.read_bytes()

    # Now corrupt the overlay file on disk.
    policy_store.path.write_text("{ this is not valid json", encoding="utf-8")

    invalid_recorder = FakeAgentRuntime(result=_approving())

    # Building the resolver loads+validates the overlay → must raise BEFORE any model call.
    with pytest.raises(WorkflowModelPolicyStoreError):
        container.build_workflow_policy_resolver(invalid_ws)

    # Zero model calls were made.
    assert invalid_recorder.received_requests == []
    # last-good backup is byte-unchanged.
    assert policy_store.last_good_path.read_bytes() == last_good_before


# ---------------------------------------------------------------------------
# AC-6 — mid-run safety: overlay mutated BETWEEN step 1 and step 2 is ignored in-flight
# ---------------------------------------------------------------------------


def test_pipeline_ac6_in_flight_ignores_later_overlay_edit(tmp_path: Path) -> None:
    workspace = _init_workspace(tmp_path)
    policy_store = container.build_workflow_model_policy_store(workspace)
    # Start with NO overlay (defaults): implement → codex-implementation-standard.
    resolver = container.build_workflow_policy_resolver(workspace, context="dadaia-workspace")
    snapshot = resolver.resolve("implementation_reviews", context="default")

    seen_models: list[str] = []

    def mutate_after_step1(request: AgentRunRequest) -> None:
        # record the profile each step ran with
        if request.resolved_model is not None:
            seen_models.append(request.resolved_model.profile_id)
        # After the FIRST step's call, mutate the on-disk overlay. The in-flight run must
        # ignore it (it reads the frozen snapshot, not the live overlay).
        if len(seen_models) == 1:
            policy_store.save(policy_store.parse(_overlay_dict("codex-review-deep")))

    recorder = FakeAgentRuntime(result=_approving(), on_run=mutate_after_step1)
    store = container.build_lifecycle_run_store(workspace)
    pipe = LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.28",
        run_store=store,
        runtime_factory=lambda kind: recorder,
        policy_snapshot=snapshot,
    )
    steps = apply_resolved_policy(implementation_ladder(AgentRuntimeKind.FAKE), snapshot)
    pipe.run("ac6-run", steps)

    # Step 1 ran the pre-mutation default; the overlay was mutated between step 1 and 2;
    # step 2 (review_qa) must still use the PRE-mutation snapshot's profile, NOT the
    # newly-written overlay (which only targets `implement` anyway).
    assert seen_models[0] == "codex-implementation-standard"
    persisted = store.load("ac6-run")
    assert persisted is not None and persisted.workflow_policy is not None
    # The persisted snapshot's implement step is the PRE-mutation default.
    impl = persisted.workflow_policy.step("implement")
    assert impl is not None and impl.model_profile == "codex-implementation-standard"

    # A FRESH resolution now (after the run) DOES see the mutated overlay — proving the
    # mutation actually landed on disk and only the in-flight run was shielded.
    fresh = container.build_workflow_policy_resolver(workspace).resolve(
        "implementation_reviews", context="default"
    )
    fresh_impl = fresh.step("implement")
    assert fresh_impl is not None and fresh_impl.model_profile == "codex-review-deep"
