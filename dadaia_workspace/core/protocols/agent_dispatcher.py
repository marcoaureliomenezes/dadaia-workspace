"""AgentDispatcher protocol — runtime-specific stage invocation."""

from typing import Protocol

from dadaia_workspace.core.models.run_state import (
    DispatcherCapabilities,
    StageInvocation,
    StageResult,
)


class AgentDispatcher(Protocol):
    def capabilities(self) -> DispatcherCapabilities: ...
    def dispatch(self, invocation: StageInvocation) -> StageResult: ...
    def dispatch_parallel(
        self, invocations: tuple[StageInvocation, ...]
    ) -> tuple[StageResult, ...]: ...
