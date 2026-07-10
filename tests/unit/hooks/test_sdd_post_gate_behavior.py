"""Harness-real behavior tests for the PostToolUse heartbeat (R2a, FR-R2-01/02 / AC-R2-01).

These drive ``sdd_post_gate`` exactly as a real Claude Code harness does: a subprocess
spawned with :func:`claude_hook_env` (pinned-minimal env, **no** hand-planted ``DADAIA_*``
session/persona/mode vars — the harness never sets them) and a Bash ``PostToolUse`` payload
piped to stdin. The session id flows through the stdin ``session_id`` field, which is the
only channel a real harness provides.

This is the corrective for audit finding 2 (``specs/audits/2026-06-10T010550Z``): the old
unit tests ``setenv``'d ``DADAIA_SESSION_ID`` and so certified a heartbeat that was
physically dead in every runtime. By going through ``run_hook_subprocess`` + a pinned
harness env, these tests prove the heartbeat actually fires under real conditions.

No direct hook-module import here — the hook-import contract (test_harness_env_contract)
requires behavior tests in ``tests/**/hooks|gate/**`` to use the subprocess runner.

CRIT: lease heartbeat under a real harness env (audit-finding-2 corrective) — no
cross-session renewal is the no-steal invariant's heartbeat half. Kept standalone below.
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


def _seed_lease(workspace: Path, ctx: str, session_id: str, *, age_seconds: int) -> str:
    """Write a live lease record for ``ctx`` held by ``session_id`` with an aged heartbeat.

    Returns the seeded heartbeat string so a test can assert the hook moved it forward.
    Built with the production ``lease`` module so the record schema stays authoritative,
    then the heartbeat is back-dated (still within TTL) to make renewal observable.
    """
    from dadaia_workspace.features.spec_context import lease

    lease.acquire(workspace, ctx, session_id, "rel-1", "implementation")
    rec = lease.read_record(workspace, ctx)
    assert rec is not None
    aged = (datetime.now(tz=UTC) - timedelta(seconds=age_seconds)).isoformat()
    rec["heartbeat"] = aged
    lease._write_record(lease._record_path(workspace, ctx), rec)
    return aged


def _heartbeat(workspace: Path, ctx: str) -> str:
    from dadaia_workspace.features.spec_context import lease

    rec = lease.read_record(workspace, ctx)
    assert rec is not None
    return str(rec["heartbeat"])


def test_bash_post_tool_use_renews_held_lease_and_logs_event(tmp_path: Path) -> None:
    """A Bash PostToolUse under claude_hook_env renews the holder's lease heartbeat AND
    the HEARTBEAT audit event records how many leases were renewed.
    """
    session_id = "claude-holder"
    old = _seed_lease(tmp_path, "myctx", session_id, age_seconds=60)

    env = claude_hook_env(tmp_path, session_id=session_id)
    payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": session_id}
    result = run_hook_subprocess("sdd_post_gate", payload, env)

    assert result.returncode == 0, result.stderr
    assert _heartbeat(tmp_path, "myctx") != old  # FRESHER after the heartbeat

    events = (tmp_path / ".dadaia" / "logs" / "lock-events.jsonl").read_text(encoding="utf-8")
    record = json.loads(events.strip().splitlines()[-1])
    assert record["event"] == "HEARTBEAT"
    assert record["session_id"] == session_id
    assert record["leases_renewed"] == 1


def test_foreign_session_does_not_renew_foreign_lease(tmp_path: Path) -> None:
    """A PostToolUse from session B never renews session A's lease (no cross-renewal)."""
    old = _seed_lease(tmp_path, "myctx", "owner-A", age_seconds=60)

    env = claude_hook_env(tmp_path, session_id="intruder-B")
    payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": "intruder-B"}
    result = run_hook_subprocess("sdd_post_gate", payload, env)

    assert result.returncode == 0, result.stderr
    assert _heartbeat(tmp_path, "myctx") == old  # untouched


@pytest.mark.parametrize(
    ("name", "session_id", "pop_native_env"),
    [
        # A session holding no lease ⇒ exit 0, no crash (fail-open).
        ("no_lease_held", "no-lease", False),
        # No session id anywhere (empty payload, scrubbed env) ⇒ exit 0 no-op.
        ("no_session_id_in_payload", None, True),
    ],
)
def test_noop_exits_zero(
    tmp_path: Path, name: str, session_id: str | None, pop_native_env: bool
) -> None:
    (tmp_path / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    env = claude_hook_env(tmp_path, session_id=session_id or "unused")
    if pop_native_env:
        env.pop("CLAUDE_CODE_SESSION_ID", None)
    payload: dict[str, Any] = {"hook_event_name": "PostToolUse", "tool_name": "Bash"}
    if session_id is not None:
        payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": session_id}
    result = run_hook_subprocess("sdd_post_gate", payload, env)
    assert result.returncode == 0, result.stderr
