"""v0.1.76 doctrine invariants — the gate never blocks a write on concurrency.

SPEC ``specs/releases/v0.1.76/SPEC.md`` (backlog ``lock-lease-session-identity-kernel``,
the operator-ratified NO-LOCKS DOCTRINE): races between sessions are ACCEPTED and
SURFACED, never prevented. After this release no path may BLOCK a write or commit
because of another session. This file is the RED-first executed-path suite (T-1) proving
that doctrine through the REAL hook subprocess (:func:`run_hook_subprocess`) — never a
simulated ``sys.stdin`` — exactly as ``tests/fixtures/harness_env`` requires.

Every test in this module currently FAILS against the pre-T-2 implementation because:
  * the gate still calls ``lease.acquire`` and can raise/emit ``LockHeldError`` BLOCK, and
  * ``_resolve_mode`` still has the context-incumbent (rung 3) fallback that lets a
    foreign session's bind change another session's resolved mode.

CRITICAL-bug probe (AC1): the exact remote topology from bug
``layer1-rebind-adopts-lease-to-synthetic-session-self-block`` — bind mints a synthetic
session, adopts the lease, and the SAME harness's next write (harness-native id) used to
self-block. Reproduced here end-to-end through the real gate subprocess: it must now
NEVER block, on either a same- or different-mode rebind.

v0.1.76 T-3 note: ``lease.acquire``/``lease.adopt_if_own_lineage`` (the production
adoption path this probe originally drove) are DELETED along with the whole
acquisition/CAS machinery — nothing production writes a lease record anymore. The
CRITICAL-bug topology (a residual lease record whose ``session_id`` no longer names the
harness-native id, following a rebind) is now seeded directly as raw JSON — exactly the
on-disk SHAPE ``adopt_if_own_lineage`` used to produce — so the probe still proves the
doctrine claim (the gate never reads this file at all) without depending on a deleted API.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import session_identity
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = pytest.mark.unit

_BLOCK_FORBIDDEN_PATTERNS: tuple[str, ...] = ("lockhelderror", "sdd lock")


def _seed_lock_record(ws: Path, ctx: str, session_id: str, *, pid: int) -> None:
    """Plant a raw ``<ctx>.lock.json`` — the residual-record topology successor to the
    deleted ``lease.acquire``/``lease.adopt_if_own_lineage`` production adoption path
    (v0.1.76 T-3). The gate never reads this file (T-2); this only reproduces the exact
    on-disk shape a pre-doctrine install could still carry.
    """
    now = datetime.now(tz=UTC).isoformat()
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "context": ctx,
        "release": "rel-1",
        "session_id": session_id,
        "mode": "IMPLEMENTATION",
        "pid": pid,
        "acquired_at": now,
        "heartbeat": now,
        "ttl": 120,
    }
    (lock_dir / f"{ctx}.lock.json").write_text(json.dumps(record, indent=2), encoding="utf-8")


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
    # The advisory line (when emitted) is stdout/stderr diagnostic text, never the block
    # envelope, and it names the other live session.
    combined = result_b.stdout + result_b.stderr
    if combined.strip():
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
# CRITICAL-bug probe (AC1): bind -> write -> rebind -> write NEVER blocks.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "rebind_mode"),
    [
        pytest.param("same_mode_rebind", "IMPLEMENTATION", id="rebind-same-mode-never-blocks"),
        pytest.param("different_mode_rebind", "BOUND_REVIEW", id="rebind-diff-mode-never-blocks"),
    ],
)
def test_critical_bug_probe_rebind_then_write_never_blocks(
    tmp_path: Path, name: str, rebind_mode: str
) -> None:
    """Reproduces bug ``layer1-rebind-adopts-lease-to-synthetic-session-self-block``
    end-to-end, exactly as the reporter's transcript shows:

      1. The harness-native session writes -> ALLOW (v0.1.76: the gate no longer
         acquires a lease at all — a residual lease record is seeded directly below to
         reproduce the exact pre-existing-lease topology the bug's transcript describes,
         e.g. a leftover from a prior release's lease machinery or a direct-API caller).
      2. A rebind's adoption mechanics (T-3: the production ``adopt_if_own_lineage`` API
         they exercised is DELETED) are reproduced by directly seeding the record's final
         on-disk shape — a synthetic ``sess_<uuid>`` names the lease while the
         harness-native id stays orphaned, exactly the topology the deleted adoption path
         used to produce.
      3. The SAME harness-native session (harness-native id, unchanged) writes again.

    Under the pre-T-2 lease machinery this second write's ``.ptr``/record no longer
    names the harness-native id, so it is treated as a live foreign holder and BLOCKed
    (the exact CRITICAL self-block). Under the doctrine it must NEVER block, regardless
    of whether the rebind changed mode — because the gate no longer consults the lease
    record for its ALLOW/BLOCK verdict at all."""
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    harness_sid = "harness-native-sid-001"
    my_pid = os.getpid()

    target_1 = _write_target(ws, ctx, "TASKS.md")
    block_1 = _run(
        ws,
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target_1)},
            "harness_pid": my_pid,
        },
        session_id=harness_sid,
    )
    _assert_never_a_lock_block(block_1)

    # Seed the residual lease record the bug's topology requires, in its POST-adoption
    # shape directly: a synthetic bind-CLI session names the lease record, orphaning the
    # harness-native id that originally wrote it (the exact end-state the deleted
    # ``adopt_if_own_lineage`` production path used to produce against a same-lineage pid).
    synthetic_sid = "sess_synthetic99"
    _write_session_record(ws, synthetic_sid, rebind_mode)
    session_identity.set_incumbent(ws, ctx, synthetic_sid)
    _seed_lock_record(ws, ctx, synthetic_sid, pid=my_pid)
    rec_after_adopt = session_identity.read_incumbent_ptr(ws, ctx)
    assert rec_after_adopt == synthetic_sid

    # The SAME harness-native session writes again — must still never block, even though
    # the lease record now names a totally different (synthetic) session.
    target_2 = _write_target(ws, ctx, "PLAN.md")
    block_2 = _run(
        ws,
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target_2)},
            "harness_pid": my_pid,
        },
        session_id=harness_sid,
    )
    _assert_never_a_lock_block(block_2)


def test_critical_bug_probe_full_cycle_no_lockhelderror_anywhere(tmp_path: Path) -> None:
    """Belt-and-suspenders textual proof: across the whole bind -> write -> rebind ->
    write -> commit-adjacent cycle, no hook output ever carries the LockHeldError / SDD
    LOCK signature — the class of message the old implementation emitted on self-block."""
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    harness_sid = "harness-native-sid-002"
    my_pid = os.getpid()

    outputs: list[str] = []

    target_1 = _write_target(ws, ctx, "TASKS.md")
    env1 = claude_hook_env(ws, session_id=harness_sid)
    env1.pop("CLAUDE_CODE_SESSION_ID", None)
    env1.pop("DADAIA_CONTEXT", None)
    r1 = run_hook_subprocess(
        "pre_gate",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target_1)},
            "session_id": harness_sid,
            "harness_pid": my_pid,
        },
        env1,
    )
    outputs.append(r1.stdout + r1.stderr)

    # Seed the residual lease record in its post-adoption shape directly (see the sibling
    # parametrized test above for why: v0.1.76 T-3 deletes ``adopt_if_own_lineage``, so the
    # topology is reproduced as raw on-disk state rather than driven through that API).
    synthetic_sid = "sess_synthetic77"
    _write_session_record(ws, synthetic_sid, "IMPLEMENTATION")
    session_identity.set_incumbent(ws, ctx, synthetic_sid)
    _seed_lock_record(ws, ctx, synthetic_sid, pid=my_pid)

    target_2 = _write_target(ws, ctx, "PLAN.md")
    env2 = claude_hook_env(ws, session_id=harness_sid)
    env2.pop("CLAUDE_CODE_SESSION_ID", None)
    env2.pop("DADAIA_CONTEXT", None)
    r2 = run_hook_subprocess(
        "pre_gate",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target_2)},
            "session_id": harness_sid,
            "harness_pid": my_pid,
        },
        env2,
    )
    outputs.append(r2.stdout + r2.stderr)

    for out in outputs:
        lowered = out.lower()
        for pattern in _BLOCK_FORBIDDEN_PATTERNS:
            assert pattern not in lowered, f"forbidden lock signature leaked: {out!r}"


# --------------------------------------------------------------------------- #
# Mode self-scope: a foreign session's bind can never change my mode.
# --------------------------------------------------------------------------- #


def test_foreign_read_bind_never_imposes_read_on_my_mutating_write(tmp_path: Path) -> None:
    """A foreign session sets the context incumbent pointer to a READ-mode record. My
    OWN session (a different harness-native sid, no self-record) must resolve its own
    default mode (IMPLEMENTATION) and its MUTATING write must ALLOW — the context-
    incumbent mode-resolution rung is deleted."""
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    foreign_read_sid = "foreign-read-bind"
    my_sid = "my-own-harness-sid"

    _write_session_record(ws, foreign_read_sid, "READ")
    session_identity.set_incumbent(ws, ctx, foreign_read_sid)

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
    """Symmetric case: a foreign session's IMPLEMENTATION incumbent-pointer bind must not
    upgrade MY OWN read-bound session into a lease-taking mode either — mode resolution is
    strictly self-scoped in both directions."""
    ws = _mk_workspace(tmp_path, "dadaia-workspace")
    ctx = "dadaia-workspace"
    foreign_impl_sid = "foreign-impl-bind"
    my_read_sid = "my-own-read-bound"

    _write_session_record(ws, foreign_impl_sid, "IMPLEMENTATION")
    session_identity.set_incumbent(ws, ctx, foreign_impl_sid)
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
