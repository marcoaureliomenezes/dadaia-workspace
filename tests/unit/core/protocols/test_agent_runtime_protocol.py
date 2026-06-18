"""Unit tests for the agent runtime protocol contract."""

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort


class FakeRuntime:
    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=f"handled {request.role}",
            structured_output={"release_id": request.release_id},
        )


def test_fake_runtime_satisfies_agent_runtime_port() -> None:
    runtime = FakeRuntime()
    request = AgentRunRequest(
        role="software-engineer",
        prompt="Implement a bounded task.",
        runtime=AgentRuntimeKind.FAKE,
        context="dadaia-workspace",
        release_id="v0.1.15",
    )

    assert isinstance(runtime, AgentRuntimePort)
    assert runtime.runtime_kind() == AgentRuntimeKind.FAKE
    result = runtime.run(request)
    assert result.status == AgentRunStatus.SUCCEEDED
    assert result.structured_output == {"release_id": "v0.1.15"}
