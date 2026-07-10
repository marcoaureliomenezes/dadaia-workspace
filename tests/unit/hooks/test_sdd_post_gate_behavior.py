"""Harness-real behavior tests for the PostToolUse heartbeat (v0.1.76 T-3, presence-only).

Re-baselined from the pre-v0.1.76 lease-heartbeat suite (R2a, FR-R2-01/02 / AC-R2-01):
the lease-renewal path this file exercised (``lease.renew_heartbeat`` over the by-session
index) is DELETED — ``presence.renew`` is now the ONLY renewal PostToolUse performs. These
tests drive ``sdd_post_gate`` exactly as a real Claude Code harness does: a subprocess
spawned with :func:`claude_hook_env` (pinned-minimal env, **no** hand-planted ``DADAIA_*``
session/persona/mode vars — the harness never sets them) and a Bash ``PostToolUse`` payload
piped to stdin. The session id flows through the stdin ``session_id`` field, which is the
only channel a real harness provides.

No direct hook-module import here — the hook-import contract (test_harness_env_contract)
requires behavior tests in ``tests/**/hooks|gate/**`` to use the subprocess runner.

CRIT: presence heartbeat under a real harness env — no cross-session renewal (a PostToolUse
from session B never renews session A's presence record).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

# A representative Bash PostToolUse payload — the case that broke before R2a: a long Bash
# call with no Write/Edit, where the old env-gated hook never renewed.
_BASH_POST_TOOL_PAYLOAD: dict[str, Any] = {
    "hook_event_name": "PostToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "sleep 130"},
}


def _seed_presence(workspace: Path, ctx: str, session_id: str, *, age_seconds: int) -> str:
    """Write a live presence record for ``ctx`` owned by ``session_id`` with an aged heartbeat.

    Returns the seeded ``last_seen_at`` string so a test can assert the hook moved it
    forward. Built with the production ``presence`` module so the record schema stays
    authoritative, then back-dated (still within TTL) to make renewal observable.
    """
    from dadaia_workspace.features.spec_context import presence

    presence.upsert(workspace, ctx, session_id, runtime="claude", pid=1234)
    path = workspace / ".dadaia" / "states" / "presence" / ctx / f"{session_id}.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    aged = (datetime.now(tz=UTC) - timedelta(seconds=age_seconds)).isoformat()
    rec["last_seen_at"] = aged
    path.write_text(json.dumps(rec), encoding="utf-8")
    return aged


def _last_seen(workspace: Path, ctx: str, session_id: str) -> str:
    path = workspace / ".dadaia" / "states" / "presence" / ctx / f"{session_id}.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    return str(rec["last_seen_at"])


def test_bash_post_tool_use_renews_held_presence(tmp_path: Path) -> None:
    """A Bash PostToolUse under claude_hook_env renews the session's presence record."""
    session_id = "claude-holder"
    old = _seed_presence(tmp_path, "myctx", session_id, age_seconds=60)

    env = claude_hook_env(tmp_path, session_id=session_id)
    payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": session_id}
    result = run_hook_subprocess("sdd_post_gate", payload, env)

    assert result.returncode == 0, result.stderr
    assert _last_seen(tmp_path, "myctx", session_id) != old  # FRESHER after the heartbeat


def test_foreign_session_does_not_renew_foreign_presence(tmp_path: Path) -> None:
    """A PostToolUse from session B never renews session A's presence record."""
    old = _seed_presence(tmp_path, "myctx", "owner-A", age_seconds=60)

    env = claude_hook_env(tmp_path, session_id="intruder-B")
    payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": "intruder-B"}
    result = run_hook_subprocess("sdd_post_gate", payload, env)

    assert result.returncode == 0, result.stderr
    assert _last_seen(tmp_path, "myctx", "owner-A") == old  # untouched


@pytest.mark.parametrize(
    ("name", "session_id", "pop_native_env"),
    [
        # A session with no presence recorded ⇒ exit 0, no crash (fail-open).
        ("no_presence_held", "no-presence", False),
        # No session id anywhere (empty payload, scrubbed env) ⇒ exit 0 no-op.
        ("no_session_id_in_payload", None, True),
    ],
)
def test_noop_exits_zero(
    tmp_path: Path, name: str, session_id: str | None, pop_native_env: bool
) -> None:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    env = claude_hook_env(tmp_path, session_id=session_id or "unused")
    if pop_native_env:
        env.pop("CLAUDE_CODE_SESSION_ID", None)
    payload: dict[str, Any] = {"hook_event_name": "PostToolUse", "tool_name": "Bash"}
    if session_id is not None:
        payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": session_id}
    result = run_hook_subprocess("sdd_post_gate", payload, env)
    assert result.returncode == 0, result.stderr
