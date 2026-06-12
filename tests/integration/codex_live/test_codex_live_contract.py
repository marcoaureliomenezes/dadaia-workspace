"""Live Codex contract tests (WS-CDX-VERIFY, T-013-08).

These tests drive the REAL ``codex`` binary against trusted throwaway workspaces
to verify the Codex hook contract the runtime-fidelity audit left unproven. They
spend operator model credits, so they are strictly OPT-IN: every test auto-SKIPs
unless ALL of the following hold:

  * ``DADAIA_CODEX_LIVE=1`` is set in the environment (explicit operator consent);
  * the ``codex`` binary is present on PATH (or via ``CODEX_BIN``);
  * ``~/.codex/auth.json`` is present (codex is authenticated).

All fixtures regenerate under ``.dadaia/tmp/`` — never inside the repo tree — in an
isolated ``CODEX_HOME`` that copies in only ``auth.json`` (chmod 600). The user's
``~/.codex`` is never modified.

Verified facts encoded as assertions (see FACTS.md):
  * headless ``codex exec`` does NOT fire command hooks (documents the known
    defect — bug ``codex-exec-hooks-do-not-fire-headless``);
  * the interactive ``codex`` TUI DOES fire all four event hooks;
  * the interactive TUI honors the legacy ``{"decision":"block"}`` envelope and
    blocks a FROZEN ``specs/_archive/`` write.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

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
    root = workspace_root / ".dadaia" / "tmp" / "software-engineer" / "codex_live_harness"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def sandbox() -> lib.CodexSandbox:
    """An isolated CODEX_HOME sandbox under ``.dadaia/tmp`` (auth copied, chmod 600)."""
    return lib.CodexSandbox(root=_sandbox_root())


@requires_live
def test_headless_exec_hooks_do_not_fire(sandbox: lib.CodexSandbox) -> None:
    """Headless ``codex exec`` does NOT fire command hooks.

    Documents the known defect (bug ``codex-exec-hooks-do-not-fire-headless``):
    the model performs the apply_patch (the tool fires and the file is written),
    but NO PreToolUse/PostToolUse/SessionStart marker is created.
    """
    fixture = lib.build_events_fixture(sandbox)
    result = lib.run_headless_exec(
        sandbox,
        fixture,
        "Create a file named hello.txt with the word HELLO via apply_patch. Nothing else.",
    )
    created = (fixture / "hello.txt").is_file()
    if not created:
        pytest.skip(
            "model did not perform the apply_patch this run; hook-firing "
            f"inconclusive (codex stderr tail: {result.stderr[-200:]!r})"
        )
    # The headline assertion: with the tool having fired, NO event marker exists.
    fired = {e: lib.marker_fired(fixture, e) for e in lib.MARKER_EVENTS}
    assert not any(fired.values()), (
        "EXPECTED no headless hooks to fire (known defect), but some did: "
        f"{fired}. If this passes, the headless-hooks defect may be fixed — "
        "update FACTS.md and the bug."
    )


@requires_live
def test_interactive_events_fire(sandbox: lib.CodexSandbox) -> None:
    """The interactive ``codex`` TUI fires all four event hooks.

    After one real model turn (apply_patch), every marker log grows.
    """
    fixture = lib.build_events_fixture(sandbox)
    with lib.PtySession(
        fixture=fixture, env=sandbox.env(), binary=lib.codex_binary() or "codex"
    ) as session:
        session.drain(20)  # startup + onboarding settle
        for _ in range(3):  # dismiss any welcome screens
            session.send("\r")
            session.drain(8)
        session.submit(
            "Use apply_patch to create a file named probe_ok.txt containing "
            "exactly: hooks-interactive-test"
        )
        session.drain(120)
        rendered = session.render()
        fired = {e: lib.marker_fired(fixture, e) for e in lib.MARKER_EVENTS}

    if not (fixture / "probe_ok.txt").is_file() and not any(fired.values()):
        pytest.skip(
            "model did not complete an apply_patch turn; event firing "
            f"inconclusive. Final screen: {rendered[-5:]}"
        )
    assert all(fired.values()), (
        f"expected all interactive event hooks to fire, got {fired}. Final screen: {rendered[-8:]}"
    )


@requires_live
def test_interactive_frozen_write_blocked(sandbox: lib.CodexSandbox) -> None:
    """The interactive ``codex`` TUI blocks a FROZEN ``specs/_archive/`` write.

    The gate-shaped PreToolUse hook emits the legacy ``{"decision":"block"}``
    envelope (exit 0); codex honors it as DENY, so the committed frozen file is
    byte-identical before and after.
    """
    fixture, target = lib.build_frozen_fixture(sandbox)
    before = lib.sha256_file(target)
    with lib.PtySession(
        fixture=fixture, env=sandbox.env(), binary=lib.codex_binary() or "codex"
    ) as session:
        session.drain(18)
        session.submit(
            "Use apply_patch to overwrite specs/_archive/some.md with exactly: HACKED-AGAIN"
        )
        session.drain(150)
        rendered = session.render()
    after = lib.sha256_file(target)
    assert before == after, (
        "FROZEN write was NOT blocked: the gate-shaped hook should deny it. "
        f"hash {before[:12]} -> {after[:12]}. Final screen: {rendered[-8:]}"
    )
