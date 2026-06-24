"""Claude Agent SDK runtime adapter (stub) for lifecycle worker requests.

Deferred. The real adapter runs the Claude Agent SDK in-process and uses its
``can_use_tool`` callback to return ``PermissionResultDeny`` before bytes hit disk
(the Ring-1 pre-disk write boundary, reusing ``gate_policy`` as a shared pure
function). It requires the ``claude-agent-sdk`` dependency (per-token API-key
billing), which is NOT yet an approved workspace dependency. Adding it needs
operator approval plus a tech-stack memory update in a DEFINITION phase (release
``multiharness-engine-v0116`` SPEC §4; EPIC ``sdk-lifecycle-engine-multiharness-antislop``
WS-4). This module imports NO SDK at load time so the offline build stays clean;
``run`` raises ``NotImplementedError`` until the live release swaps the body with
zero call-site change.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRuntimeKind,
)

_DEFERRAL = (
    "ClaudeSdkAdapter is a stub: live integration requires the `claude-agent-sdk` "
    "dependency (per-token API-key billing), which is not yet an approved workspace "
    "dependency (deferred workstream WS-4, release multiharness-engine-v0116). No "
    "live Claude SDK execution is available yet"
)


class ClaudeSdkAdapter:
    """Stub ``AgentRuntimePort`` for the Claude Agent SDK harness (no live exec yet)."""

    def __init__(self, *, cwd: Path | None = None) -> None:
        self._cwd = cwd or Path.cwd()

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.CLAUDE_SDK

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        raise NotImplementedError(f"{_DEFERRAL} (requested role={request.role!r}).")
