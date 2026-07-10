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
  (c) PROTECTED (.dadaia/sessions/) is the sole fail-CLOSED path (kept as a standalone
      test AND as a param row under mode=READ — CRIT, never weakened).

CRIT: this file is the core of the SDD gate — path-class x lease x phase x mode,
pid-lineage (long-lived holder pid), and anti-downgrade liveness (NF-2/NF-4). Every one
of the 6 anti-downgrade decisions survives below as a named param row in the
liveness x precedence matrix — this matrix is the workspace's concurrency law.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.exceptions import LockHeldError
from dadaia_workspace.features.spec_context import gate_policy, lease, session_identity
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


def _write_session_record(ws: Path, session_id: str, mode: str) -> None:
    """Persist a minimal session record (id + mode) the way the bind CLI does."""
    session_identity.write_session(ws, session_id, {"session_id": session_id, "mode": mode})


def _write_lease_record(ws: Path, ctx: str, record: dict[str, object]) -> None:
    """Plant a raw lease record on disk (bypasses acquire so heartbeat/pid are controllable)."""
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / f"{ctx}.lock.json").write_text(json.dumps(record), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Behavior: ALLOW / BLOCK envelope under a real subprocess spawn.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "tool_name", "tool_input_fn", "expect_block", "reason_contains"),
    [
        ("non_write_tool", "Read", lambda ws: {"file_path": "x"}, False, None),
        ("unparseable_target", "Write", lambda ws: {}, False, None),
        (
            "ungated_path",
            "Write",
            lambda ws: {"file_path": str(ws / "README.md")},
            False,
            None,
        ),
        (
            # PARITY (c): .dadaia/sessions/ is the sole fail-CLOSED path — blocked
            # unconditionally.
            "protected_sessions_blocks",
            "Write",
            lambda ws: {"file_path": str(ws / ".dadaia" / "sessions" / "runtime" / "a.ptr")},
            True,
            "SEC-01",
        ),
    ],
)
def test_allow_parity(
    tmp_path: Path,
    name: str,
    tool_name: str,
    tool_input_fn: Any,
    expect_block: bool,
    reason_contains: str | None,
) -> None:
    ws = _mk_workspace(tmp_path, "a")
    block = _run(tmp_path, {"tool_name": tool_name, "tool_input": tool_input_fn(ws)})
    if expect_block:
        assert block is not None
        assert reason_contains is not None and reason_contains in block["reason"]
    else:
        assert block is None


@pytest.mark.parametrize(
    ("name", "second_header", "second_body", "expect_block", "reason_fragment"),
    [
        (
            # REGRESSION (T-014-02 / FR-W4-04): a multi-file apply_patch whose FIRST file
            # is allowed and whose SECOND file is FROZEN (specs/_archive/) blocks the
            # WHOLE patch. Before the fix, target_path() returned only the first header
            # (README.md), so the FROZEN file's block branch never evaluated and the
            # patch was allowed. Now every header is classified and the most restrictive
            # verdict wins.
            "frozen",
            "specs/_archive/x.md",
            "+frozen",
            True,
            "_archive",
        ),
        (
            # REGRESSION (T-014-02): a later PROTECTED (.dadaia/sessions/) header blocks
            # the patch.
            "protected",
            ".dadaia/sessions/runtime/a.ptr",
            "+forge",
            True,
            "SEC-01",
        ),
        (
            # A multi-file apply_patch where EVERY header is allowed is not blocked (no
            # false block).
            "all_allowed",
            "docs/notes.md",
            "+more",
            False,
            None,
        ),
    ],
)
def test_apply_patch_multi_file_most_restrictive(
    tmp_path: Path,
    name: str,
    second_header: str,
    second_body: str,
    expect_block: bool,
    reason_fragment: str | None,
) -> None:
    _mk_workspace(tmp_path, "a")
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: README.md\n"
        "+ok\n"
        f"*** Update File: {second_header}\n"
        f"{second_body}\n"
        "*** End Patch"
    )
    block = _run(tmp_path, {"tool_name": "apply_patch", "tool_input": {"command": cmd}})
    if expect_block:
        assert block is not None
        assert reason_fragment is not None
        assert (
            reason_fragment in block["reason"] or reason_fragment.upper() in block["reason"].upper()
        )
    else:
        assert block is None


def test_path_first_context_slug_parity_no_context_fails_open_and_live_foreign_blocks(
    tmp_path: Path,
) -> None:
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

    # A specs/releases/ path with no repo slug + no DADAIA_CONTEXT -> fail open (no lease).
    ws2 = _mk_workspace(tmp_path.parent / (tmp_path.name + "-no-ctx"), "a")
    target2 = ws2 / "specs" / "releases" / "x" / "TASKS.md"
    block2 = _run(
        ws2,
        {"tool_name": "Write", "tool_input": {"file_path": str(target2)}},
    )
    assert block2 is None

    # PARITY: a genuine fresh foreign lease held by THIS (alive) process makes the gate
    # BLOCK — reproduced harness-real by seeding a real lease, no monkeypatch of acquire.
    ws3 = _mk_workspace(tmp_path.parent / (tmp_path.name + "-foreign"), "B")
    lease.acquire(ws3, "B", "owner-A", "rel-1", "implementation", pid=os.getpid())
    target3 = ws3 / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target3.parent.mkdir(parents=True, exist_ok=True)
    block3 = _run(
        ws3,
        {"tool_name": "Write", "tool_input": {"file_path": str(target3)}},
        session_id="intruder",
    )
    assert block3 is not None
    # The yield-iff-live-foreign message names the holder and the contended context.
    assert "SDD LOCK" in block3["reason"]
    assert "owner-A" in block3["reason"]
    assert "context 'B'" in block3["reason"]


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
    monkeypatch.setattr(lease, "acquire", acquire)
    return gate_policy.evaluate(
        ws,
        "repos/B/specs/releases/rel-1/TASKS.md",
        ctx="B",
        phase="IMPLEMENTATION",
        session_id="s",
        release="rel-1",
        mode="IMPLEMENTATION",
    )


@pytest.mark.parametrize(
    ("name", "acquire_raises", "expected_decision", "reason_contains"),
    [
        (
            # PARITY (b): any non-LockHeldError from the lease subsystem -> ALLOW
            # (fail-open). Asserted at the policy layer (the fail-safe guarantee lives
            # in gate_policy.evaluate, AC-04).
            "fail_open_on_lease_error",
            RuntimeError("lease subsystem exploded"),
            gate_policy.Decision.ALLOW,
            "",
        ),
        (
            # A genuine live-foreign LockHeldError -> BLOCK with the informative yield
            # message.
            "live_foreign_lease_blocks",
            LockHeldError("context 'B' is held by another live session"),
            gate_policy.Decision.BLOCK,
            "another live session",
        ),
    ],
)
def test_gate_policy_fail_safe_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    acquire_raises: Exception,
    expected_decision: gate_policy.Decision,
    reason_contains: str,
) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise acquire_raises

    decision, reason = _evaluate_mutating(tmp_path, acquire=boom, monkeypatch=monkeypatch)
    assert decision == expected_decision
    assert reason_contains in reason


# --------------------------------------------------------------------------- #
# White-box: WS-R4 FR-R4-02/03/04 — gate mode resolution helper (_resolve_mode).
# These call the pure helper directly; no main(), no simulated stdin.
# --------------------------------------------------------------------------- #


def _setup_env_override_wins(ws: Path, mp: pytest.MonkeyPatch) -> None:
    # Order (1): DADAIA_MODE env override beats any session record. DADAIA_MODE
    # is an operator-shell escape (no harness sets it) and an allowlisted
    # operator-override env var.
    _write_session_record(ws, "sess-1", "READ")
    mp.setenv("DADAIA_MODE", "IMPLEMENTATION")


def _setup_session_record_path(ws: Path, mp: pytest.MonkeyPatch) -> None:
    # Order (2): with NO env var, the on-disk session record supplies the mode.
    # This is the harness-real path (a real hook subprocess never carries
    # DADAIA_MODE).
    _write_session_record(ws, "sess-read", "READ")
    mp.delenv("DADAIA_MODE", raising=False)


def _setup_default_implementation_when_absent(ws: Path, mp: pytest.MonkeyPatch) -> None:
    # Order (3): no env, no record → IMPLEMENTATION (FR-R4-04 / D-3, lease-capable).
    mp.delenv("DADAIA_MODE", raising=False)


@pytest.mark.parametrize(
    ("name", "setup_fn", "session_id", "expected_mode"),
    [
        ("env_override_wins", _setup_env_override_wins, "sess-1", "IMPLEMENTATION"),
        ("session_record_path", _setup_session_record_path, "sess-read", "READ"),
        (
            "default_implementation_when_absent",
            _setup_default_implementation_when_absent,
            "no-such-session",
            "IMPLEMENTATION",
        ),
    ],
)
def test_resolve_mode_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    setup_fn: Any,
    session_id: str,
    expected_mode: str,
) -> None:
    ws = _mk_workspace(tmp_path, "a")
    setup_fn(ws, monkeypatch)
    assert sdd_gate._resolve_mode(ws, session_id) == expected_mode


# --------------------------------------------------------------------------- #
# Behavior: WS-R4 READ non-acquiring + BOUND_REVIEW/missing acquire, via subprocess.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    (
        "session_id",
        "session_mode",
        "target_fn",
        "expect_block",
        "lease_forbidden",
        "lease_expected",
        "reason_checks",
        "reason_lower",
    ),
    [
        pytest.param(
            "sess-read",
            "READ",
            lambda ws: ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md",
            True,
            True,
            False,
            ("read", "--mode implementation"),
            True,
            id="read-mode-blocks-mutating-no-lease-written",
        ),
        pytest.param(
            "sess-read",
            "READ",
            lambda ws: ws / "repos" / "B" / "specs" / "bugs" / "some-bug.md",
            False,
            False,
            False,
            (),
            False,
            id="read-mode-allows-additive-in-repo",
        ),
        pytest.param(
            "sess-read",
            "READ",
            lambda ws: ws / ".dadaia" / "sessions" / "runtime" / "B.ptr",
            True,
            False,
            False,
            ("SEC-01",),
            False,
            id="read-mode-protected-still-blocks",
        ),
        pytest.param(
            # FR-R4-03 / D-3: only explicit READ blocks MUTATING. BOUND_REVIEW is
            # lease-taking, so a free lease is acquired exactly like implementation.
            "sess-rev",
            "BOUND_REVIEW",
            lambda ws: ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md",
            False,
            False,
            True,
            (),
            False,
            id="bound-review-acquires-like-implementation",
        ),
        pytest.param(
            # FR-R4-04: no bind record, no env → IMPLEMENTATION; free-lease acquire
            # proceeds. (session_id "unbound" has no record at all — session_mode=None.)
            "unbound",
            None,
            lambda ws: ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md",
            False,
            False,
            True,
            (),
            False,
            id="missing-mode-acquires-free-lease",
        ),
    ],
)
def test_read_mode_matrix(
    tmp_path: Path,
    session_id: str,
    session_mode: str | None,
    target_fn: Any,
    expect_block: bool,
    lease_forbidden: bool,
    lease_expected: bool,
    reason_checks: tuple[str, ...],
    reason_lower: bool,
) -> None:
    # FR-R4-03: READ-bound session's write outcome depends on path class. MUTATING →
    # BLOCK (non-acquiring, no lease record, --mode implementation hint). ADDITIVE →
    # ALLOW. PROTECTED stays fail-closed regardless of mode (second CRIT row for
    # PROTECTED — see test_allow_parity's protected_sessions_blocks row for the base
    # IMPLEMENTATION case). BOUND_REVIEW and missing-mode(unbound) both acquire a free
    # lease exactly like IMPLEMENTATION — only explicit READ blocks MUTATING.
    ws = _mk_workspace(tmp_path, "B")
    if session_mode is not None:
        _write_session_record(ws, session_id, session_mode)
    target = target_fn(ws)
    target.parent.mkdir(parents=True, exist_ok=True)
    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id=session_id,
    )
    if expect_block:
        assert block is not None
        reason = block["reason"].lower() if reason_lower else block["reason"]
        for check in reason_checks:
            assert check in reason
    else:
        assert block is None
    if lease_forbidden:
        # Non-acquiring: the gate must NOT have created the lease record.
        assert not (ws / ".dadaia" / "states" / "ctx_locks" / "B.lock.json").exists()
    if lease_expected:
        assert (ws / ".dadaia" / "states" / "ctx_locks" / "B.lock.json").exists()


# --------------------------------------------------------------------------- #
# White-box: NF-1 (rc-2) — the gate records a LONG-LIVED holder pid (getppid /
# payload), never the ephemeral hook child's own. _resolve_holder_pid is pure.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "payload", "expected"),
    [
        (
            # In a real hook subprocess the harness is the PARENT; getppid() is the
            # long-lived pid. The hook's own os.getpid() is ephemeral and would make the
            # no-steal veto probe a dead pid, so it must NEVER be recorded. With no
            # payload pid hint, getppid() is used.
            "defaults_to_parent_pid",
            {},
            "getppid",
        ),
        # A harness that sends an explicit long-lived pid is honored (int and string
        # forms).
        ("prefers_payload_harness_pid_int", {"harness_pid": 4242}, 4242),
        ("prefers_payload_parent_pid_str", {"parent_pid": "5151"}, 5151),
        ("prefers_payload_ppid_int", {"ppid": 6262}, 6262),
        # Non-positive / unparseable payload pids fall back to getppid(), never to
        # 0/negative.
        ("ignores_zero_pid", {"harness_pid": 0}, "getppid"),
        ("ignores_negative_pid", {"harness_pid": -3}, "getppid"),
        ("ignores_unparseable_pid", {"harness_pid": "nope"}, "getppid"),
    ],
)
def test_resolve_holder_pid(
    tmp_path: Path, name: str, payload: dict[str, object], expected: object
) -> None:
    want = os.getppid() if expected == "getppid" else expected
    assert sdd_gate._resolve_holder_pid(payload) == want

    if name == "prefers_payload_harness_pid_int":
        # End-to-end companion: through the real hook subprocess, a payload-supplied
        # harness pid is the pid stamped into the lease record (proving the gate
        # threads the LONG-LIVED pid, not its own ephemeral child pid). Uses a
        # known-alive pid (this test process), not the synthetic 4242 above.
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
# White-box: NF-2/NF-4 (rc-2) — context-incumbent mode resolution + anti-downgrade
# liveness x precedence matrix. Every anti-downgrade decision survives as a named row:
# self-record wins over incumbent, live-holder overrides incumbent, no-holder honors
# incumbent, dead-leftover honored (NF-4), live-divergent overrides, plain fallback.
# --------------------------------------------------------------------------- #


def _setup_incumbent_fallback(ws: Path) -> tuple[str, str]:
    # NF-2: a `dadaia context bind --mode read` mints a sid the harness never reports,
    # but it refreshes the context incumbent pointer. A DIFFERENT harness sid (no self
    # record, no env) resolves READ through the incumbent pointer → record.
    bind_sid = "sess_bind01"
    _write_session_record(ws, bind_sid, "READ")
    session_identity.set_incumbent(ws, "a", bind_sid)
    return "harness-sid-xyz", "READ"


def _setup_self_record_wins(ws: Path) -> tuple[str, str]:
    # Precedence: a record keyed to the harness sid wins over the incumbent pointer — a
    # live implementation session is never downgraded by another session's read-bind.
    read_sid = "sess_read01"
    _write_session_record(ws, read_sid, "READ")
    session_identity.set_incumbent(ws, "a", read_sid)
    impl_sid = "harness-impl"
    _write_session_record(ws, impl_sid, "BOUND_IMPLEMENTATION")
    return impl_sid, "BOUND_IMPLEMENTATION"


def _setup_live_holder_overrides_incumbent(ws: Path) -> tuple[str, str]:
    # Anti-downgrade (NF-2): a stale read-bind set the incumbent, but a DIFFERENT
    # session then acquired the implementation lease. The live holder must not be
    # downgraded to READ — the stale incumbent is ignored and the resolving session
    # defaults to IMPLEMENTATION.
    read_sid = "sess_readstale"
    _write_session_record(ws, read_sid, "READ")
    session_identity.set_incumbent(ws, "a", read_sid)
    lease.acquire(ws, "a", "live-impl", "rel-1", "IMPLEMENTATION")
    return "live-impl", "IMPLEMENTATION"


def _setup_no_holder_honors_incumbent(ws: Path) -> tuple[str, str]:
    # No lease holder yet ⇒ the read-bind incumbent still governs (a read session takes
    # no lease, so absence of a holder is the normal read-bound state, not staleness).
    bind_sid = "sess_nolease"
    _write_session_record(ws, bind_sid, "READ")
    session_identity.set_incumbent(ws, "a", bind_sid)
    assert not (ws / ".dadaia" / "states" / "ctx_locks" / "a.lock.json").exists()
    return "another-harness-sid", "READ"


def _setup_dead_leftover_honored(ws: Path) -> tuple[str, str]:
    # NF-4: the canonical review flow — an implementation session finished, leaving a
    # TTL-stale lock record with a dead pid (nothing deletes it until takeover/GC), then
    # the operator runs `bind --mode read`. The dead leftover's sid differs from the
    # read-bind sid, but it is NOT live, so the incumbent READ must be honored (not
    # silently downgraded).
    stale_hb = (datetime.now(tz=UTC) - timedelta(seconds=10_000)).isoformat()
    _write_lease_record(
        ws, "a", {"session_id": "old-impl", "heartbeat": stale_hb, "ttl": 120, "pid": 0}
    )
    bind_sid = "sess_freshread"
    _write_session_record(ws, bind_sid, "READ")
    session_identity.set_incumbent(ws, "a", bind_sid)
    return "harness-reviewer", "READ"


def _setup_live_divergent_overrides_read(ws: Path) -> tuple[str, str]:
    # Anti-downgrade preserved: a TTL-fresh divergent holder (live) defeats the
    # read-bind incumbent — the live implementation session is not downgraded to READ.
    fresh_hb = datetime.now(tz=UTC).isoformat()
    _write_lease_record(
        ws, "a", {"session_id": "live-impl", "heartbeat": fresh_hb, "ttl": 120, "pid": 0}
    )
    read_sid = "sess_staleread"
    _write_session_record(ws, read_sid, "READ")
    session_identity.set_incumbent(ws, "a", read_sid)
    return "harness-other", "IMPLEMENTATION"


@pytest.mark.parametrize(
    ("name", "setup_fn"),
    [
        ("incumbent_fallback", _setup_incumbent_fallback),
        ("self_record_wins_over_incumbent", _setup_self_record_wins),
        ("live_holder_overrides_incumbent", _setup_live_holder_overrides_incumbent),
        ("no_holder_honors_incumbent", _setup_no_holder_honors_incumbent),
        ("dead_leftover_honored_nf4", _setup_dead_leftover_honored),
        ("live_divergent_overrides_read_incumbent", _setup_live_divergent_overrides_read),
    ],
)
def test_resolve_mode_liveness_precedence_matrix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, setup_fn: Any
) -> None:
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    resolving_sid, expected_mode = setup_fn(ws)
    assert sdd_gate._resolve_mode(ws, resolving_sid, "a") == expected_mode

    if name == "dead_leftover_honored_nf4":
        # End-to-end companion (NF-4): the SAME dead-leftover + fresh-READ-incumbent
        # setup, driven through the real hook subprocess, blocks a MUTATING write
        # (READ enforced) rather than merely resolving READ in isolation.
        ws2 = _mk_workspace(tmp_path.parent / (tmp_path.name + "-e2e"), "a")
        stale_hb2 = (datetime.now(tz=UTC) - timedelta(seconds=10_000)).isoformat()
        _write_lease_record(
            ws2,
            "a",
            {"session_id": "old-impl", "heartbeat": stale_hb2, "ttl": 120, "pid": 0},
        )
        bind_sid2 = "sess_freshread2"
        _write_session_record(ws2, bind_sid2, "READ")
        session_identity.set_incumbent(ws2, "a", bind_sid2)
        target2 = ws2 / "repos" / "a" / "src" / "mod.py"
        payload2 = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target2), "content": "x = 1\n"},
        }
        env2 = claude_hook_env(ws2, session_id="harness-reviewer2")
        env2.pop("CLAUDE_CODE_SESSION_ID", None)
        env2.pop("DADAIA_CONTEXT", None)
        result2 = run_hook_subprocess(
            "sdd_gate", {**payload2, "session_id": "harness-reviewer2"}, env2
        )
        assert result2.returncode == 0, result2.stderr
        assert result2.block_envelope() is not None  # READ enforced ⇒ MUTATING blocked
