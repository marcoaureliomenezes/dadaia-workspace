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

from dadaia_workspace.features.spec_context import gate_policy, presence, session_identity
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


def test_path_first_context_slug_parity_no_context_fails_open_never_blocks(
    tmp_path: Path,
) -> None:
    # PARITY (a): first-ALIVE is repos/A, but a write under repos/B MUST attribute
    # presence to repos/B, never repos/A (fixes gate-cross-context-lock-contamination).
    ws = _mk_workspace(tmp_path, "A", "B")  # A is first-ALIVE
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="sess-1",
    )
    assert block is None  # v0.1.76: never blocks on concurrency
    # The presence record must be for context B, never A.
    presence_root = ws / ".dadaia" / "states" / "presence"
    assert (presence_root / "B" / "sess-1.json").exists()
    assert not (presence_root / "A").exists()

    # A specs/releases/ path with no repo slug + no DADAIA_CONTEXT -> fail open (no
    # presence target attributable).
    ws2 = _mk_workspace(tmp_path.parent / (tmp_path.name + "-no-ctx"), "a")
    target2 = ws2 / "specs" / "releases" / "x" / "TASKS.md"
    block2 = _run(
        ws2,
        {"tool_name": "Write", "tool_input": {"file_path": str(target2)}},
    )
    assert block2 is None

    # DOCTRINE (v0.1.76): a genuinely live foreign session's presence on the SAME
    # context never blocks — the write ALLOWs (advisory only), reproduced harness-real
    # by seeding a real presence record, no monkeypatch of the gate.
    ws3 = _mk_workspace(tmp_path.parent / (tmp_path.name + "-foreign"), "B")
    presence.upsert(ws3, "B", "owner-A", runtime="claude", pid=os.getpid())
    target3 = ws3 / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target3.parent.mkdir(parents=True, exist_ok=True)
    block3 = _run(
        ws3,
        {"tool_name": "Write", "tool_input": {"file_path": str(target3)}},
        session_id="intruder",
    )
    assert block3 is None


# --------------------------------------------------------------------------- #
# White-box: gate_policy.evaluate fail-safe contract (no hook, no stdin).
# --------------------------------------------------------------------------- #


def _evaluate_mutating(tmp_path: Path) -> tuple[gate_policy.Decision, str]:
    ws = _mk_workspace(tmp_path, "B")
    return gate_policy.evaluate(
        ws,
        "repos/B/specs/releases/rel-1/TASKS.md",
        ctx="B",
        phase="IMPLEMENTATION",
        session_id="s",
        release="rel-1",
        mode="IMPLEMENTATION",
    )


def test_gate_policy_fail_safe_contract_presence_error_never_blocks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """v0.1.76 doctrine (AC-04 successor): a MUTATING write is NEVER blocked because of
    another session. Even if the presence subsystem itself explodes, the write ALLOWs —
    ``presence.upsert``/``others_alive`` are internally fail-soft (see
    ``features/spec_context/presence.py``), and ``gate_policy.evaluate`` no longer has
    any acquisition call site that can raise a block-worthy error at all."""

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("presence subsystem exploded")

    monkeypatch.setattr(presence, "upsert", boom)
    monkeypatch.setattr(presence, "others_alive", boom)
    decision, _reason = _evaluate_mutating(tmp_path)
    assert decision == gate_policy.Decision.ALLOW


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
        "presence_forbidden",
        "presence_expected",
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
            id="read-mode-blocks-mutating-no-presence-written",
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
            # presence-upserting, so it ALLOWs exactly like implementation.
            "sess-rev",
            "BOUND_REVIEW",
            lambda ws: ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md",
            False,
            False,
            True,
            (),
            False,
            id="bound-review-allows-like-implementation",
        ),
        pytest.param(
            # FR-R4-04: no bind record, no env → IMPLEMENTATION; the write ALLOWs.
            # (session_id "unbound" has no record at all — session_mode=None.)
            "unbound",
            None,
            lambda ws: ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md",
            False,
            False,
            True,
            (),
            False,
            id="missing-mode-allows-write",
        ),
    ],
)
def test_read_mode_matrix(
    tmp_path: Path,
    session_id: str,
    session_mode: str | None,
    target_fn: Any,
    expect_block: bool,
    presence_forbidden: bool,
    presence_expected: bool,
    reason_checks: tuple[str, ...],
    reason_lower: bool,
) -> None:
    # FR-R4-03: READ-bound session's write outcome depends on path class. MUTATING →
    # BLOCK (non-acquiring, no presence record, --mode implementation hint). ADDITIVE →
    # ALLOW. PROTECTED stays fail-closed regardless of mode (second CRIT row for
    # PROTECTED — see test_allow_parity's protected_sessions_blocks row for the base
    # IMPLEMENTATION case). BOUND_REVIEW and missing-mode(unbound) both ALLOW exactly
    # like IMPLEMENTATION — only explicit READ (self-scoped) blocks MUTATING.
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
    presence_path = ws / ".dadaia" / "states" / "presence" / "B" / f"{session_id}.json"
    if presence_forbidden:
        # Non-acquiring: the gate must NOT have created a presence record.
        assert not presence_path.exists()
    if presence_expected:
        assert presence_path.exists()


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
        # harness pid is the pid stamped into the PRESENCE record (v0.1.76 — proving the
        # gate threads the LONG-LIVED pid, not its own ephemeral child pid). Uses a
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
        rec_path = ws / ".dadaia" / "states" / "presence" / "B" / "s-pid.json"
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        assert rec["pid"] == my_pid, rec


# --------------------------------------------------------------------------- #
# White-box: v0.1.76 FR4 — mode resolution is STRICTLY SELF-SCOPED. The former
# context-incumbent (rung 3) anti-downgrade matrix is DELETED (kills audit P1-1): a
# foreign session's bind/incumbent pointer/lease residue can NEVER change what THIS
# session's own mode resolves to. Every row below proves the incumbent pointer (and any
# lease-record residue) is now INERT to _resolve_mode.
# --------------------------------------------------------------------------- #


def _setup_self_record_wins_no_incumbent_needed(ws: Path) -> tuple[str, str]:
    # A record keyed to the harness sid resolves regardless of any incumbent pointer.
    impl_sid = "harness-impl"
    _write_session_record(ws, impl_sid, "BOUND_IMPLEMENTATION")
    return impl_sid, "BOUND_IMPLEMENTATION"


def _setup_foreign_incumbent_never_imposes_read(ws: Path) -> tuple[str, str]:
    # v0.1.76 FR4: a foreign session's READ bind sets the incumbent pointer, but a
    # DIFFERENT harness sid (no self record) must resolve its OWN default
    # (IMPLEMENTATION) — the incumbent rung is deleted, not merely overridden.
    bind_sid = "sess_bind01"
    _write_session_record(ws, bind_sid, "READ")
    session_identity.set_incumbent(ws, "a", bind_sid)
    return "harness-sid-xyz", "IMPLEMENTATION"


def _setup_foreign_incumbent_never_imposes_implementation(ws: Path) -> tuple[str, str]:
    # Symmetric: a foreign IMPLEMENTATION incumbent must not upgrade a DIFFERENT
    # session with no self record either — the default (IMPLEMENTATION) is reached
    # independently, not "inherited" from the incumbent.
    bind_sid = "sess_bind02"
    _write_session_record(ws, bind_sid, "BOUND_IMPLEMENTATION")
    session_identity.set_incumbent(ws, "a", bind_sid)
    return "harness-other-sid", "IMPLEMENTATION"


def _setup_dead_lease_residue_never_consulted(ws: Path) -> tuple[str, str]:
    # A dead lease-record residue (the old anti-downgrade NF-4 scenario) is now
    # completely inert to mode resolution: my own self record is all that matters.
    stale_hb = (datetime.now(tz=UTC) - timedelta(seconds=10_000)).isoformat()
    _write_lease_record(
        ws, "a", {"session_id": "old-impl", "heartbeat": stale_hb, "ttl": 120, "pid": 0}
    )
    my_sid = "harness-reviewer"
    _write_session_record(ws, my_sid, "READ")
    return my_sid, "READ"


def _setup_live_lease_residue_never_consulted(ws: Path) -> tuple[str, str]:
    # A TTL-fresh lease-record residue for a DIFFERENT session is also inert — mode
    # resolution never reads the lease record at all anymore.
    fresh_hb = datetime.now(tz=UTC).isoformat()
    _write_lease_record(
        ws, "a", {"session_id": "live-impl", "heartbeat": fresh_hb, "ttl": 120, "pid": 0}
    )
    return "harness-no-self-record", "IMPLEMENTATION"


@pytest.mark.parametrize(
    ("name", "setup_fn"),
    [
        ("self_record_wins_no_incumbent_needed", _setup_self_record_wins_no_incumbent_needed),
        ("foreign_incumbent_never_imposes_read", _setup_foreign_incumbent_never_imposes_read),
        (
            "foreign_incumbent_never_imposes_implementation",
            _setup_foreign_incumbent_never_imposes_implementation,
        ),
        ("dead_lease_residue_never_consulted", _setup_dead_lease_residue_never_consulted),
        ("live_lease_residue_never_consulted", _setup_live_lease_residue_never_consulted),
    ],
)
def test_resolve_mode_self_scoped_matrix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, setup_fn: Any
) -> None:
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    resolving_sid, expected_mode = setup_fn(ws)
    assert sdd_gate._resolve_mode(ws, resolving_sid, "a") == expected_mode


def test_resolve_mode_foreign_read_bind_end_to_end_never_blocks_my_write(tmp_path: Path) -> None:
    """End-to-end companion (successor to the deleted NF-4 anti-downgrade test): the SAME
    foreign-READ-incumbent setup, driven through the real hook subprocess, ALLOWS a
    MUTATING write from a DIFFERENT harness session — the doctrine's mode self-scope,
    proven at the hook boundary, not just in ``_resolve_mode`` isolation."""
    ws2 = _mk_workspace(tmp_path, "a")
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
    result2 = run_hook_subprocess("sdd_gate", {**payload2, "session_id": "harness-reviewer2"}, env2)
    assert result2.returncode == 0, result2.stderr
    assert result2.block_envelope() is None  # doctrine: never blocked by a foreign bind
