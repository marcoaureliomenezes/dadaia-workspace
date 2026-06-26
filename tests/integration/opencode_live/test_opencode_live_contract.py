"""Live `opencode` contract tests (T-23-08, WS-1 verification seam).

These tests drive the REAL ``opencode`` binary through the ``OpenCodeAdapter`` to
verify the ONE upstream-owned binding the offline suite cannot prove: the live
``opencode run --format json`` event schema (the success-path message/part shapes
ADR-23-2 leaves defensive). They require an installed ``opencode`` binary and
provider auth, and they spend operator model credits, so they are strictly
OPT-IN.

Every test auto-SKIPs unless ALL of the following hold:

  * ``DADAIA_OPENCODE_LIVE=1`` is set (explicit operator consent);
  * the ``opencode`` binary is present on PATH (or via ``OPENCODE_BIN``);
  * an opencode ``auth.json`` is present (a provider is authenticated).

This module is NOT CI-gated. With ``DADAIA_OPENCODE_LIVE`` unset it is collected
and skipped — no live call. All adapter mapping/integration logic is real and
fully faked-tested offline in ``tests/unit/infrastructure/test_opencode_runtime.py``;
this seam exists only to confirm the upstream schema against a pinned ``opencode``
build and to record the verified version in ``specs/memory/tech-stack.md`` at
CLOSURE.
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
from dadaia_workspace.infrastructure.opencode_runtime import OpenCodeAdapter, OpenCodeConfig

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _opencode_binary() -> str | None:
    explicit = os.environ.get("OPENCODE_BIN")
    if explicit:
        return explicit
    return shutil.which("opencode")


def _auth_present() -> bool:
    """True when an opencode credentials file exists in any standard location."""
    candidates: list[Path] = []
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        candidates.append(Path(xdg) / "opencode" / "auth.json")
    home = os.environ.get("HOME")
    if home:
        candidates.append(Path(home) / ".local" / "share" / "opencode" / "auth.json")
    return any(path.is_file() for path in candidates)


def _live_skip_reason() -> str | None:
    """Return a skip reason string, or None when all live preconditions hold."""
    if os.environ.get("DADAIA_OPENCODE_LIVE") != "1":
        return "DADAIA_OPENCODE_LIVE != 1 (live tests spend operator credits; opt-in only)"
    if _opencode_binary() is None:
        return "opencode binary absent (install opencode or set OPENCODE_BIN)"
    if not _auth_present():
        return "opencode auth.json absent (opencode is not authenticated)"
    return None


requires_live = pytest.mark.skipif(
    _live_skip_reason() is not None, reason=_live_skip_reason() or "live preconditions unmet"
)


def _sandbox_root() -> Path:
    """Throwaway sandbox under the workspace ``.dadaia/tmp`` landing zone.

    Resolved relative to this file: tests/integration/opencode_live ->
    repos/dadaia-workspace -> repos -> <workspace-root>.
    """
    workspace_root = Path(__file__).resolve().parents[5]
    root = workspace_root / ".dadaia" / "tmp" / "software-engineer" / "opencode_live_harness"
    root.mkdir(parents=True, exist_ok=True)
    return root


@requires_live
def test_opencode_json_stream_maps_to_result() -> None:
    """A real ``opencode run --format json`` run yields a typed, non-crashing result.

    This is the live verification of the message/part event schema the offline
    suite covers defensively. If ``opencode`` emits an unexpected shape, the
    adapter's defensive parser degrades to a raw-stdout summary (SUCCEEDED) or maps
    an error event to FAILED rather than crashing — assert that invariant holds
    against the live binary and record the verified version in tech-stack memory at
    CLOSURE.
    """
    sandbox = _sandbox_root()
    model = os.environ.get("DADAIA_OPENCODE_MODEL")
    adapter = OpenCodeAdapter(
        config=OpenCodeConfig(
            cwd=sandbox,
            opencode_bin=_opencode_binary() or "opencode",
            model=model,
            timeout_seconds=120,
        ),
    )
    request = AgentRunRequest(
        role="software-engineer",
        prompt="Reply with the single word: OK. Do not use any tools.",
        runtime=AgentRuntimeKind.OPENCODE_RUN,
        context="dadaia-workspace",
        release_id="v0.1.23",
    )

    result = adapter.run(request)

    # The adapter never crashes on the live stream; the result is always typed.
    assert result.status in (AgentRunStatus.SUCCEEDED, AgentRunStatus.FAILED)
    if result.status is AgentRunStatus.SUCCEEDED:
        assert result.summary.strip() != ""
