"""Agent runtime port for bounded lifecycle worker execution."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRuntimeKind,
)


@runtime_checkable
class AgentRuntimePort(Protocol):
    """Execute one bounded agent worker request.

    Implementations live outside ``core``. Lifecycle services use this port so
    Python-owned workflow state can validate outputs before any transition.
    """

    def runtime_kind(self) -> AgentRuntimeKind:
        """Return the concrete runtime kind behind the port."""
        ...

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        """Execute a bounded agent request and return structured output."""
        ...
