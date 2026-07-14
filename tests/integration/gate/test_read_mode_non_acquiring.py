"""Caller-scoped READ-mode behavior at the real hook boundary.

These are *behavior* tests at the real hook boundary: the ``sdd_gate`` hook is invoked as a
subprocess the way a harness spawns it, via ``run_hook_subprocess`` + ``claude_hook_env()``
with **no** ``DADAIA_*`` env vars planted. That matters because READ enforcement in production
has exactly one working channel — the on-disk session record the bind CLI persists, resolved
by the harness-native session id. A real hook never carries ``DADAIA_MODE``; if mode
resolution only worked via env, READ would be dead in every runtime (the simulated-env blind
spot the v0.1.10 harness-env fixture exists to kill).

The session record is keyed by the harness-native session id that ``claude_hook_env`` injects
as ``CLAUDE_CODE_SESSION_ID``; the gate resolves the same id via ``resolve_session_id`` and
reads the record through ``session_identity`` — no env override anywhere in these tests.

Covered: a caller's READ record blocks its MUTATING write but allows ADDITIVE work; an
unbound caller defaults to IMPLEMENTATION; and another session's READ record never changes
the caller's mode. Mutating ALLOWs upsert advisory presence and never coordinate through a
workspace lock.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import session_identity
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = pytest.mark.integration

_SLUG = "dadaia-workspace"


def _make_workspace(tmp_path: Path) -> Path:
    """Minimal workspace: one ALIVE context with an IMPLEMENTATION-phase release + bugs dir."""
    rel = tmp_path / "repos" / _SLUG / "specs" / "releases"
    rel.mkdir(parents=True)
    (rel / "ACTIVE.md").write_text("release: v0.1.10\nphase: IMPLEMENTATION\n", encoding="utf-8")
    (tmp_path / "repos" / _SLUG / "specs" / "bugs").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    return tmp_path


def _presence_path(ws: Path, session_id: str) -> Path:
    return ws / ".dadaia" / "states" / "presence" / _SLUG / f"{session_id}.json"


def _write_payload(target: Path) -> dict[str, object]:
    return {"tool_name": "Write", "tool_input": {"file_path": str(target)}}


def test_read_bound_mutating_blocks_additive_allows_both_non_acquiring(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    sid = "claude-read-session"
    # Bind-equivalent: persist the READ session record the gate reads (no env var anywhere).
    session_identity.write_session(ws, sid, {"session_id": sid, "mode": "READ"})

    target = ws / "repos" / _SLUG / "specs" / "releases" / "v0.1.10" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    env = claude_hook_env(ws, session_id=sid)
    result = run_hook_subprocess("sdd_gate", _write_payload(target), env)

    assert result.returncode == 0
    envelope = result.block_envelope()
    assert envelope is not None, f"expected a BLOCK envelope, got stdout={result.stdout!r}"
    reason = envelope["reason"]
    assert "read" in reason.lower()
    # Names the documented path to write rights without a banned auto-rebind nag.
    assert "--mode implementation" in reason
    assert not _presence_path(ws, sid).exists()

    # Same READ-bound session, ADDITIVE target -> ALLOW without presence mutation.
    additive_target = ws / "repos" / _SLUG / "specs" / "bugs" / "planted-bug.md"
    result_additive = run_hook_subprocess("sdd_gate", _write_payload(additive_target), env)
    assert result_additive.returncode == 0
    assert result_additive.block_envelope() is None, (
        f"ADDITIVE write must ALLOW; stdout={result_additive.stdout!r}"
    )
    assert not _presence_path(ws, sid).exists()


def test_unbound_session_is_implementation_capable(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    sid = "claude-unbound-session"
    # No session record written, no DADAIA_MODE → default IMPLEMENTATION (FR-R4-04).
    target = ws / "repos" / _SLUG / "specs" / "releases" / "v0.1.10" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    env = claude_hook_env(ws, session_id=sid)
    result = run_hook_subprocess("sdd_gate", _write_payload(target), env)

    assert result.returncode == 0
    assert result.block_envelope() is None, f"unbound write must ALLOW; stdout={result.stdout!r}"
    assert _presence_path(ws, sid).exists()


# --------------------------------------------------------------------------------------
# A foreign session record can never impose its mode on this caller. Resolution is
# strictly caller-scoped: env -> own session record -> IMPLEMENTATION default.
# --------------------------------------------------------------------------------------


def _write_foreign_read_session(ws: Path, bind_sid: str) -> None:
    """Persist another caller's READ session record."""
    session_identity.write_session(ws, bind_sid, {"session_id": bind_sid, "mode": "READ"})


def test_foreign_read_session_never_imposes_read_on_caller(
    tmp_path: Path,
) -> None:
    # A different harness sid has no caller-owned record, so it resolves its own default
    # IMPLEMENTATION mode and upserts presence under its own identity.
    ws = _make_workspace(tmp_path)
    _write_foreign_read_session(ws, "sess_operatorbind")

    target = ws / "repos" / _SLUG / "specs" / "releases" / "v0.1.10" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    # The harness session id is DIFFERENT from the bind sid and has no record of its own.
    foreign_sid = "claude-harness-other"
    env = claude_hook_env(ws, session_id=foreign_sid)
    result = run_hook_subprocess("sdd_gate", _write_payload(target), env)

    assert result.returncode == 0
    assert result.block_envelope() is None, (
        f"a foreign read-bind must NEVER impose READ on this session; stdout={result.stdout!r}"
    )
    assert _presence_path(ws, foreign_sid).exists()

    # The same caller may also write an ADDITIVE artifact.
    additive_target = ws / "repos" / _SLUG / "specs" / "bugs" / "planted-by-other.md"
    result_additive = run_hook_subprocess("sdd_gate", _write_payload(additive_target), env)

    assert result_additive.returncode == 0
    assert result_additive.block_envelope() is None, (
        f"ADDITIVE must ALLOW; stdout={result_additive.stdout!r}"
    )
