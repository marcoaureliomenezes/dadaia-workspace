"""Deterministic in-process fake AgentRuntime for dry-runs and tests.

Returns a canned ``SUCCEEDED`` result without touching disk, network, or a model.
The runtime factory (``container.build_agent_runtime``) maps
``AgentRuntimeKind.FAKE`` here so a lifecycle workflow can be exercised end-to-end
with no real harness. Tests that need a specific result inject their own via
``result=``.
"""

from __future__ import annotations

from collections.abc import Callable

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.models.workflow_execution import ResolvedModelConfig


class FakeAgentRuntime:
    """An ``AgentRuntimePort`` that returns deterministic output, no side effects.

    Records every request it receives in :attr:`received_requests` so tests can assert
    that policy resolution threaded the right ``resolved_model`` into each step's request
    — without a live provider (T-28-A-06). An optional ``on_run`` hook fires before each
    canned result, letting a test mutate external state *between* steps (used by the AC-6
    in-flight-mutation demo in T-28-A-10).
    """

    def __init__(
        self,
        *,
        result: AgentRunResult | None = None,
        on_run: Callable[[AgentRunRequest], None] | None = None,
    ) -> None:
        self._result = result
        self._on_run = on_run
        self.received_requests: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    @property
    def received_models(self) -> list[ResolvedModelConfig | None]:
        """The resolved model config recorded for each request, in call order."""
        return [req.resolved_model for req in self.received_requests]

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        if self._on_run is not None:
            self._on_run(request)
        if self._result is not None:
            return self._result
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=f"fake runtime: {request.role} (no-op)",
        )
