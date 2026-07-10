"""W2 — build_agent_runtime maps every kind to the right port; rejects unknown.

Owns AgentRuntimePort conformance for the real adapters — justifies deleting the
protocol echo test in tests/unit/core/protocols/ (that coverage lives here instead).
"""

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
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter

_CONCRETE_TYPES: dict[AgentRuntimeKind, type] = {
    AgentRuntimeKind.FAKE: FakeAgentRuntime,
    AgentRuntimeKind.CODEX_EXEC: CodexExecAdapter,
    AgentRuntimeKind.CLAUDE_SDK: ClaudeSdkAdapter,
    AgentRuntimeKind.PI_HEADLESS: PiHeadlessAdapter,
}


@pytest.mark.parametrize("kind", list(AgentRuntimeKind))
def test_factory_returns_port_whose_kind_matches_and_concrete_type(
    kind: AgentRuntimeKind, tmp_path: Path
) -> None:
    port = build_agent_runtime(kind, cwd=tmp_path)
    assert isinstance(port, AgentRuntimePort)
    assert port.runtime_kind() is kind
    assert isinstance(port, _CONCRETE_TYPES[kind])


def test_factory_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unsupported agent runtime kind"):
        build_agent_runtime(cast(AgentRuntimeKind, "bogus-kind"))
