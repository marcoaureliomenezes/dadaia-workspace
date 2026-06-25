"""OpenCode runtime adapter (stub) for lifecycle worker requests.

Deferred. The real adapter shells ``opencode run --format json`` and reads the
nd-JSON / ACP stream for structured output. OpenCode's pre-execution permission
callback and the ``opencode run`` output schema are UNVERIFIED (release
``multiharness-engine-v0116`` SPEC §5; EPIC ``sdk-lifecycle-engine-multiharness-antislop``
WS-3 / WS-5-live). Until live-verified, this stub raises ``NotImplementedError`` so
``container.build_agent_runtime`` is total over ``AgentRuntimeKind``; a later release
swaps the body with zero call-site change. Engine enforcement for this harness
degrades to Ring-2 post-flight diff inspection (no pre-disk boundary on the headless
path). This module imports no OpenCode client at load time.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRuntimeKind,
)

_DEFERRAL = (
    "OpenCodeAdapter is a stub: the `opencode run` headless API and its "
    "pre-execution permission callback are unverified (deferred workstream "
    "WS-3/WS-5-live, release multiharness-engine-v0116). No live OpenCode "
    "execution is available yet"
)


class OpenCodeAdapter:
    """Stub ``AgentRuntimePort`` for the OpenCode harness (no live execution yet)."""

    def __init__(self, *, cwd: Path | None = None) -> None:
        self._cwd = cwd or Path.cwd()

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.OPENCODE_RUN

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        raise NotImplementedError(f"{_DEFERRAL} (requested role={request.role!r}).")
