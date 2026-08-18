"""Live Codex exec probe — runs ONLY when a real Codex CLI is installed (A22.4).

Intent: SENTINEL — v0.4.3 A22.4 (the one executed-path integration test of the
codex-live-probe seam; declared plan ref T-043-34)

Genuinely exercises the INSTALLED Codex binary through the production
``SubprocessCertificationProcess`` adapter — no fake, no mock; a real ``codex exec``
call leaves this process. Skips honestly (never fails) when no ``codex`` CLI is
reachable on PATH — true for every CI runner today, since Codex is a manually
installed local dev tool, not a repo/CI dependency. This is the env-gated,
plan-referenced skip dadaia-test-stewardship §I requires ("give every env-gated skip a
plan ref or delete it") — the plan ref is T-043-34/A22.4 above.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from dadaia_workspace.features.certification.service import _codex_live_probe_detail
from dadaia_workspace.infrastructure.certification_process import SubprocessCertificationProcess

pytestmark = pytest.mark.skipif(
    shutil.which("codex") is None,
    reason=(
        "requires a real installed Codex CLI binary on PATH — plan ref T-043-34 "
        "(v0.4.3 A22.4); absent on every CI runner today (Codex is a manually "
        "installed local dev tool, not a repo/CI dependency)"
    ),
)


@pytest.mark.timeout(90)
def test_codex_live_probe_exercises_the_real_installed_codex(tmp_path: Path) -> None:
    """A22.4: certification's live probe genuinely talks to the installed Codex CLI.

    Explicit 90s timeout override (justified, dadaia-test-stewardship §C): the probe's
    own internal bound is 15s (``codex --version``) + 60s (``codex exec``) = up to 75s
    worst case; the default integration-tier ceiling (60s) would truncate a
    legitimately slow-but-successful run before the function's own bounded-timeout
    logic gets to report cleanly.
    """
    process = SubprocessCertificationProcess()
    detail = _codex_live_probe_detail(process, tmp_path)
    assert "live exec probe observed" in detail
    assert "DADAIA-LIVE-PROBE-OK" in detail
