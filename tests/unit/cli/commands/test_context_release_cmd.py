"""CLI ``dadaia context release`` — drops the session's advisory presence (v0.1.76 FR2).

Re-baselined from the pre-v0.1.76 lease-drop test (T-014-08 / FR-W4-03): under the
NO-LOCKS DOCTRINE there is no lease to release anymore — ``presence`` is the sole
concurrency-signal surface, and it is never exclusive, so there is no "live foreign
holder" concept left to protect. These are CLI-LEVEL tests: they drive
``context.release_cmd`` through the Typer runner end-to-end against a minimal tmp
workspace (NO real venv built).

* **release WITH a presence record** (harness-native id, env override, or ``--session``)
  -> the record is deleted, the CLI session record is unlinked.
* **release WITHOUT any presence record** -> a clean no-op (exit 0).
* **another session's presence is UNTOUCHED** — release only ever clears the resolved
  session's own records, never a sibling's (presence has no exclusivity to steal, but
  release must still be scoped to "self").
* **no resolvable session id** (no ``--session``, no env, no harness-native var) -> exit 1
  with an actionable message.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import context as context_cmd
from dadaia_workspace.features.spec_context import presence

runner = CliRunner()


def _seed_presence(ws: Path, ctx: str, sid: str, *, pid: int = 4242) -> None:
    presence.upsert(ws, ctx, sid, runtime="claude", pid=pid)


def _seed_session(ws: Path, sid: str, ctx: str) -> None:
    """Write a CLI session record naming the bound context."""
    sessions_dir = context_cmd._sessions_dir(ws)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    (sessions_dir / f"{sid}.json").write_text(
        json.dumps({"session_id": sid, "context": ctx, "mode": "IMPLEMENTATION"}),
        encoding="utf-8",
    )


def _patch_workspace(monkeypatch: pytest.MonkeyPatch, ws: Path) -> None:
    monkeypatch.setattr(context_cmd, "resolve_workspace_root", lambda: ws)


def _clear_harness_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)


# --------------------------------------------------------------------------- #
# --session override
# --------------------------------------------------------------------------- #


def test_release_with_session_flag_clears_presence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path
    sid = "sess_cli01"
    _seed_presence(ws, "ctxa", sid)
    _seed_session(ws, sid, "ctxa")
    _patch_workspace(monkeypatch, ws)
    _clear_harness_env(monkeypatch)

    result = runner.invoke(context_cmd.app, ["release", "--session", sid])

    assert result.exit_code == 0, result.output
    assert sid in result.output
    assert not (ws / ".dadaia" / "states" / "presence" / "ctxa" / f"{sid}.json").exists()
    assert not (context_cmd._sessions_dir(ws) / f"{sid}.json").exists()


# --------------------------------------------------------------------------- #
# DADAIA_SESSION_ID env override (eval-flow)
# --------------------------------------------------------------------------- #


def test_release_via_env_sid_clears_presence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path
    sid = "sess_env01"
    _seed_presence(ws, "ctxa", sid)
    _seed_session(ws, sid, "ctxa")
    _patch_workspace(monkeypatch, ws)
    _clear_harness_env(monkeypatch)
    monkeypatch.setenv("DADAIA_SESSION_ID", sid)

    result = runner.invoke(context_cmd.app, ["release"])

    assert result.exit_code == 0, result.output
    assert not (ws / ".dadaia" / "states" / "presence" / "ctxa" / f"{sid}.json").exists()
    assert not (context_cmd._sessions_dir(ws) / f"{sid}.json").exists()


# --------------------------------------------------------------------------- #
# Harness-native session id (no flag, no env override needed)
# --------------------------------------------------------------------------- #


def test_release_resolves_harness_native_session_id_with_no_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path
    sid = "harness-native-sid-001"
    _seed_presence(ws, "ctxa", sid)
    _seed_session(ws, sid, "ctxa")
    _patch_workspace(monkeypatch, ws)
    _clear_harness_env(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", sid)

    result = runner.invoke(context_cmd.app, ["release"])

    assert result.exit_code == 0, result.output
    assert not (ws / ".dadaia" / "states" / "presence" / "ctxa" / f"{sid}.json").exists()


# --------------------------------------------------------------------------- #
# Presence for ANOTHER session is never touched (release is self-scoped).
# --------------------------------------------------------------------------- #


def test_release_never_clears_a_different_sessions_presence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path
    my_sid = "sess_cli02"
    other_sid = "sess_other"
    _seed_presence(ws, "ctxa", my_sid)
    _seed_presence(ws, "ctxa", other_sid)
    _seed_session(ws, my_sid, "ctxa")
    _patch_workspace(monkeypatch, ws)
    _clear_harness_env(monkeypatch)

    result = runner.invoke(context_cmd.app, ["release", "--session", my_sid])

    assert result.exit_code == 0, result.output
    assert not (ws / ".dadaia" / "states" / "presence" / "ctxa" / f"{my_sid}.json").exists()
    # The other session's presence record survives untouched.
    assert (ws / ".dadaia" / "states" / "presence" / "ctxa" / f"{other_sid}.json").exists()


# --------------------------------------------------------------------------- #
# No presence / no session id
# --------------------------------------------------------------------------- #


def test_release_without_presence_noop_and_no_session_id_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """release with a session record but no presence recorded -> exit 0, clean no-op; and
    neither --session nor any env/harness id resolvable -> exit 1 with an actionable message."""
    ws = tmp_path
    cli_sid = "sess_cli03"
    _seed_session(ws, cli_sid, "ctxa")  # bound, but no presence ever recorded
    _patch_workspace(monkeypatch, ws)
    _clear_harness_env(monkeypatch)

    result = runner.invoke(context_cmd.app, ["release", "--session", cli_sid])

    assert result.exit_code == 0, result.output
    assert not (context_cmd._sessions_dir(ws) / f"{cli_sid}.json").exists()

    no_id_result = runner.invoke(context_cmd.app, ["release"])
    assert no_id_result.exit_code == 1, no_id_result.output
    assert "session" in no_id_result.output.lower()
