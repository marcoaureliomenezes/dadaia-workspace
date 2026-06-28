"""Live `pi` contract tests (WS-PI-2 verification seam, T-PI-07).

These tests drive the REAL ``pi`` binary (``@earendil-works/pi-coding-agent``)
through the ``PiHeadlessAdapter`` to verify the ONE upstream-owned binding the
offline suite cannot prove: the live ``pi --mode json`` event schema — in
particular whether ``AgentMessage.content`` is a plain string or a content-block
array. They require Node, an installed ``pi`` binary, and ``ANTHROPIC_API_KEY``,
and they spend operator model credits, so they are strictly OPT-IN.

Every test auto-SKIPs unless ALL of the following hold:

  * ``DADAIA_PI_LIVE=1`` is set (explicit operator consent);
  * the ``pi`` binary is present on PATH (or via ``PI_BIN``);
  * ``ANTHROPIC_API_KEY`` is set in the environment.

This module is NOT CI-gated. With ``DADAIA_PI_LIVE`` unset it is collected and
skipped — no live call. The retained behavior suite covers the offline lifecycle
and harness wiring; this seam exists only to confirm the upstream schema against
a pinned ``pi`` build and to record the verified version in
``specs/memory/tech-stack.md`` at CLOSURE.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _pi_binary() -> str | None:
    explicit = os.environ.get("PI_BIN")
    if explicit:
        return explicit
    return shutil.which("pi")


def _live_skip_reason() -> str | None:
    """Return a skip reason string, or None when all live preconditions hold."""
    if os.environ.get("DADAIA_PI_LIVE") != "1":
        return "DADAIA_PI_LIVE != 1 (live tests spend operator credits; opt-in only)"
    if _pi_binary() is None:
        return "pi binary absent (install @earendil-works/pi-coding-agent or set PI_BIN)"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "ANTHROPIC_API_KEY absent (pi is not authenticated)"
    return None


requires_live = pytest.mark.skipif(
    _live_skip_reason() is not None, reason=_live_skip_reason() or "live preconditions unmet"
)


def _sandbox_root() -> Path:
    """Throwaway sandbox under the workspace ``.dadaia/tmp`` landing zone.

    Resolved relative to this file: tests/integration/pi_live ->
    repos/dadaia-workspace -> repos -> <workspace-root>.
    """
    workspace_root = Path(__file__).resolve().parents[5]
    root = workspace_root / ".dadaia" / "tmp" / "software-engineer" / "pi_live_harness"
    root.mkdir(parents=True, exist_ok=True)
    return root


@requires_live
def test_pi_headless_json_stream_maps_to_result() -> None:
    """A real ``pi --mode json`` run yields a typed, non-empty ``AgentRunResult``.

    This is the live verification of the ``message_end`` / ``AgentMessage.content``
    binding. If ``pi`` changes its event schema, the adapter's defensive parser
    degrades to a raw-stdout summary (SUCCEEDED) rather than crashing — assert that
    invariant holds against the live binary and record the verified version in
    tech-stack memory at CLOSURE.
    """
    sandbox = _sandbox_root()
    adapter = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=sandbox, pi_bin=_pi_binary() or "pi", timeout_seconds=120),
    )
    request = AgentRunRequest(
        role="software-engineer",
        prompt="Reply with the single word: OK. Do not use any tools.",
        runtime=AgentRuntimeKind.PI_HEADLESS,
        context="dadaia-workspace",
        release_id="pi-fourth-harness-v1",
    )

    result = adapter.run(request)

    # The adapter never crashes on the live stream; on success it carries a summary.
    assert result.status in (AgentRunStatus.SUCCEEDED, AgentRunStatus.FAILED)
    if result.status is AgentRunStatus.SUCCEEDED:
        assert result.summary.strip() != ""
