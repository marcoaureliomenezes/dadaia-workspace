"""W1 — AgentRuntimeKind members + request round-trips."""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import AgentRunRequest, AgentRuntimeKind


def test_runtime_kind_members() -> None:
    assert {k.value for k in AgentRuntimeKind} == {
        "fake",
        "codex_exec",
        "claude_sdk",
        "pi_headless",
    }


def test_pi_headless_value_roundtrip() -> None:
    assert AgentRuntimeKind("pi_headless") is AgentRuntimeKind.PI_HEADLESS


def test_pi_headless_request_roundtrips() -> None:
    request = AgentRunRequest(
        role="software-engineer",
        prompt="do work",
        runtime=AgentRuntimeKind.PI_HEADLESS,
        context="dadaia-workspace",
        release_id="pi-fourth-harness-v1",
    )
    restored = AgentRunRequest.from_dict(request.to_dict())
    assert restored.runtime is AgentRuntimeKind.PI_HEADLESS
    assert restored == request


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
