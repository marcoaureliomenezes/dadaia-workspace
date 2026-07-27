"""v0.1.76 doctrine invariants — the gate never blocks a write on concurrency.

The operator-ratified NO-LOCKS DOCTRINE accepts and surfaces races between sessions;
it never prevents work because of peer activity. This suite proves that behavior at the
real hook subprocess boundary and verifies caller-local READ self-protection.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import session_identity
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = pytest.mark.unit


def _mk_workspace(tmp_path: Path, *slugs: str, phase: str = "IMPLEMENTATION") -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": s, "state": "alive"} for s in slugs]}),
        encoding="utf-8",
    )
    for s in slugs:
        rel = tmp_path / "repos" / s / "specs" / "releases"
        rel.mkdir(parents=True, exist_ok=True)
        (rel / "ACTIVE.md").write_text(f"release: rel-1\nphase: {phase}\n", encoding="utf-8")
    return tmp_path


def _write_session_record(ws: Path, session_id: str, mode: str) -> None:
    session_identity.write_session(ws, session_id, {"session_id": session_id, "mode": mode})


def _write_target(ws: Path, ctx: str, name: str) -> Path:
    target = ws / "repos" / ctx / "specs" / "releases" / "rel-1" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _run(
    ws: Path,
    payload: dict[str, object],
    *,
    session_id: str,
) -> dict[str, object] | None:
    env = claude_hook_env(ws, session_id=session_id)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    full_payload = {**payload, "session_id": session_id}
    result = run_hook_subprocess("pre_gate", full_payload, env)
    assert result.returncode == 0, result.stderr
    return result.block_envelope()


def _assert_never_a_lock_block(block: dict[str, object] | None) -> None:
    """A concurrency block, if any survives, would carry the LockHeldError/SDD-LOCK
    signature. The doctrine forbids ANY block for this reason — asserting both "no block
    at all" AND "if somehow blocked, never for a lock reason" pins the failure mode."""
    assert block is None, f"doctrine violation: write BLOCKed — {block}"


# --------------------------------------------------------------------------- #
# Two live sessions — both writes ALLOW, at most one throttled advisory each.
# --------------------------------------------------------------------------- #


def test_two_live_sessions_both_mutating_writes_allow(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    sid_a, sid_b = "session-alpha", "session-beta"

    target_a = _write_target(ws, ctx, "TASKS.md")
    block_a = _run(
        ws, {"tool_name": "Write", "tool_input": {"file_path": str(target_a)}}, session_id=sid_a
    )
    _assert_never_a_lock_block(block_a)

    target_b = _write_target(ws, ctx, "PLAN.md")
    block_b = _run(
        ws, {"tool_name": "Write", "tool_input": {"file_path": str(target_b)}}, session_id=sid_b
    )
    _assert_never_a_lock_block(block_b)

    # Both sessions' presence must now be recorded on this context (co-presence proof).
    presence_dir = ws / ".dadaia" / "states" / "presence" / ctx
    recorded = {p.stem for p in presence_dir.glob("*.json")} if presence_dir.is_dir() else set()
    assert {sid_a, sid_b} <= recorded, recorded


def test_second_session_write_surfaces_advisory_naming_the_other_session(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    sid_a, sid_b = "session-alpha", "session-beta"

    target_a = _write_target(ws, ctx, "TASKS.md")
    _run(ws, {"tool_name": "Write", "tool_input": {"file_path": str(target_a)}}, session_id=sid_a)

    target_b = _write_target(ws, ctx, "PLAN.md")
    result_b = run_hook_subprocess(
        "pre_gate",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target_b)},
            "session_id": sid_b,
        },
        (lambda e: (e.pop("CLAUDE_CODE_SESSION_ID", None), e.pop("DADAIA_CONTEXT", None), e)[-1])(
            claude_hook_env(ws, session_id=sid_b)
        ),
    )
    assert result_b.returncode == 0, result_b.stderr
    # ALLOW: no block envelope on stdout.
    assert result_b.block_envelope() is None
    # Bug pre-gate-drops-live-presence-advisory-042 (Hermes R1-B): the doctrine
    # MANDATES the throttled advisory on detection — a neutral allow envelope that
    # swallows it blinds concurrency diagnosis. The advisory rides the allow
    # envelope's systemMessage and names the other live session.
    combined = result_b.stdout + result_b.stderr
    assert "[PRESENCE]" in combined, (
        f"allowed write with a live foreign presence must surface the advisory; "
        f"got stdout={result_b.stdout!r} stderr={result_b.stderr!r}"
    )
    assert sid_a in combined


def test_advisory_is_throttled_within_the_window(tmp_path: Path) -> None:
    """A second write from the same session within the throttle window emits at most one
    advisory total — never re-warns on every single write inside the window."""
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    sid_a, sid_b = "session-alpha", "session-beta"

    target_a = _write_target(ws, ctx, "TASKS.md")
    _run(ws, {"tool_name": "Write", "tool_input": {"file_path": str(target_a)}}, session_id=sid_a)

    outputs = []
    for name in ("PLAN.md", "SPEC.md"):
        target_b = _write_target(ws, ctx, name)
        env = claude_hook_env(ws, session_id=sid_b)
        env.pop("CLAUDE_CODE_SESSION_ID", None)
        env.pop("DADAIA_CONTEXT", None)
        result = run_hook_subprocess(
            "pre_gate",
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(target_b)},
                "session_id": sid_b,
            },
            env,
        )
        assert result.returncode == 0, result.stderr
        assert result.block_envelope() is None
        outputs.append(result.stdout + result.stderr)

    warned = sum(1 for o in outputs if sid_a in o)
    assert warned <= 1, "advisory must be throttled — never re-warn on every write in-window"


# --------------------------------------------------------------------------- #
# Mode self-scope: a foreign session's bind can never change my mode.
# --------------------------------------------------------------------------- #


def test_foreign_read_bind_never_imposes_read_on_my_mutating_write(tmp_path: Path) -> None:
    """Another session's READ record cannot change this caller's default mode."""
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    foreign_read_sid = "foreign-read-bind"
    my_sid = "my-own-harness-sid"

    _write_session_record(ws, foreign_read_sid, "READ")

    target = _write_target(ws, ctx, "TASKS.md")
    block = _run(
        ws, {"tool_name": "Write", "tool_input": {"file_path": str(target)}}, session_id=my_sid
    )
    _assert_never_a_lock_block(block)


def test_my_own_read_bind_still_blocks_my_own_mutating_write(tmp_path: Path) -> None:
    """Self-protection is kept: MY OWN session record resolving READ still blocks MY OWN
    MUTATING write (opt-in only, never imposed by a foreign session)."""
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    my_sid = "self-read-bound"
    _write_session_record(ws, my_sid, "READ")

    target = _write_target(ws, ctx, "TASKS.md")
    block = _run(
        ws, {"tool_name": "Write", "tool_input": {"file_path": str(target)}}, session_id=my_sid
    )
    assert block is not None
    assert "read" in str(block["reason"]).lower()


def test_foreign_implementation_bind_never_changes_my_read_mode(tmp_path: Path) -> None:
    """Another session's implementation record cannot upgrade this caller's READ mode."""
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    foreign_impl_sid = "foreign-impl-bind"
    my_read_sid = "my-own-read-bound"

    _write_session_record(ws, foreign_impl_sid, "IMPLEMENTATION")
    _write_session_record(ws, my_read_sid, "READ")

    target = _write_target(ws, ctx, "TASKS.md")
    block = _run(
        ws,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id=my_read_sid,
    )
    assert block is not None
    assert "read" in str(block["reason"]).lower()


# --------------------------------------------------------------------------- #
# anon-session guard: no session id -> write ALLOWED, but no presence record created.
# --------------------------------------------------------------------------- #


def test_anon_session_write_allowed_but_creates_no_presence_record(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"

    target = _write_target(ws, ctx, "TASKS.md")
    env = claude_hook_env(ws, session_id="unused")
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("CODEX_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    env.pop("DADAIA_SESSION_ID", None)
    # No session_id in the payload either -> resolves the anon-session default.
    result = run_hook_subprocess(
        "pre_gate",
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        env,
    )
    assert result.returncode == 0, result.stderr
    assert result.block_envelope() is None

    presence_dir = ws / ".dadaia" / "states" / "presence" / ctx
    recorded = {p.stem for p in presence_dir.glob("*.json")} if presence_dir.is_dir() else set()
    assert "anon-session" not in recorded, recorded
    assert recorded == set(), recorded


def test_throttle_marker_rejects_traversal_shaped_identity_components(tmp_path: Path) -> None:
    """Direct-API defense-in-depth (v0.1.76 security-review LOW): a traversal-shaped
    ``session_id``/``ctx`` must never place the advisory throttle marker outside
    ``.dadaia/tmp/`` — the helpers reject invalid name components outright (hook callers
    already sanitize; this pins the module's own guard)."""
    from dadaia_workspace.features.spec_context import gate_policy

    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    escape_probe = tmp_path / "escape-probe"
    hostile = f"../../../{escape_probe.name}"

    assert gate_policy._advisory_throttle_path(ws, hostile, "dadaia-workspace") is None
    assert gate_policy._advisory_throttle_path(ws, "session-ok", hostile) is None

    gate_policy._stamp_advisory_throttle(ws, hostile, "dadaia-workspace")
    gate_policy._stamp_advisory_throttle(ws, "session-ok", hostile)
    assert not escape_probe.exists()
    assert gate_policy._advisory_throttled(ws, hostile, "dadaia-workspace", now=0.0) is False

    marker = gate_policy._advisory_throttle_path(ws, "session-ok", "dadaia-workspace")
    assert marker is not None
    assert marker.parent == ws / ".dadaia" / "tmp"
