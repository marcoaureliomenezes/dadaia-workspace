"""`resolve_session_id` precedence (v0.1.50 FR1 — rotated-sid root cause).

The harness payload sid must outrank INHERITED per-harness env sids (a stale
`CLAUDE_CODE_SESSION_ID` from a parent shell must not shadow the live payload),
while the explicit `DADAIA_SESSION_ID` eval-flow override stays first. This seam
is shared by the gate, the PostToolUse heartbeat, and ctx-inject — one fix keeps
all three sid-consistent.

CRIT: session identity is the seam shared by gate, heartbeat, ctx-inject (v0.1.50
rotated-sid root cause). All orderings survive below as parametrized rows, absorbing
the two resolve_session_id cases formerly duplicated in test_common.py.
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


@pytest.mark.parametrize(
    ("name", "env", "payload", "default", "expected"),
    [
        (
            "payload_sid_beats_inherited_claude_env",
            {"CLAUDE_CODE_SESSION_ID": "stale-inherited"},
            {"session_id": "live-payload"},
            None,
            "live-payload",
        ),
        (
            "payload_sid_beats_inherited_codex_env",
            {"CODEX_SESSION_ID": "stale-inherited"},
            {"session_id": "live-payload"},
            None,
            "live-payload",
        ),
        (
            # Eval-flow contract: the explicit override outranks even the payload.
            "dadaia_override_stays_first",
            {"DADAIA_SESSION_ID": "explicit-override"},
            {"session_id": "live-payload"},
            None,
            "explicit-override",
        ),
        (
            # Without a payload sid, the per-harness env is still honored.
            "env_fallback_without_payload",
            {"CLAUDE_CODE_SESSION_ID": "harness-env"},
            {},
            None,
            "harness-env",
        ),
        (
            # Stdin field used when no env var is set at all.
            "stdin_field_when_no_env",
            {},
            {"session_id": "from-stdin"},
            None,
            "from-stdin",
        ),
        (
            # DADAIA_SESSION_ID overrides even a competing CODEX_SESSION_ID + stdin.
            "dadaia_override_beats_codex_and_stdin",
            {"CODEX_SESSION_ID": "codex-sid", "DADAIA_SESSION_ID": "explicit"},
            {"session_id": "x"},
            None,
            "explicit",
        ),
        (
            # No env, no payload sid → the caller-supplied default.
            "default_when_nothing_resolves",
            {},
            {},
            "workspace",
            "workspace",
        ),
    ],
)
def test_resolve_session_id_precedence_table(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    env: dict[str, str],
    payload: dict[str, object],
    default: str | None,
    expected: str,
) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    kwargs = {"default": default} if default is not None else {}
    assert _common.resolve_session_id(payload, **kwargs) == expected
