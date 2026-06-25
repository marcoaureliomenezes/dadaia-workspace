"""WS-4 — ClaudeSdkAdapter: Ring-1 write boundary + result mapping via injected transport.

The Claude Agent SDK is an optional operator-installed extra; these tests inject the
transport seam (`query_fn`) so the security-critical permission logic and the
AgentRunResult mapping are exercised without the package installed.
"""

from __future__ import annotations

import sys

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.infrastructure.claude_sdk_runtime import (
    ClaudeRunOutput,
    ClaudeSdkAdapter,
    WritePermission,
)


def _request() -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="implement",
        runtime=AgentRuntimeKind.CLAUDE_SDK,
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        forbidden_paths=("repos/dadaia-workspace/secrets.py",),
    )


def test_adapter_satisfies_port() -> None:
    adapter = ClaudeSdkAdapter()
    assert isinstance(adapter, AgentRuntimePort)
    assert adapter.runtime_kind() is AgentRuntimeKind.CLAUDE_SDK


def test_ring1_write_permission_mirrors_scope() -> None:
    decide = ClaudeSdkAdapter().write_permission(_request())
    assert decide(".dadaia/handoff/dadaia-workspace/qa.handoff.json") is True
    assert decide("repos/dadaia-workspace/secrets.py") is False  # forbidden
    assert decide("repos/dadaia-workspace/src/app.py") is False  # outside allowed


def test_run_maps_approved_output_to_succeeded_result() -> None:
    def query_fn(prompt: str, permission: WritePermission) -> ClaudeRunOutput:
        # The transport is handed the Ring-1 decider; an out-of-scope write is denied.
        assert permission(".dadaia/handoff/dadaia-workspace/qa.handoff.json") is True
        assert permission("repos/dadaia-workspace/secrets.py") is False
        return ClaudeRunOutput(
            summary="done",
            verdict="APPROVED",
            artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
            changed_paths=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        )

    result = ClaudeSdkAdapter(query_fn=query_fn).run(_request())
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output["verdict"] == "APPROVED"
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/qa.handoff.json",)
    assert result.structured_output["changed_paths"].endswith("qa.handoff.json")


def test_run_returns_failed_when_sdk_absent() -> None:
    def query_fn(prompt: str, permission: WritePermission) -> ClaudeRunOutput:
        raise ImportError("Claude execution requires the optional `claude-agent-sdk` package")

    result = ClaudeSdkAdapter(query_fn=query_fn).run(_request())
    assert result.status is AgentRunStatus.FAILED
    assert result.error is not None
    assert "claude-agent-sdk" in result.error


def test_run_rejects_mismatched_runtime() -> None:
    bad = AgentRunRequest(
        role="x",
        prompt="y",
        runtime=AgentRuntimeKind.CODEX_EXEC,
        context="c",
        release_id="r",
    )
    result = ClaudeSdkAdapter(query_fn=lambda p, perm: ClaudeRunOutput(summary="")).run(bad)
    assert result.status is AgentRunStatus.FAILED
    assert "unsupported runtime" in (result.error or "")


def test_run_propagates_transport_error_as_failed() -> None:
    def query_fn(prompt: str, permission: WritePermission) -> ClaudeRunOutput:
        return ClaudeRunOutput(summary="boom", error="model refused")

    result = ClaudeSdkAdapter(query_fn=query_fn).run(_request())
    assert result.status is AgentRunStatus.FAILED
    assert result.error == "model refused"


def test_module_does_not_import_the_sdk_at_load() -> None:
    assert "claude_agent_sdk" not in sys.modules
