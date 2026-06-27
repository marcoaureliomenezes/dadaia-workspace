"""Real `pi` command smoke — proves the headless command actually executes (T-31-B-02).

This is the regression guard the frozen-fake unit test could not provide for bug
``pi-headless-command-trailing-dash-breaks-layer2``: the unit test
(``tests/unit/infrastructure/test_pi_runtime.py::test_pi_adapter_builds_controlled_command_and_env``)
asserts the argv ends ``-p`` with no trailing ``-`` against a *fake* runner, so a
malformed real command could once ship green. Here we run the **real** ``pi`` binary
through :class:`PiHeadlessAdapter` and prove the command executes WITHOUT the
"Unknown option: -" failure, returning a typed :class:`AgentRunResult` (SPEC v0.1.31
Cluster 3 / A13; L5 — adopt+verify the ``c8513fa5`` fix, never re-fix it).

It spends operator model credits, so it is strictly OPT-IN. The test auto-SKIPs unless
ALL of the following hold (shared with the Wave-C real-worker e2e per GRILL D-4):

  * ``DADAIA_E2E_REAL_WORKER=1`` is set (explicit operator consent — the single Wave-B/C
    gate flag);
  * the ``pi`` binary is present on PATH (or via ``PI_BIN``);
  * ``ANTHROPIC_API_KEY`` is set in the environment (pi is authenticated).

This module is NOT CI-gated. With ``DADAIA_E2E_REAL_WORKER`` unset it is collected and
SKIPPED — no live call, no credit spent — so a default ``pytest`` / CI run stays fully
faked + green.

Run it on demand (from the dadaia-workspace repo root, with the workspace venv):

    DADAIA_E2E_REAL_WORKER=1 PI_BIN="$(command -v pi)" ANTHROPIC_API_KEY=... \\
      /home/marco/workspace/dadaia/.dadaia/.venv/bin/pytest -p no:cacheprovider -q \\
      tests/integration/pi_live/test_pi_command_smoke.py
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
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


def _real_worker_skip_reason() -> str | None:
    """Return a skip reason string, or None when all live preconditions hold.

    Gated on the SHARED ``DADAIA_E2E_REAL_WORKER`` flag (D-4) plus the live ``pi``
    preconditions — identical to the Wave-C real-worker e2e so a single operator
    opt-in enables both.
    """
    if os.environ.get("DADAIA_E2E_REAL_WORKER") != "1":
        return "DADAIA_E2E_REAL_WORKER != 1 (real-worker tests spend operator credits; opt-in only)"
    if _pi_binary() is None:
        return "pi binary absent (install @earendil-works/pi-coding-agent or set PI_BIN)"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "ANTHROPIC_API_KEY absent (pi is not authenticated)"
    return None


requires_real_worker = pytest.mark.skipif(
    _real_worker_skip_reason() is not None,
    reason=_real_worker_skip_reason() or "real-worker preconditions unmet",
)


def _sandbox_root() -> Path:
    """Throwaway sandbox under the workspace ``.dadaia/tmp`` landing zone.

    Resolved relative to this file: tests/integration/pi_live ->
    repos/dadaia-workspace -> repos -> <workspace-root>.
    """
    workspace_root = Path(__file__).resolve().parents[5]
    root = workspace_root / ".dadaia" / "tmp" / "software-engineer" / "pi_command_smoke_harness"
    root.mkdir(parents=True, exist_ok=True)
    return root


@requires_real_worker
def test_real_pi_command_executes_without_unknown_option_dash() -> None:
    """The real ``pi`` command runs end-to-end — no "Unknown option: -" (A13).

    Proves the adopted ``c8513fa5`` argv fix (``-p -`` → ``-p``) works against the
    *installed* ``pi`` build: the adapter returns a typed :class:`AgentRunResult`, and
    crucially neither its ``summary`` nor its ``error`` carries the "Unknown option: -"
    failure that BLOCKed every PI Layer-2 step before the fix.
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
        release_id="v0.1.31",
    )

    result = adapter.run(request)

    # The adapter always returns a typed result and never crashes on the live stream.
    assert isinstance(result, AgentRunResult)
    assert result.status in (AgentRunStatus.SUCCEEDED, AgentRunStatus.FAILED)
    # The command was accepted by the installed pi binary: the trailing-dash regression
    # (bug pi-headless-command-trailing-dash-breaks-layer2) surfaced as exactly this
    # substring in the adapter's error/summary, so its absence is the regression guard.
    haystack = f"{result.summary or ''}\n{result.error or ''}"
    assert "Unknown option: -" not in haystack
    # On a clean run the adapter carries a non-empty summary.
    if result.status is AgentRunStatus.SUCCEEDED:
        assert result.summary.strip() != ""
