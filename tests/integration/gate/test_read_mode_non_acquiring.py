"""T-010-09 / WS-R4 (FR-R4-02/03/04, AC-R4-01/02): READ-mode non-acquiring at the hook boundary.

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

Covered:
  * READ-bound sid + in-repo MUTATING write ⇒ BLOCK, and NO lease record is created/modified
    (non-acquiring; FR-R4-03).
  * READ-bound sid + in-repo ADDITIVE (``specs/bugs``) write ⇒ ALLOW (FR-R4-03).
  * unbound sid (no record, no env) ⇒ IMPLEMENTATION-capable: free-lease acquire proceeds
    (FR-R4-04 / Decision D-3).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import session_identity
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = pytest.mark.integration

_SLUG = "dadaia-workspace"
_LOCK_FILE = "{slug}.lock.json"


def _make_workspace(tmp_path: Path) -> Path:
    """Minimal workspace: one ALIVE context with an IMPLEMENTATION-phase release + bugs dir."""
    rel = tmp_path / "repos" / _SLUG / "specs" / "releases"
    rel.mkdir(parents=True)
    (rel / "ACTIVE.md").write_text("release: v0.1.10\nphase: IMPLEMENTATION\n", encoding="utf-8")
    (tmp_path / "repos" / _SLUG / "specs" / "bugs").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    return tmp_path


def _lock_path(ws: Path) -> Path:
    return ws / ".dadaia" / "states" / "ctx_locks" / _LOCK_FILE.format(slug=_SLUG)


def _write_payload(target: Path) -> dict[str, object]:
    return {"tool_name": "Write", "tool_input": {"file_path": str(target)}}


def test_read_bound_in_repo_mutating_blocks_and_writes_no_lease(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    sid = "claude-read-session"
    # Bind-equivalent: persist the READ session record the gate reads (no env var anywhere).
    session_identity.write_session(ws, sid, {"session_id": sid, "mode": "READ"})
    assert not _lock_path(ws).exists()

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
    # Non-acquiring: the gate must NOT have created or modified the lease record.
    assert not _lock_path(ws).exists()


def test_read_bound_in_repo_additive_allows(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    sid = "claude-read-session"
    session_identity.write_session(ws, sid, {"session_id": sid, "mode": "READ"})

    target = ws / "repos" / _SLUG / "specs" / "bugs" / "planted-bug.md"
    env = claude_hook_env(ws, session_id=sid)
    result = run_hook_subprocess("sdd_gate", _write_payload(target), env)

    assert result.returncode == 0
    assert result.block_envelope() is None, f"ADDITIVE write must ALLOW; stdout={result.stdout!r}"
    # ADDITIVE never touches the lease either.
    assert not _lock_path(ws).exists()


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
    # Free-lease acquire proceeded: the lease record now exists, held by this session.
    assert _lock_path(ws).exists()


# --------------------------------------------------------------------------------------
# NF-2 (rc-2): the default `dadaia context bind --mode read` flow — a sid the harness never
# reports — is honored at the REAL hook boundary via the CONTEXT incumbent pointer, with a
# DIFFERENT harness sid (no self record, no env var).
# --------------------------------------------------------------------------------------


def _bind_read_incumbent(ws: Path, bind_sid: str) -> None:
    """Emulate `dadaia context bind --mode read`: persist a READ record AND refresh the
    context incumbent pointer to ``bind_sid`` — exactly what the bind CLI now does (NF-2)."""
    session_identity.write_session(ws, bind_sid, {"session_id": bind_sid, "mode": "READ"})
    session_identity.set_incumbent(ws, _SLUG, bind_sid)


def test_cross_sid_read_bind_blocks_mutating_via_incumbent(tmp_path: Path) -> None:
    # The operator's `bind --mode read` minted a sid the running harness never reports. A
    # DIFFERENT harness sid performs a MUTATING write under the real hook: it must resolve
    # READ through the context incumbent pointer ⇒ BLOCK, no lease written. This is the
    # NF-2 falsification: the mode channel works with NO env var and a cross-sid record.
    ws = _make_workspace(tmp_path)
    _bind_read_incumbent(ws, "sess_operatorbind")
    assert not _lock_path(ws).exists()

    target = ws / "repos" / _SLUG / "specs" / "releases" / "v0.1.10" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    # The harness session id is DIFFERENT from the bind sid and has no record of its own.
    env = claude_hook_env(ws, session_id="claude-harness-other")
    result = run_hook_subprocess("sdd_gate", _write_payload(target), env)

    assert result.returncode == 0
    envelope = result.block_envelope()
    assert envelope is not None, (
        f"cross-sid read-bind must BLOCK MUTATING; stdout={result.stdout!r}"
    )
    assert "read" in envelope["reason"].lower()
    assert "--mode implementation" in envelope["reason"]
    # Non-acquiring: no lease record created by the blocked write.
    assert not _lock_path(ws).exists()


def test_cross_sid_read_bind_allows_additive_via_incumbent(tmp_path: Path) -> None:
    # Same cross-sid read-bind, but an ADDITIVE write ⇒ ALLOW (FR-R4-03), still no lease.
    ws = _make_workspace(tmp_path)
    _bind_read_incumbent(ws, "sess_operatorbind")

    target = ws / "repos" / _SLUG / "specs" / "bugs" / "planted-by-other.md"
    env = claude_hook_env(ws, session_id="claude-harness-other")
    result = run_hook_subprocess("sdd_gate", _write_payload(target), env)

    assert result.returncode == 0
    assert result.block_envelope() is None, f"ADDITIVE must ALLOW; stdout={result.stdout!r}"
    assert not _lock_path(ws).exists()
