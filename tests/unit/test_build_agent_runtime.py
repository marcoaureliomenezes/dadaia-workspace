"""W2 — build_agent_runtime maps every kind to the right port; rejects unknown."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from dadaia_workspace.container import build_agent_runtime
from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.infrastructure.claude_sdk_runtime import ClaudeSdkAdapter
from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.opencode_runtime import OpenCodeAdapter


@pytest.mark.parametrize("kind", list(AgentRuntimeKind))
def test_factory_returns_port_whose_kind_matches(kind: AgentRuntimeKind, tmp_path: Path) -> None:
    port = build_agent_runtime(kind, cwd=tmp_path)
    assert isinstance(port, AgentRuntimePort)
    assert port.runtime_kind() is kind


def test_factory_returns_expected_concrete_types(tmp_path: Path) -> None:
    assert isinstance(build_agent_runtime(AgentRuntimeKind.FAKE), FakeAgentRuntime)
    assert isinstance(
        build_agent_runtime(AgentRuntimeKind.CODEX_EXEC, cwd=tmp_path), CodexExecAdapter
    )
    assert isinstance(
        build_agent_runtime(AgentRuntimeKind.OPENCODE_RUN, cwd=tmp_path), OpenCodeAdapter
    )
    assert isinstance(
        build_agent_runtime(AgentRuntimeKind.CLAUDE_SDK, cwd=tmp_path), ClaudeSdkAdapter
    )


def test_factory_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unsupported agent runtime kind"):
        build_agent_runtime(cast(AgentRuntimeKind, "bogus-kind"))
