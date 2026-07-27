"""Harness-real behavior tests for the presence-only PostToolUse heartbeat.

``presence.renew`` is the only renewal PostToolUse performs. These tests drive
``sdd_post_gate`` exactly as a real Claude Code harness does: a subprocess
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

from tests.fixtures.harness_env import claude_hook_env, kimi_hook_env, run_hook_subprocess

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


# --- bug kimi-ctx-inject-bind-attribution-gap: post-gate bind self-adoption ----
#
# kimi-code exposes no native session-id env var, so `dadaia context bind` (run through
# the harness Bash tool) mints a CLI sid the kimi hooks can never key on — context
# injection, bind mode, and the session heartbeat all missed the kimi session. But the
# hook's own ANCESTRY still carries the long-lived harness pid the bind-epoch marker
# records: the post-gate adopts an attributed bind into the session's OWN record.


def _seed_attributed_bind(workspace: Path, ctx: str, *, mode: str = "read") -> None:
    """A bind made THROUGH this session's harness: the marker's ancestry chain contains
    the test process's pid (the hook subprocess's parent — standing in for the harness
    pid a real marker records), and the CLI-minted bind record hangs off the marker's
    ``sid:`` line with the operator-chosen mode."""
    import os

    (workspace / "repos" / ctx / "specs").mkdir(parents=True)
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": ctx, "state": "alive"}]}),
        encoding="utf-8",
    )
    marker_dir = states / "bind_epoch"
    marker_dir.mkdir(parents=True, exist_ok=True)
    (marker_dir / ctx).write_text(f"{os.getpid()}\nsid:sess_bindcli\n", encoding="utf-8")
    sessions = workspace / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / "sess_bindcli.json").write_text(
        json.dumps(
            {
                "session_id": "sess_bindcli",
                "context": ctx,
                "mode": mode,
                "release": "",
                "runtime": "unknown",
                "pid": 1,
                "bound_at": "2026-07-22T00:00:00+00:00",
                "last_seen_at": "2026-07-22T00:00:00+00:00",
                "ttl_seconds": 300,
                "is_stale": False,
            }
        ),
        encoding="utf-8",
    )


def _read_own_record(workspace: Path, session_id: str) -> dict[str, Any] | None:
    path = workspace / ".dadaia" / "sessions" / f"{session_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def test_kimi_session_adopts_attributed_bind_into_own_record(tmp_path: Path) -> None:
    """The kimi hook (payload-only session id, no native env var) keys the attributed
    bind's context+mode to its OWN session id — closing the injection/mode/heartbeat gap."""
    _seed_attributed_bind(tmp_path, "myctx", mode="read")
    session_id = "session_kimi-abc"

    env = kimi_hook_env(tmp_path, extra={"DADAIA_RUNTIME": "kimi-code"})
    payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": session_id}
    result = run_hook_subprocess("sdd_post_gate", payload, env)

    assert result.returncode == 0, result.stderr
    record = _read_own_record(tmp_path, session_id)
    assert record is not None, "adoption never happened — the kimi gap is still open"
    assert record["context"] == "myctx"
    assert record["mode"] == "read"
    assert record["runtime"] == "kimi-code"


def test_no_attributed_bind_writes_no_record(tmp_path: Path) -> None:
    """No attributable marker (unbound, or another session's bind) ⇒ no adoption, no
    record — a foreign bind must NEVER leak into this session."""
    (tmp_path / ".dadaia" / "states" / "bind_epoch").mkdir(parents=True)
    session_id = "session_kimi-solo"

    env = kimi_hook_env(tmp_path, extra={"DADAIA_RUNTIME": "kimi-code"})
    payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": session_id}
    result = run_hook_subprocess("sdd_post_gate", payload, env)

    assert result.returncode == 0, result.stderr
    assert _read_own_record(tmp_path, session_id) is None


def test_existing_record_not_clobbered_when_context_matches(tmp_path: Path) -> None:
    """An own record already carrying the attributed context is left untouched (the
    heartbeat refresh owns liveness; adoption never rewrites it)."""
    _seed_attributed_bind(tmp_path, "myctx")
    session_id = "session_kimi-same"
    sessions = tmp_path / ".dadaia" / "sessions"
    (sessions / f"{session_id}.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "context": "myctx",
                "mode": "implementation",
                "bound_at": "2026-07-20T00:00:00+00:00",
                "last_seen_at": "2026-07-21T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    env = kimi_hook_env(tmp_path, extra={"DADAIA_RUNTIME": "kimi-code"})
    payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": session_id}
    result = run_hook_subprocess("sdd_post_gate", payload, env)

    assert result.returncode == 0, result.stderr
    record = _read_own_record(tmp_path, session_id)
    assert record is not None
    assert record["bound_at"] == "2026-07-20T00:00:00+00:00"


def test_rebind_elsewhere_updates_own_record(tmp_path: Path) -> None:
    """The operator re-bound THIS session to a different context: the attributed marker
    is the session's most recent bind truth, so the own record follows it."""
    _seed_attributed_bind(tmp_path, "newctx")
    session_id = "session_kimi-move"
    sessions = tmp_path / ".dadaia" / "sessions"
    (sessions / f"{session_id}.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "context": "oldctx",
                "mode": "implementation",
                "bound_at": "2026-07-20T00:00:00+00:00",
                "last_seen_at": "2026-07-21T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    env = kimi_hook_env(tmp_path, extra={"DADAIA_RUNTIME": "kimi-code"})
    payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": session_id}
    result = run_hook_subprocess("sdd_post_gate", payload, env)

    assert result.returncode == 0, result.stderr
    record = _read_own_record(tmp_path, session_id)
    assert record is not None
    assert record["context"] == "newctx"


def test_same_context_rebind_with_new_mode_updates_mode(tmp_path: Path) -> None:
    """A same-context re-bind with a DIFFERENT mode (read -> implementation) is how mode
    changes reach a payload-only session at all: the own record follows the marker's
    bind record even though the context is unchanged. Proven live in production during
    the fix: a read-mode adoption had to yield to a later implementation bind."""
    _seed_attributed_bind(tmp_path, "myctx", mode="BOUND_IMPLEMENTATION")
    session_id = "session_kimi-mode"
    sessions = tmp_path / ".dadaia" / "sessions"
    (sessions / f"{session_id}.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "context": "myctx",
                "mode": "read",
                "bound_at": "2026-07-20T00:00:00+00:00",
                "last_seen_at": "2026-07-21T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    env = kimi_hook_env(tmp_path, extra={"DADAIA_RUNTIME": "kimi-code"})
    payload = {**_BASH_POST_TOOL_PAYLOAD, "session_id": session_id}
    result = run_hook_subprocess("sdd_post_gate", payload, env)

    assert result.returncode == 0, result.stderr
    record = _read_own_record(tmp_path, session_id)
    assert record is not None
    assert record["mode"] == "BOUND_IMPLEMENTATION"
    assert record["bound_at"] == "2026-07-20T00:00:00+00:00"
