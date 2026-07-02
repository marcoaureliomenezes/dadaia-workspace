"""`resolve_session_id` precedence (v0.1.50 FR1 — rotated-sid root cause).

The harness payload sid must outrank INHERITED per-harness env sids (a stale
`CLAUDE_CODE_SESSION_ID` from a parent shell must not shadow the live payload),
while the explicit `DADAIA_SESSION_ID` eval-flow override stays first. This seam
is shared by the gate, the PostToolUse heartbeat, and ctx-inject — one fix keeps
all three sid-consistent.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.hooks import _common

pytestmark = pytest.mark.unit

_ENV_VARS = ("DADAIA_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_payload_sid_beats_inherited_harness_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "stale-inherited")
    assert _common.resolve_session_id({"session_id": "live-payload"}) == "live-payload"


def test_payload_sid_beats_inherited_codex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_SESSION_ID", "stale-inherited")
    assert _common.resolve_session_id({"session_id": "live-payload"}) == "live-payload"


def test_dadaia_override_stays_first(monkeypatch: pytest.MonkeyPatch) -> None:
    """Eval-flow contract: the explicit override outranks even the payload."""
    monkeypatch.setenv("DADAIA_SESSION_ID", "explicit-override")
    assert _common.resolve_session_id({"session_id": "live-payload"}) == "explicit-override"


def test_env_fallback_without_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a payload sid, the per-harness env is still honored."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-env")
    assert _common.resolve_session_id({}) == "harness-env"
