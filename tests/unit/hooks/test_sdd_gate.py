"""Behavior + white-box tests for dadaia_workspace.hooks.sdd_gate.

Two test layers, each driven through its harness-real channel:

* **Behavior** (the gate's ALLOW/BLOCK envelope on a real PreToolUse) is exercised by
  spawning the hook as a subprocess via :func:`run_hook_subprocess` + :func:`claude_hook_env`
  — never by patching ``sys.stdin`` and calling ``sdd_gate.main()`` in-process (the
  simulated-stdin pattern the harness-env contract bans).
* **White-box** unit tests target the pure helper ``sdd_gate._resolve_mode`` and the
  fail-safe contract of ``gate_policy.evaluate`` directly. These never simulate harness
  stdin; the lease fault-injection (arbitrary error ⇒ ALLOW; live-foreign ⇒ BLOCK) is a
  property of the *policy* layer, so it is asserted there rather than through the hook.

Mandatory rc-4 parity invariants covered:
  (a) PATH-first context slug: a write under repos/B never acquires repos/A's lease.
  (b) Fail-open: any non-PROTECTED, non-live-foreign error -> ALLOW.
  (c) PROTECTED (.dadaia/sessions/) is the sole fail-CLOSED path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.spec_context import gate_policy, session_identity
from dadaia_workspace.hooks import sdd_gate
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


def _mk_workspace(tmp_path: Path, *slugs: str) -> Path:
    """Build a minimal workspace with repos/<slug>/specs/releases/ACTIVE.md for each slug."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": s, "state": "alive"} for s in slugs]}),
        encoding="utf-8",
    )
    for s in slugs:
        rel = tmp_path / "repos" / s / "specs" / "releases"
        rel.mkdir(parents=True)
        (rel / "ACTIVE.md").write_text("release: rel-1\nphase: IMPLEMENTATION\n", encoding="utf-8")
    return tmp_path


def _run(
    tmp_path: Path,
    payload: dict[str, Any],
    *,
    session_id: str = "claude-sess",
) -> dict[str, Any] | None:
    """Spawn sdd_gate as a real subprocess; return the parsed BLOCK envelope (or None=ALLOW).

    The session id is supplied through the stdin ``session_id`` field (the harness-real
    channel); ``claude_hook_env``'s native ``CLAUDE_CODE_SESSION_ID`` is popped so resolution
    falls to the payload field, matching how these gate paths are driven. ``DADAIA_CONTEXT``
    is popped so the PATH-first slug derivation is the only context source.
    """
    env = claude_hook_env(tmp_path, session_id=session_id)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    full_payload = {**payload, "session_id": session_id}
    result = run_hook_subprocess("sdd_gate", full_payload, env)
    assert result.returncode == 0, result.stderr
    return result.block_envelope()


# --------------------------------------------------------------------------- #
# Behavior: ALLOW / BLOCK envelope under a real subprocess spawn.
# --------------------------------------------------------------------------- #


def test_non_write_tool_allows(tmp_path: Path) -> None:
    _mk_workspace(tmp_path, "a")
    block = _run(tmp_path, {"tool_name": "Read", "tool_input": {"file_path": "x"}})
    assert block is None


def test_unparseable_target_allows(tmp_path: Path) -> None:
    _mk_workspace(tmp_path, "a")
    block = _run(tmp_path, {"tool_name": "Write", "tool_input": {}})
    assert block is None


def test_ungated_path_allows(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path, "a")
    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "README.md")}},
    )
    assert block is None


def test_protected_sessions_blocks(tmp_path: Path) -> None:
    # PARITY (c): .dadaia/sessions/ is the sole fail-CLOSED path — blocked unconditionally.
    ws = _mk_workspace(tmp_path, "a")
    target = ws / ".dadaia" / "sessions" / "runtime" / "a.ptr"
    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
    )
    assert block is not None
    assert "SEC-01" in block["reason"]


def test_apply_patch_multi_file_frozen_blocks_whole_patch(tmp_path: Path) -> None:
    """REGRESSION (T-014-02 / FR-W4-04): a multi-file apply_patch whose FIRST file is
    allowed and whose SECOND file is FROZEN (specs/_archive/) blocks the WHOLE patch.

    Before the fix, target_path() returned only the first header (README.md), so the
    FROZEN file's block branch never evaluated and the patch was allowed. Now every
    header is classified and the most restrictive verdict wins.
    """
    _mk_workspace(tmp_path, "a")
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: README.md\n"
        "+ok\n"
        "*** Update File: specs/_archive/x.md\n"
        "+frozen\n"
        "*** End Patch"
    )
    block = _run(tmp_path, {"tool_name": "apply_patch", "tool_input": {"command": cmd}})
    assert block is not None
    assert "_archive" in block["reason"] or "FROZEN" in block["reason"].upper()


def test_apply_patch_multi_file_protected_blocks_whole_patch(tmp_path: Path) -> None:
    """REGRESSION (T-014-02): a later PROTECTED (.dadaia/sessions/) header blocks the patch."""
    _mk_workspace(tmp_path, "a")
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: README.md\n"
        "+ok\n"
        "*** Update File: .dadaia/sessions/runtime/a.ptr\n"
        "+forge\n"
        "*** End Patch"
    )
    block = _run(tmp_path, {"tool_name": "apply_patch", "tool_input": {"command": cmd}})
    assert block is not None
    assert "SEC-01" in block["reason"]


def test_apply_patch_multi_file_all_allowed_passes(tmp_path: Path) -> None:
    """A multi-file apply_patch where EVERY header is allowed is not blocked (no false block)."""
    _mk_workspace(tmp_path, "a")
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: README.md\n"
        "+ok\n"
        "*** Update File: docs/notes.md\n"
        "+more\n"
        "*** End Patch"
    )
    block = _run(tmp_path, {"tool_name": "apply_patch", "tool_input": {"command": cmd}})
    assert block is None


def test_path_first_context_slug_parity(tmp_path: Path) -> None:
    # PARITY (a): first-ALIVE is repos/A, but a write under repos/B MUST acquire repos/B's
    # lease, never repos/A's (fixes gate-cross-context-lock-contamination).
    ws = _mk_workspace(tmp_path, "A", "B")  # A is first-ALIVE
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="sess-1",
    )
    assert block is None  # acquired cleanly (no foreign conflict)
    # The lease record must be for context B, never A.
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    assert (lock_dir / "B.lock.json").exists()
    assert not (lock_dir / "A.lock.json").exists()


def test_mutating_no_context_fails_open(tmp_path: Path) -> None:
    # A specs/releases/ path with no repo slug + no DADAIA_CONTEXT -> fail open (no lease).
    ws = _mk_workspace(tmp_path, "a")
    target = ws / "specs" / "releases" / "x" / "TASKS.md"
    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
    )
    assert block is None


def test_live_foreign_lease_blocks_real(tmp_path: Path) -> None:
    # PARITY: a genuine fresh foreign lease held by THIS (alive) process makes the gate BLOCK
    # — reproduced harness-real by seeding a real lease, no monkeypatch of acquire.
    import os

    from dadaia_workspace.features.spec_context import lease

    ws = _mk_workspace(tmp_path, "B")
    # A different session already holds B's lease, stamped with a live pid (this process).
    lease.acquire(ws, "B", "owner-A", "rel-1", "implementation", pid=os.getpid())
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="intruder",
    )
    assert block is not None
    # The yield-iff-live-foreign message names the holder and the contended context.
    assert "SDD LOCK" in block["reason"]
    assert "owner-A" in block["reason"]
    assert "context 'B'" in block["reason"]


# --------------------------------------------------------------------------- #
# White-box: gate_policy.evaluate fail-safe contract (no hook, no stdin).
# --------------------------------------------------------------------------- #


def _evaluate_mutating(
    tmp_path: Path,
    *,
    acquire: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[gate_policy.Decision, str]:
    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setattr(gate_policy.lease, "acquire", acquire)
    return gate_policy.evaluate(
        ws,
        "repos/B/specs/releases/rel-1/TASKS.md",
        ctx="B",
        phase="IMPLEMENTATION",
        session_id="s",
        release="rel-1",
        mode="IMPLEMENTATION",
    )


def test_fail_open_on_lease_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # PARITY (b): any non-LockHeldError from the lease subsystem -> ALLOW (fail-open). Asserted
    # at the policy layer (the fail-safe guarantee lives in gate_policy.evaluate, AC-04).
    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("lease subsystem exploded")

    decision, reason = _evaluate_mutating(tmp_path, acquire=boom, monkeypatch=monkeypatch)
    assert decision == gate_policy.Decision.ALLOW
    assert reason == ""


def test_live_foreign_lease_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # A genuine live-foreign LockHeldError -> BLOCK with the informative yield message.
    from dadaia_workspace.core.exceptions import LockHeldError

    def held(*_a: object, **_k: object) -> None:
        raise LockHeldError("context 'B' is held by another live session")

    decision, reason = _evaluate_mutating(tmp_path, acquire=held, monkeypatch=monkeypatch)
    assert decision == gate_policy.Decision.BLOCK
    assert "another live session" in reason


# --------------------------------------------------------------------------- #
# White-box: WS-R4 FR-R4-02/03/04 — gate mode resolution helper (_resolve_mode).
# These call the pure helper directly; no main(), no simulated stdin.
# --------------------------------------------------------------------------- #


def _write_session_record(ws: Path, session_id: str, mode: str) -> None:
    """Persist a minimal session record (id + mode) the way the bind CLI does."""
    session_identity.write_session(ws, session_id, {"session_id": session_id, "mode": mode})


def test_resolve_mode_env_override_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Order (1): DADAIA_MODE env override beats any session record. DADAIA_MODE is an
    # operator-shell escape (no harness sets it) and an allowlisted operator-override env var.
    ws = _mk_workspace(tmp_path, "a")
    _write_session_record(ws, "sess-1", "READ")
    monkeypatch.setenv("DADAIA_MODE", "IMPLEMENTATION")
    assert sdd_gate._resolve_mode(ws, "sess-1") == "IMPLEMENTATION"


def test_resolve_mode_session_record_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Order (2): with NO env var, the on-disk session record supplies the mode. This is the
    # harness-real path (a real hook subprocess never carries DADAIA_MODE).
    ws = _mk_workspace(tmp_path, "a")
    _write_session_record(ws, "sess-read", "READ")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    assert sdd_gate._resolve_mode(ws, "sess-read") == "READ"


def test_resolve_mode_default_implementation_when_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Order (3): no env, no record → IMPLEMENTATION (FR-R4-04 / D-3, lease-capable).
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    assert sdd_gate._resolve_mode(ws, "no-such-session") == "IMPLEMENTATION"


# --------------------------------------------------------------------------- #
# Behavior: WS-R4 READ non-acquiring + BOUND_REVIEW/missing acquire, via subprocess.
# --------------------------------------------------------------------------- #


def test_read_mode_blocks_mutating_no_lease_written(tmp_path: Path) -> None:
    # FR-R4-03: a READ-bound session's MUTATING write → BLOCK, and NO lease record is
    # written (non-acquiring). Message names the documented path, with no auto-rebind nag.
    ws = _mk_workspace(tmp_path, "B")
    _write_session_record(ws, "sess-read", "READ")
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="sess-read",
    )
    assert block is not None
    assert "read" in block["reason"].lower()
    assert "--mode implementation" in block["reason"]
    # Non-acquiring: the gate must NOT have created the lease record.
    assert not (ws / ".dadaia" / "states" / "ctx_locks" / "B.lock.json").exists()


def test_read_mode_allows_additive_in_repo(tmp_path: Path) -> None:
    # FR-R4-03: a READ session's ADDITIVE write (in-repo specs/bugs) is allowed.
    ws = _mk_workspace(tmp_path, "B")
    _write_session_record(ws, "sess-read", "READ")
    target = ws / "repos" / "B" / "specs" / "bugs" / "some-bug.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="sess-read",
    )
    assert block is None


def test_read_mode_protected_still_blocks(tmp_path: Path) -> None:
    # PROTECTED stays fail-closed regardless of mode (unchanged by R4).
    ws = _mk_workspace(tmp_path, "B")
    _write_session_record(ws, "sess-read", "READ")
    target = ws / ".dadaia" / "sessions" / "runtime" / "B.ptr"
    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="sess-read",
    )
    assert block is not None
    assert "SEC-01" in block["reason"]


def test_bound_review_acquires_like_implementation(tmp_path: Path) -> None:
    # FR-R4-03 / D-3: only explicit READ blocks MUTATING. BOUND_REVIEW is lease-taking, so a
    # free lease is acquired exactly like implementation.
    ws = _mk_workspace(tmp_path, "B")
    _write_session_record(ws, "sess-rev", "BOUND_REVIEW")
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="sess-rev",
    )
    assert block is None  # acquired cleanly
    assert (ws / ".dadaia" / "states" / "ctx_locks" / "B.lock.json").exists()


def test_missing_mode_acquires_free_lease(tmp_path: Path) -> None:
    # FR-R4-04: no bind record, no env → IMPLEMENTATION; free-lease acquire proceeds.
    ws = _mk_workspace(tmp_path, "B")
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="unbound",
    )
    assert block is None
    assert (ws / ".dadaia" / "states" / "ctx_locks" / "B.lock.json").exists()


# --------------------------------------------------------------------------- #
# White-box: NF-1 (rc-2) — the gate records a LONG-LIVED holder pid (getppid /
# payload), never the ephemeral hook child's own. _resolve_holder_pid is pure.
# --------------------------------------------------------------------------- #


def test_resolve_holder_pid_defaults_to_parent_pid() -> None:
    # In a real hook subprocess the harness is the PARENT; getppid() is the long-lived pid.
    # The hook's own os.getpid() is ephemeral and would make the no-steal veto probe a dead
    # pid, so it must NEVER be recorded. With no payload pid hint, getppid() is used.
    import os

    assert sdd_gate._resolve_holder_pid({}) == os.getppid()


def test_resolve_holder_pid_prefers_payload_harness_pid() -> None:
    # A harness that sends an explicit long-lived pid is honored (int and string forms).
    assert sdd_gate._resolve_holder_pid({"harness_pid": 4242}) == 4242
    assert sdd_gate._resolve_holder_pid({"parent_pid": "5151"}) == 5151
    assert sdd_gate._resolve_holder_pid({"ppid": 6262}) == 6262


def test_resolve_holder_pid_ignores_bad_payload_pid() -> None:
    # Non-positive / unparseable payload pids fall back to getppid(), never to 0/negative.
    import os

    assert sdd_gate._resolve_holder_pid({"harness_pid": 0}) == os.getppid()
    assert sdd_gate._resolve_holder_pid({"harness_pid": -3}) == os.getppid()
    assert sdd_gate._resolve_holder_pid({"harness_pid": "nope"}) == os.getppid()


def test_gate_threads_payload_pid_into_lease_record(tmp_path: Path) -> None:
    # End-to-end through the real hook subprocess: a payload-supplied harness pid is the pid
    # stamped into the lease record (proving the gate threads the LONG-LIVED pid, not its own
    # ephemeral child pid). The pid is a known-alive process (this test process).
    import os

    from dadaia_workspace.features.spec_context import lease

    ws = _mk_workspace(tmp_path, "B")
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    my_pid = os.getpid()
    block = _run(
        tmp_path,
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
            "harness_pid": my_pid,
        },
        session_id="s-pid",
    )
    assert block is None
    rec = lease.read_record(ws, "B")
    assert rec is not None and rec["pid"] == my_pid, rec


# --------------------------------------------------------------------------- #
# White-box: NF-2 (rc-2) — context-incumbent mode resolution + anti-downgrade.
# --------------------------------------------------------------------------- #


def test_resolve_mode_falls_back_to_context_incumbent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # NF-2: a `dadaia context bind --mode read` mints a sid the harness never reports, but it
    # refreshes the context incumbent pointer. A DIFFERENT harness sid (no self record, no env)
    # resolves READ through the incumbent pointer → record.
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    bind_sid = "sess_bind01"
    _write_session_record(ws, bind_sid, "READ")
    session_identity.set_incumbent(ws, "a", bind_sid)
    assert sdd_gate._resolve_mode(ws, "harness-sid-xyz", "a") == "READ"


def test_resolve_mode_self_record_wins_over_incumbent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Precedence: a record keyed to the harness sid wins over the incumbent pointer — a live
    # implementation session is never downgraded by another session's read-bind.
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    read_sid = "sess_read01"
    _write_session_record(ws, read_sid, "READ")
    session_identity.set_incumbent(ws, "a", read_sid)
    impl_sid = "harness-impl"
    _write_session_record(ws, impl_sid, "BOUND_IMPLEMENTATION")
    assert sdd_gate._resolve_mode(ws, impl_sid, "a") == "BOUND_IMPLEMENTATION"


def test_resolve_mode_incumbent_ignored_when_live_holder_differs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Anti-downgrade (NF-2): a stale read-bind set the incumbent, but a DIFFERENT session then
    # acquired the implementation lease. The live holder must not be downgraded to READ — the
    # stale incumbent is ignored and the resolving session defaults to IMPLEMENTATION.
    from dadaia_workspace.features.spec_context import lease

    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    read_sid = "sess_readstale"
    _write_session_record(ws, read_sid, "READ")
    session_identity.set_incumbent(ws, "a", read_sid)
    lease.acquire(ws, "a", "live-impl", "rel-1", "IMPLEMENTATION")
    assert sdd_gate._resolve_mode(ws, "live-impl", "a") == "IMPLEMENTATION"


def test_resolve_mode_incumbent_honored_when_no_lease_holder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # No lease holder yet ⇒ the read-bind incumbent still governs (a read session takes no
    # lease, so absence of a holder is the normal read-bound state, not staleness).
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    bind_sid = "sess_nolease"
    _write_session_record(ws, bind_sid, "READ")
    session_identity.set_incumbent(ws, "a", bind_sid)
    assert not (ws / ".dadaia" / "states" / "ctx_locks" / "a.lock.json").exists()
    assert sdd_gate._resolve_mode(ws, "another-harness-sid", "a") == "READ"


# --------------------------------------------------------------------------- #
# White-box: NF-4 (rc-2) — anti-downgrade guard must test record LIVENESS, not
# mere presence. A dead leftover lock record (the normal residue after an
# implementation session ends) must NOT defeat a fresh `bind --mode read`.
# --------------------------------------------------------------------------- #


def _write_lease_record(ws: Path, ctx: str, record: dict[str, object]) -> None:
    """Plant a raw lease record on disk (bypasses acquire so heartbeat/pid are controllable)."""
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / f"{ctx}.lock.json").write_text(json.dumps(record), encoding="utf-8")


def test_resolve_mode_dead_leftover_record_does_not_defeat_read_bind(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # NF-4: the canonical review flow — an implementation session finished, leaving a
    # TTL-stale lock record with a dead pid (nothing deletes it until takeover/GC), then the
    # operator runs `bind --mode read`. The dead leftover's sid differs from the read-bind sid,
    # but it is NOT live, so the incumbent READ must be honored (not silently downgraded).
    from datetime import UTC, datetime, timedelta

    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    stale_hb = (datetime.now(tz=UTC) - timedelta(seconds=10_000)).isoformat()
    _write_lease_record(
        ws,
        "a",
        {"session_id": "old-impl", "heartbeat": stale_hb, "ttl": 120, "pid": 0},
    )
    bind_sid = "sess_freshread"
    _write_session_record(ws, bind_sid, "READ")
    session_identity.set_incumbent(ws, "a", bind_sid)
    assert sdd_gate._resolve_mode(ws, "harness-reviewer", "a") == "READ"


def test_resolve_mode_dead_leftover_record_blocks_mutating_write(tmp_path: Path) -> None:
    # End-to-end: with a dead leftover record + fresh READ incumbent, a MUTATING write is
    # blocked (READ enforced), and no lease is written by the blocked attempt.
    from datetime import UTC, datetime, timedelta

    ws = _mk_workspace(tmp_path, "a")
    stale_hb = (datetime.now(tz=UTC) - timedelta(seconds=10_000)).isoformat()
    _write_lease_record(
        ws,
        "a",
        {"session_id": "old-impl", "heartbeat": stale_hb, "ttl": 120, "pid": 0},
    )
    bind_sid = "sess_freshread2"
    _write_session_record(ws, bind_sid, "READ")
    session_identity.set_incumbent(ws, "a", bind_sid)
    target = ws / "repos" / "a" / "src" / "mod.py"
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target), "content": "x = 1\n"},
    }
    env = claude_hook_env(ws, session_id="harness-reviewer2")
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    result = run_hook_subprocess("sdd_gate", {**payload, "session_id": "harness-reviewer2"}, env)
    assert result.returncode == 0, result.stderr
    assert result.block_envelope() is not None  # READ enforced ⇒ MUTATING blocked


def test_resolve_mode_live_divergent_record_overrides_read_incumbent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Anti-downgrade preserved: a TTL-fresh divergent holder (live) defeats the read-bind
    # incumbent — the live implementation session is not downgraded to READ.
    from datetime import UTC, datetime

    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    fresh_hb = datetime.now(tz=UTC).isoformat()
    _write_lease_record(
        ws,
        "a",
        {"session_id": "live-impl", "heartbeat": fresh_hb, "ttl": 120, "pid": 0},
    )
    read_sid = "sess_staleread"
    _write_session_record(ws, read_sid, "READ")
    session_identity.set_incumbent(ws, "a", read_sid)
    assert sdd_gate._resolve_mode(ws, "harness-other", "a") == "IMPLEMENTATION"
