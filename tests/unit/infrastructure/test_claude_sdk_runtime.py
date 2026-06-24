"""W4 — ClaudeSdkAdapter stub conforms to the port, raises deferral, imports no SDK."""

from __future__ import annotations

import sys

import pytest

from dadaia_workspace.core.models.lifecycle import AgentRunRequest, AgentRuntimeKind
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.infrastructure.claude_sdk_runtime import ClaudeSdkAdapter


def _request() -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="implement",
        runtime=AgentRuntimeKind.CLAUDE_SDK,
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
    )


def test_claude_sdk_adapter_satisfies_port() -> None:
    adapter = ClaudeSdkAdapter()
    assert isinstance(adapter, AgentRuntimePort)
    assert adapter.runtime_kind() is AgentRuntimeKind.CLAUDE_SDK


def test_claude_sdk_run_raises_documented_not_implemented() -> None:
    with pytest.raises(NotImplementedError) as exc:
        ClaudeSdkAdapter().run(_request())
    message = str(exc.value)
    assert "claude-agent-sdk" in message
    assert "WS-4" in message


def test_module_does_not_import_the_sdk_at_load() -> None:
    # The stub must keep the offline build clean — no SDK imported by loading it.
    assert "claude_agent_sdk" not in sys.modules
