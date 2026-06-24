"""Deterministic in-process fake AgentRuntime for dry-runs and tests.

Returns a canned ``SUCCEEDED`` result without touching disk, network, or a model.
The runtime factory (``container.build_agent_runtime``) maps
``AgentRuntimeKind.FAKE`` here so a lifecycle workflow can be exercised end-to-end
with no real harness. Tests that need a specific result inject their own via
``result=``.
"""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)


class FakeAgentRuntime:
    """An ``AgentRuntimePort`` that returns deterministic output, no side effects."""

    def __init__(self, *, result: AgentRunResult | None = None) -> None:
        self._result = result

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if self._result is not None:
            return self._result
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=f"fake runtime: {request.role} (no-op)",
        )
