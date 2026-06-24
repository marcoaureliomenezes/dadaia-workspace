"""W3 — OpenCodeAdapter stub conforms to the port and raises documented deferral."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.lifecycle import AgentRunRequest, AgentRuntimeKind
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.infrastructure.opencode_runtime import OpenCodeAdapter


def _request() -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="implement",
        runtime=AgentRuntimeKind.OPENCODE_RUN,
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
    )


def test_opencode_adapter_satisfies_port() -> None:
    adapter = OpenCodeAdapter()
    assert isinstance(adapter, AgentRuntimePort)
    assert adapter.runtime_kind() is AgentRuntimeKind.OPENCODE_RUN


def test_opencode_run_raises_documented_not_implemented() -> None:
    with pytest.raises(NotImplementedError) as exc:
        OpenCodeAdapter().run(_request())
    message = str(exc.value)
    assert "stub" in message
    assert "WS-3" in message
    assert "software-engineer" in message
