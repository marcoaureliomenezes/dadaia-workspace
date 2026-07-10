"""W1 — AgentRuntimeKind members + request round-trips."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.lifecycle import AgentRunRequest, AgentRuntimeKind


def test_runtime_kind_members() -> None:
    assert {k.value for k in AgentRuntimeKind} == {
        "fake",
        "codex_exec",
        "claude_sdk",
        "pi_headless",
    }


@pytest.mark.parametrize("kind", list(AgentRuntimeKind))
def test_agent_run_request_roundtrips_every_runtime_kind(kind: AgentRuntimeKind) -> None:
    # Every AgentRuntimeKind value round-trips through both the enum constructor and
    # AgentRunRequest.to_dict/from_dict.
    assert AgentRuntimeKind(kind.value) is kind
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
