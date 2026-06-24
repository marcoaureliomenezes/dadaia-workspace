"""W1 — AgentRuntimeKind gains CLAUDE_SDK + OPENCODE_RUN; request round-trips."""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import AgentRunRequest, AgentRuntimeKind


def test_runtime_kind_members() -> None:
    assert {k.value for k in AgentRuntimeKind} == {
        "fake",
        "codex_exec",
        "claude_sdk",
        "opencode_run",
    }


def test_runtime_kind_value_roundtrip() -> None:
    for kind in AgentRuntimeKind:
        assert AgentRuntimeKind(kind.value) is kind


def test_agent_run_request_roundtrips_every_runtime() -> None:
    for kind in AgentRuntimeKind:
        request = AgentRunRequest(
            role="software-engineer",
            prompt="do work",
            runtime=kind,
            context="dadaia-workspace",
            release_id="multiharness-engine-v0116",
        )
        restored = AgentRunRequest.from_dict(request.to_dict())
        assert restored.runtime is kind
        assert restored == request
