"""Live Codex Layer-2 adapter contract test (T-23-12, WS-3 live half).

Distinct from the existing Layer-1 hook tests in this directory
(``test_codex_live_contract.py``, which verify hook firing through the codex
runtime): this test drives the REAL ``codex exec`` binary through the
**Layer-2** ``CodexExecAdapter`` (the lifecycle worker seam behind
``AgentRuntimePort``), asserting it returns a typed, non-crashing
``AgentRunResult``.

It spends operator model credits, so it is strictly OPT-IN. The test auto-SKIPs
unless ALL of the following hold:

  * ``DADAIA_CODEX_LIVE=1`` is set (explicit operator consent);
  * the ``codex`` binary is present on PATH (or via ``CODEX_BIN``);
  * ``~/.codex/auth.json`` is present (codex is authenticated).

This module is NOT CI-gated. With ``DADAIA_CODEX_LIVE`` unset it is collected and
skipped — no live call. The retained behavior suite covers the offline lifecycle
and harness wiring; this seam exists only to confirm the live
``codex exec --output-last-message`` contract against a pinned ``codex`` build
and to record the verified version in ``specs/memory/tech-stack.md`` at CLOSURE.

The sandbox runs under ``.dadaia/tmp/`` with an isolated ``CODEX_HOME`` (auth
copied, chmod 600) — the user's real ``~/.codex`` is never modified.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter, CodexExecConfig
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

from . import _probe_lib as lib

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _live_skip_reason() -> str | None:
    """Return a skip reason string, or None when all live preconditions hold."""
    if os.environ.get("DADAIA_CODEX_LIVE") != "1":
        return "DADAIA_CODEX_LIVE != 1 (live tests spend operator credits; opt-in only)"
    if lib.codex_binary() is None:
        return "codex binary absent"
    if not lib.codex_auth_path().is_file():
        return "~/.codex/auth.json absent (codex not authenticated)"
    return None


requires_live = pytest.mark.skipif(
    _live_skip_reason() is not None, reason=_live_skip_reason() or "live preconditions unmet"
)


def _sandbox_root() -> Path:
    """Throwaway sandbox root under the workspace ``.dadaia/tmp`` landing zone.

    Resolved relative to this test file: tests/integration/codex_live ->
    repos/dadaia-workspace -> repos -> <workspace-root>.
    """
    workspace_root = Path(__file__).resolve().parents[5]
    root = workspace_root / ".dadaia" / "tmp" / "software-engineer" / "codex_adapter_live_harness"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def sandbox() -> lib.CodexSandbox:
    """An isolated CODEX_HOME sandbox under ``.dadaia/tmp`` (auth copied, chmod 600)."""
    return lib.CodexSandbox(root=_sandbox_root())


@requires_live
def test_codex_exec_adapter_maps_live_run_to_result(sandbox: lib.CodexSandbox) -> None:
    """A real ``codex exec`` run through the Layer-2 adapter yields a typed result.

    Verifies the ``CodexExecAdapter`` non-crashing contract against the live binary:
    the adapter returns a typed ``AgentRunResult`` (SUCCEEDED on a clean run, FAILED
    on a non-zero/timeout), with ``changed_paths`` sourced from the real git diff
    (the injected ``GitSubprocessClient``), never from a model self-report.
    """
    fixture = sandbox.root / "adapter_fixture"
    sandbox.git_init(fixture)

    adapter = CodexExecAdapter(
        CodexExecConfig(
            cwd=fixture,
            codex_bin=lib.codex_binary() or "codex",
            timeout_seconds=120,
        ),
        environ=sandbox.env(),
        git=GitSubprocessClient(),
    )
    request = AgentRunRequest(
        role="software-engineer",
        prompt="Reply with the single word: OK. Do not modify any files.",
        runtime=AgentRuntimeKind.CODEX_EXEC,
        context="dadaia-workspace",
        release_id="v0.1.23",
    )

    result = adapter.run(request)

    # The adapter never crashes on the live run; the result is always typed.
    assert result.status in (AgentRunStatus.SUCCEEDED, AgentRunStatus.FAILED)
    if result.status is AgentRunStatus.SUCCEEDED:
        assert result.summary.strip() != ""
        # changed_paths is always present (git-diff sourced) once a git client is wired.
        assert "changed_paths" in result.structured_output
