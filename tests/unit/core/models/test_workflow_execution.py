"""Unit tests for the resolved-policy core DTOs (T-28-A-01).

These are pure ``core`` data objects threaded through every governance layer:
``WorkflowModelProfile`` (a named profile), ``ResolvedModelConfig`` (the resolved
concrete model handed to an adapter), ``WorkflowPolicyStepEntry`` (one step's
resolution), and ``WorkflowPolicySnapshot`` (the persisted per-run snapshot). The
tests assert frozen-dataclass immutability, ``to_dict``/``from_dict`` round-trip, and
zero I/O (the module imports only stdlib + core).
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


def test_profile_is_frozen() -> None:
    profile = _profile()
    with pytest.raises(dataclasses.FrozenInstanceError):
        profile.harness = "pi"  # type: ignore[misc]


def test_profile_round_trip() -> None:
    profile = _profile()
    assert WorkflowModelProfile.from_dict(profile.to_dict()) == profile


def test_profile_deprecated_with_replacement_round_trip() -> None:
    profile = dataclasses.replace(_profile(), deprecated=True, replacement="codex-review-deep")
    restored = WorkflowModelProfile.from_dict(profile.to_dict())
    assert restored.deprecated is True
    assert restored.replacement == "codex-review-deep"


def test_resolved_model_config_round_trip() -> None:
    resolved = _resolved()
    restored = ResolvedModelConfig.from_dict(resolved.to_dict())
    assert restored == resolved
    assert restored.source is PolicySource.LIBRARY_DEFAULT


def test_resolved_model_config_is_frozen() -> None:
    resolved = _resolved()
    with pytest.raises(dataclasses.FrozenInstanceError):
        resolved.model = "gpt-5.3-codex-spark"  # type: ignore[misc]


def test_step_entry_round_trip() -> None:
    entry = _snapshot().steps[0]
    restored = WorkflowPolicyStepEntry.from_dict(entry.to_dict())
    assert restored == entry
    assert restored.fragments == ("implementation.implement_tdd", "shared.write_scope")


def test_snapshot_round_trip() -> None:
    snapshot = _snapshot()
    restored = WorkflowPolicySnapshot.from_dict(snapshot.to_dict())
    assert restored == snapshot


def test_snapshot_to_dict_is_json_shaped() -> None:
    payload = _snapshot().to_dict()
    # lists, not tuples, after to_dict (JSON-serializable)
    assert isinstance(payload["source_precedence"], list)
    assert isinstance(payload["steps"], list)
    assert isinstance(payload["steps"][0]["fragments"], list)
    assert payload["steps"][0]["source"] == "library-default"


def test_snapshot_step_lookup() -> None:
    snapshot = _snapshot()
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
