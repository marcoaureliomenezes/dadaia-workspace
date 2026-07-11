"""T-010-03 / WS-R1 (AC-R1-01/02): full-pipeline gate matrix + lease-theft incident regression.

Where ``tests/unit/features/spec_context/test_gate_policy.py`` asserts *classification* in
isolation, this suite drives the **whole gate decision pipeline** (``gate_policy.evaluate``)
for in-repo paths across both the default and a non-default slug. It proves three things the
audit (CONF-1) demanded:

1. In-repo ADDITIVE writes take **no** presence record (never touch the concurrency-signal
   surface) — the lease-theft-shaped surface stays closed (FR-R1-01 successor).
2. The MEMORY phase rule and FROZEN block at ``gate_policy.py:90-93,137-143`` — previously
   dead for every real (in-repo) Spec Context — now execute for in-repo paths (FR-R1-02/03).
3. v0.1.76 NO-LOCKS DOCTRINE: the 2026-06-10 lease-theft incident's PRECONDITION (a live
   foreign holder) can no longer even produce a BLOCK — every in-repo MUTATING write ALLOWs
   regardless of any lease-record residue, since ``gate_policy.evaluate`` no longer reads
   ``ctx_locks/`` at all (FR-R1-08 successor).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.features.spec_context.gate_policy import Decision, evaluate

BASE = datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC)
_DEFAULT_SLUG = "dadaia-workspace"
_NONDEFAULT_SLUG = "rand-engine"


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def _seed_lease(
    workspace: Path,
    ctx: str,
    session_id: str,
    heartbeat: datetime,
    ttl: int = kernel_tunables.LEASE_TTL_SECONDS,
) -> None:
    lease._record_path(workspace, ctx).write_text(
        json.dumps(
            {
                "context": ctx,
                "release": "v0.1.10",
                "session_id": session_id,
                "mode": "IMPLEMENTATION",
                "acquired_at": heartbeat.isoformat(),
                "heartbeat": heartbeat.isoformat(),
                "ttl": ttl,
            }
        ),
        encoding="utf-8",
    )


def _evaluate(
    workspace: Path, ctx: str, rel_path: str, *, phase: str = "SPEC", session_id: str = "sess"
) -> tuple[Decision, str]:
    return evaluate(
        workspace,
        rel_path,
        ctx=ctx,
        phase=phase,
        session_id=session_id,
        release="v0.1.10",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )


# (row_id, ctx_rel, phase, expected_decision, presence_must_stay_absent, message_contains)
_PIPELINE_ROWS: tuple[tuple[str, str, str, Decision, bool, tuple[str, ...]], ...] = (
    # ADDITIVE in-repo — ALLOW, and (the incident surface) no presence record is written.
    ("additive_bugs_no_lease", "specs/bugs/x.md", "SPEC", Decision.ALLOW, True, ()),
    ("additive_audits_no_lease", "specs/audits/d/a.md", "SPEC", Decision.ALLOW, True, ()),
    ("additive_backlog_no_lease", "specs/backlog/x.md", "SPEC", Decision.ALLOW, True, ()),
    # MEMORY in-repo — the phase rule (dead :137-143 pre-WS-R1) is now live (RULE A).
    (
        "memory_block_outside_phase",
        "specs/memory/a.md",
        "SPEC",
        Decision.BLOCK,
        True,
        ("RULE A", "DEFINITION or CLOSURE"),
    ),
    ("memory_allow_definition", "specs/memory/a.md", "DEFINITION", Decision.ALLOW, True, ()),
    ("memory_allow_closure", "specs/memory/a.md", "CLOSURE", Decision.ALLOW, True, ()),
    # FROZEN in-repo — the archive block (dead :90-93 classify + :134-135 decision pre-WS-R1)
    # is now live (RULE B).
    (
        "frozen_block",
        "specs/_archive/v0.1.9/SPEC.md",
        "SPEC",
        Decision.BLOCK,
        True,
        ("RULE B", "frozen"),
    ),
    # MUTATING in-repo — ALLOWs (v0.1.76 doctrine) and upserts an advisory presence record.
    (
        "mutating_release_acquires",
        "specs/releases/v0.1.10/SPEC.md",
        "SPEC",
        Decision.ALLOW,
        False,
        (),
    ),
    ("mutating_source_acquires", "dadaia_workspace/x.py", "SPEC", Decision.ALLOW, False, ()),
)


@pytest.mark.parametrize("slug", [_DEFAULT_SLUG, _NONDEFAULT_SLUG], ids=["default", "nondefault"])
@pytest.mark.parametrize("row", _PIPELINE_ROWS, ids=[r[0] for r in _PIPELINE_ROWS])
def test_full_pipeline_in_repo_matrix(
    row: tuple[str, str, str, Decision, bool, tuple[str, ...]], slug: str, tmp_path: Path
) -> None:
    row_id, ctx_rel, phase, expected, presence_absent, message_contains = row
    rel_path = f"repos/{slug}/{ctx_rel}"
    decision, message = _evaluate(tmp_path, slug, rel_path, phase=phase)

    assert decision == expected, f"{row_id} slug={slug}"
    if decision == Decision.BLOCK:
        assert message, f"{row_id}: BLOCK must carry an actionable message"
    for fragment in message_contains:
        assert fragment in message, f"{row_id}: expected {fragment!r} in message {message!r}"

    presence_path = tmp_path / ".dadaia" / "states" / "presence" / slug / "sess.json"
    if presence_absent:
        assert not presence_path.exists(), (
            f"{row_id}: a non-MUTATING in-repo write must touch NO presence record "
            "(lease-theft-shaped surface guard)"
        )
    else:
        assert presence_path.exists(), (
            f"{row_id}: MUTATING in-repo write must upsert an advisory presence record"
        )


# ---------------------------------------------------------------------------
# AC-R1-02 — Full-pipeline lease-theft incident regression (FR-R1-08).
# Bug: lease-stolen-from-live-session-during-long-bash. Closed later by T-010-12.
# ---------------------------------------------------------------------------


def test_lease_theft_incident_two_phase_additive_free_mutating_allows(tmp_path: Path) -> None:
    """The 2026-06-10 incident, reproduced as a regression, in two phases.

    Phase 1 (ADDITIVE never steals): Session A holds a (now-inert) lease-record residue
    on context ``dadaia-workspace``. The clock advances 130 s (> 120 s TTL) with no
    Write/Edit from A (A is inside a long Bash/pytest call, the exact starvation in the
    incident). Session B then does an **in-repo** ``specs/bugs`` write — the very write
    the constitution promises is ADDITIVE and lock-free. Pre-WS-R1 this classified
    MUTATING (because ``repos/`` won first) and B's evaluate auto-TAKEOVER'd A's
    TTL-stale lease — stealing it mid-CLOSURE. Post-re-root it classifies ADDITIVE: B is
    ALLOWed with **no lease interaction at all**, and the lock record still names A.

    Phase 2 (v0.1.76 NO-LOCKS DOCTRINE successor): a foreign *MUTATING* write against a
    context with a live holder lease-record residue no longer BLOCKs at all — the
    lease-theft incident's precondition (a live foreign holder) is now doctrinally
    IRRELEVANT to the gate's verdict, since ``gate_policy.evaluate`` never reads
    ``ctx_locks/``. The write ALLOWs and the (inert) lease record stays byte-for-byte
    untouched.
    """
    slug = "dadaia-workspace"
    holder = "session-A-holder"
    foreign = "session-B-foreign"

    # Phase 1 — Session A's in-repo MUTATING write ALLOWs (v0.1.76: evaluate() no
    # longer acquires a lease itself). A pre-existing lease-record residue is seeded
    # directly to reproduce the incident's exact topology (a live-looking holder record
    # on disk, e.g. a leftover from a prior release's lease machinery).
    a_decision, _ = evaluate(
        tmp_path,
        f"repos/{slug}/specs/releases/v0.1.10/TASKS.md",
        ctx=slug,
        phase="SPEC",
        session_id=holder,
        release="v0.1.10",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert a_decision == Decision.ALLOW
    _seed_lease(tmp_path, slug, holder, BASE)
    record_before = lease.read_record(tmp_path, slug)
    assert record_before is not None and record_before["session_id"] == holder

    # 130 s pass with NO heartbeat from A (A starves inside a long Bash call). The lease is
    # now TTL-stale by write-recency — the precondition that triggered the theft.
    later = BASE + timedelta(seconds=130)

    # Session B writes an in-repo bug file — ADDITIVE, must take/steal NOTHING.
    b_decision, b_msg = evaluate(
        tmp_path,
        f"repos/{slug}/specs/bugs/lease-stolen-incident.md",
        ctx=slug,
        phase="SPEC",
        session_id=foreign,
        release="v0.1.10",
        mode="IMPLEMENTATION",
        clock=fixed(later),
    )

    assert b_decision == Decision.ALLOW, "in-repo ADDITIVE write must always flow"
    assert b_msg == "", "ADDITIVE ALLOW carries no message"

    # THE INVARIANT (asserted on file content, not return value): the holder is unchanged.
    record_after = lease.read_record(tmp_path, slug)
    assert record_after is not None
    assert record_after["session_id"] == holder, (
        "lease-theft regression: a foreign in-repo ADDITIVE write must NOT change the lock "
        "holder — the foreign session's id must never appear in the lock record"
    )
    assert record_after["acquired_at"] == record_before["acquired_at"], (
        "the holder's lease record must be byte-for-byte untouched by the foreign write"
    )

    # Phase 2 — v0.1.76: a fresh live holder's lease-record residue is doctrinally inert;
    # a foreign MUTATING write ALLOWs (never BLOCKs) and the residue stays untouched.
    slug2 = "dadaia-workspace-phase2"
    _seed_lease(tmp_path, slug2, holder, BASE)  # fresh heartbeat, live by recency

    decision, message = evaluate(
        tmp_path,
        f"repos/{slug2}/specs/releases/v0.1.10/SPEC.md",
        ctx=slug2,
        phase="SPEC",
        session_id="session-B-foreign",
        release="v0.1.10",
        mode="IMPLEMENTATION",
        clock=fixed(BASE + timedelta(seconds=30)),
    )
    assert decision == Decision.ALLOW
    record = lease.read_record(tmp_path, slug2)
    assert record is not None and record["session_id"] == holder, (
        "the inert lease-record residue must stay byte-for-byte untouched by the ALLOWed "
        "foreign write — evaluate() never reads or writes ctx_locks/"
    )
    for forbidden in ("bind --mode write", "relaunch", "lock steal"):
        assert forbidden not in message
