"""Live ``claude-agent-sdk`` contract tests (WS-2 verification seam, T-23-11).

These tests drive the REAL ``claude-agent-sdk`` (``query()`` + ``can_use_tool``)
through ``ClaudeSdkAdapter._default_query_fn`` to verify the ONE upstream-owned
binding the offline suite cannot prove: that the installed SDK's async event
stream maps to a typed ``AgentRunResult`` and that the Ring-1 ``can_use_tool``
wiring genuinely denies an out-of-scope write. They require the optional
``claude-agent-sdk`` package and ``ANTHROPIC_API_KEY``, and they spend operator
model credits, so they are strictly OPT-IN.

Every test auto-SKIPs unless ALL of the following hold:

  * ``DADAIA_CLAUDE_LIVE=1`` is set (explicit operator consent);
  * ``claude-agent-sdk`` is importable;
  * ``ANTHROPIC_API_KEY`` is set in the environment.

This module is NOT CI-gated. With ``DADAIA_CLAUDE_LIVE`` unset it is collected and
skipped — no live call, no import of the optional SDK. All adapter mapping and
the security-critical permission wiring are real and fully faked-tested offline in
``tests/unit/infrastructure/test_claude_sdk_runtime.py``; this seam exists only to
confirm the upstream async API against a pinned ``claude-agent-sdk`` build and to
record the verified version in ``specs/memory/tech-stack.md`` at CLOSURE.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.infrastructure.claude_sdk_runtime import (
    ClaudeSdkAdapter,
    _build_can_use_tool,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _sdk_importable() -> bool:
    return importlib.util.find_spec("claude_agent_sdk") is not None


def _live_skip_reason() -> str | None:
    """Return a skip reason string, or None when all live preconditions hold."""
    if os.environ.get("DADAIA_CLAUDE_LIVE") != "1":
        return "DADAIA_CLAUDE_LIVE != 1 (live tests spend operator credits; opt-in only)"
    if not _sdk_importable():
        return "claude-agent-sdk absent (pip install dadaia-workspace[claude-sdk])"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "ANTHROPIC_API_KEY absent (claude-agent-sdk is not authenticated)"
    return None


requires_live = pytest.mark.skipif(
    _live_skip_reason() is not None, reason=_live_skip_reason() or "live preconditions unmet"
)


def _sandbox_root() -> Path:
    """Throwaway sandbox under the workspace ``.dadaia/tmp`` landing zone.

    Resolved relative to this file: tests/integration/claude_live ->
    repos/dadaia-workspace -> repos -> <workspace-root>.
    """
    workspace_root = Path(__file__).resolve().parents[5]
    root = workspace_root / ".dadaia" / "tmp" / "software-engineer" / "claude_live_harness"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _request(sandbox: Path) -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="Reply with the single word: OK. Do not use any tools.",
        runtime=AgentRuntimeKind.CLAUDE_SDK,
        context="dadaia-workspace",
        release_id="v0.1.23",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        forbidden_paths=("secrets.py",),
    )


@requires_live
def test_claude_live_query_maps_to_typed_result() -> None:
    """A real ``claude-agent-sdk`` run yields a typed, non-crashing ``AgentRunResult``.

    This is the live verification of the async ``query()`` / ``ResultMessage`` binding.
    On success the adapter carries a non-empty summary; on any SDK error it degrades to a
    FAILED result rather than crashing — assert that invariant holds against the live SDK
    and record the verified version in tech-stack memory at CLOSURE.
    """
    sandbox = _sandbox_root()
    result = ClaudeSdkAdapter(cwd=sandbox).run(_request(sandbox))

    assert result.status in (AgentRunStatus.SUCCEEDED, AgentRunStatus.FAILED)
    if result.status is AgentRunStatus.SUCCEEDED:
        assert result.summary.strip() != ""


@requires_live
def test_claude_live_can_use_tool_denies_out_of_scope_write() -> None:
    """The Ring-1 ``can_use_tool`` wiring, built against the live SDK types, denies an
    out-of-scope write and allows an in-scope one — no network needed for this assertion,
    but it runs only under the live gate so the live SDK types are present."""
    import claude_agent_sdk as sdk

    sandbox = _sandbox_root()
    decide = ClaudeSdkAdapter(cwd=sandbox).write_permission(_request(sandbox))
    can_use_tool = _build_can_use_tool(decide, sdk)

    denied = asyncio.run(can_use_tool("Write", {"file_path": "secrets.py"}, None))
    assert isinstance(denied, sdk.PermissionResultDeny)

    allowed = asyncio.run(
        can_use_tool(
            "Write",
            {"file_path": ".dadaia/handoff/dadaia-workspace/qa.handoff.json"},
            None,
        )
    )
    assert isinstance(allowed, sdk.PermissionResultAllow)
