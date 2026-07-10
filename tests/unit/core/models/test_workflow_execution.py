"""Unit tests for the resolved-policy core DTOs (T-28-A-01).

These are pure ``core`` data objects threaded through every governance layer:
``WorkflowModelProfile`` (a named profile), ``ResolvedModelConfig`` (the resolved
concrete model handed to an adapter), ``WorkflowPolicyStepEntry`` (one step's
resolution), and ``WorkflowPolicySnapshot`` (the persisted per-run snapshot). The
tests assert ``to_dict``/``from_dict`` round-trip and zero I/O (the module imports
only stdlib + core).

The frozen-dataclass immutability check is SHARED across the lifecycle / workflow_execution
/ hygiene / handoff model families in one parametrized fn here (``test_all_models_are_frozen``)
rather than one fn per module.
"""

from __future__ import annotations

import dataclasses

import pytest

from dadaia_workspace.core.models.workflow_execution import (
    PolicySource,
    ResolvedModelConfig,
    WorkflowModelProfile,
    WorkflowPolicySnapshot,
    WorkflowPolicyStepEntry,
)


def _profile() -> WorkflowModelProfile:
    return WorkflowModelProfile(
        id="codex-implementation-standard",
        harness="codex",
        label="Codex implementation (standard)",
        model_id="gpt-5.5",
        effort="medium",
        purpose="Standard implementation worker.",
        availability="available",
        source="built-in",
        deprecated=False,
        replacement=None,
    )


def _resolved() -> ResolvedModelConfig:
    return ResolvedModelConfig(
        profile_id="codex-implementation-standard",
        harness="codex",
        model="gpt-5.5",
        reasoning="medium",
        source=PolicySource.LIBRARY_DEFAULT,
    )


def _snapshot() -> WorkflowPolicySnapshot:
    return WorkflowPolicySnapshot(
        workflow_id="implementation",
        policy_id="default",
        resolved_at="2026-06-26T12:00:00Z",
        source_precedence=("cli", "default-overlay", "library-default"),
        overlay_id=None,
        steps=(
            WorkflowPolicyStepEntry(
                step="implement",
                harness="codex",
                model_profile="codex-implementation-standard",
                model="gpt-5.5",
                reasoning="medium",
                source=PolicySource.LIBRARY_DEFAULT,
                fragments=("implementation.implement_tdd", "shared.write_scope"),
                output_schema="agent-run-result-v1",
            ),
            WorkflowPolicyStepEntry(
                step="review_qa",
                harness="codex",
                model_profile="codex-review-deep",
                model="gpt-5.5",
                reasoning="high",
                source=PolicySource.DEFAULT_OVERLAY,
                fragments=("implementation.qa_review",),
                output_schema="agent-run-result-v1",
            ),
        ),
        prefix_hash="abc123",
    )


@pytest.mark.parametrize(
    ("name", "build_fn", "assert_fn"),
    [
        ("profile", _profile, lambda obj: WorkflowModelProfile.from_dict(obj.to_dict()) == obj),
        (
            "profile_deprecated_with_replacement",
            lambda: dataclasses.replace(
                _profile(), deprecated=True, replacement="codex-review-deep"
            ),
            lambda obj: (
                WorkflowModelProfile.from_dict(obj.to_dict()).deprecated is True
                and WorkflowModelProfile.from_dict(obj.to_dict()).replacement == "codex-review-deep"
            ),
        ),
        (
            "resolved_model_config",
            _resolved,
            lambda obj: (
                ResolvedModelConfig.from_dict(obj.to_dict()) == obj
                and ResolvedModelConfig.from_dict(obj.to_dict()).source
                is PolicySource.LIBRARY_DEFAULT
            ),
        ),
        (
            "step_entry",
            lambda: _snapshot().steps[0],
            lambda obj: (
                WorkflowPolicyStepEntry.from_dict(obj.to_dict()) == obj
                and WorkflowPolicyStepEntry.from_dict(obj.to_dict()).fragments
                == ("implementation.implement_tdd", "shared.write_scope")
            ),
        ),
        ("snapshot", _snapshot, lambda obj: WorkflowPolicySnapshot.from_dict(obj.to_dict()) == obj),
    ],
)
def test_round_trip_table(name: str, build_fn: object, assert_fn: object) -> None:
    obj = build_fn()  # type: ignore[operator]
    assert assert_fn(obj)  # type: ignore[operator]


def test_snapshot_to_dict_is_json_shaped_and_step_lookup_works() -> None:
    snapshot = _snapshot()
    payload = snapshot.to_dict()
    # lists, not tuples, after to_dict (JSON-serializable)
    assert isinstance(payload["source_precedence"], list)
    assert isinstance(payload["steps"], list)
    assert isinstance(payload["steps"][0]["fragments"], list)
    assert payload["steps"][0]["source"] == "library-default"

    entry = snapshot.step("review_qa")
    assert entry is not None
    assert entry.reasoning == "high"
    assert snapshot.step("missing") is None


def test_policy_source_values() -> None:
    # The four precedence sources are stable string tokens.
    assert PolicySource.CLI.value == "cli"
    assert PolicySource.CONTEXT_OVERLAY.value == "context-overlay"
    assert PolicySource.DEFAULT_OVERLAY.value == "default-overlay"
    assert PolicySource.LIBRARY_DEFAULT.value == "library-default"


def test_resolved_config_to_dict_round_trips_all_sources() -> None:
    for source in PolicySource:
        resolved = dataclasses.replace(_resolved(), source=source)
        assert ResolvedModelConfig.from_dict(resolved.to_dict()) == resolved


def test_all_models_are_frozen() -> None:
    """SHARED frozen-dataclass immutability check across the lifecycle / workflow_execution
    / hygiene / handoff model families — one parametrized-style assertion sweep instead of
    one fn per module.
    """
    from dadaia_workspace.core.models.hygiene import SlopPolicy
    from dadaia_workspace.core.models.lifecycle import (
        LifecyclePhase,
        LifecycleRun,
        LifecycleRunStatus,
    )

    profile = _profile()
    with pytest.raises(dataclasses.FrozenInstanceError):
        profile.harness = "pi"  # type: ignore[misc]

    resolved = _resolved()
    with pytest.raises(dataclasses.FrozenInstanceError):
        resolved.model = "gpt-5.3-codex"  # type: ignore[misc]

    policy = SlopPolicy()
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.tmp_ttl_seconds = 10  # type: ignore[misc]

    run = LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.15",
        command="status",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="status",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        run.status = LifecycleRunStatus.COMPLETED  # type: ignore[misc]
