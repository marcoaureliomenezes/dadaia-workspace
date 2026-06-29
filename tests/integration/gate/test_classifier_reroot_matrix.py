"""T-010-03 / WS-R1 (AC-R1-01/02): full-pipeline gate matrix + lease-theft incident regression.

This suite drives the **whole gate decision pipeline** (``gate_policy.evaluate``, which
classifies then acquires/blocks the per-context lease) for in-repo paths across both the
default and a non-default slug. It proves three things the audit (CONF-1) demanded:

1. In-repo ADDITIVE writes take **no** lease (the lease record stays absent) — the
   lease-theft surface is closed (FR-R1-01).
2. The MEMORY phase rule and FROZEN block at ``gate_policy.py:90-93,137-143`` — previously
   dead for every real (in-repo) Spec Context — now execute for in-repo paths (FR-R1-02/03).
3. The lease-theft incident (2026-06-10): a foreign session's in-repo ``specs/bugs`` write
   while a holder lease is live and TTL-stale returns ALLOW **and leaves the lock record's
   holder untouched** (FR-R1-08, asserted on file content, not the return value).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

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
    ttl: int = lease.LEASE_TTL_SECONDS,
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


# (row_id, ctx_rel, phase, expected_decision, lease_must_stay_absent)
_PIPELINE_ROWS: tuple[tuple[str, str, str, Decision, bool], ...] = (
    # ADDITIVE in-repo — ALLOW, and (the incident surface) no lease is ever written.
    ("additive_bugs_no_lease", "specs/bugs/x.md", "SPEC", Decision.ALLOW, True),
    ("additive_audits_no_lease", "specs/audits/d/a.md", "SPEC", Decision.ALLOW, True),
    ("additive_backlog_no_lease", "specs/backlog/x.md", "SPEC", Decision.ALLOW, True),
    ("frozen_bugs_archive", "specs/bugs/_archive/x.md", "SPEC", Decision.BLOCK, True),
    ("frozen_audits_archive", "specs/audits/_archive/x.md", "SPEC", Decision.BLOCK, True),
    ("frozen_backlog_archive", "specs/backlog/_archive/x.md", "SPEC", Decision.BLOCK, True),
    # MEMORY in-repo — the phase rule (dead :137-143) is now live.
    ("memory_block_outside_phase", "specs/memory/a.md", "SPEC", Decision.BLOCK, True),
    ("memory_allow_definition", "specs/memory/a.md", "DEFINITION", Decision.ALLOW, True),
    ("memory_allow_closure", "specs/memory/a.md", "CLOSURE", Decision.ALLOW, True),
    # FROZEN in-repo — the archive block (dead :90-93 classify + :134-135 decision) is live.
    ("frozen_block", "specs/_archive/v0.1.9/SPEC.md", "SPEC", Decision.BLOCK, True),
    # MUTATING in-repo — acquires the lease (free lease ⇒ ALLOW); record is written.
    ("mutating_release_acquires", "specs/releases/v0.1.10/SPEC.md", "SPEC", Decision.ALLOW, False),
    ("mutating_source_acquires", "dadaia_workspace/x.py", "SPEC", Decision.ALLOW, False),
)


@pytest.mark.parametrize("slug", [_DEFAULT_SLUG, _NONDEFAULT_SLUG], ids=["default", "nondefault"])
@pytest.mark.parametrize("row", _PIPELINE_ROWS, ids=[r[0] for r in _PIPELINE_ROWS])
def test_full_pipeline_in_repo_matrix(
    row: tuple[str, str, str, Decision, bool], slug: str, tmp_path: Path
) -> None:
    row_id, ctx_rel, phase, expected, lease_absent = row
    rel_path = f"repos/{slug}/{ctx_rel}"
    decision, message = _evaluate(tmp_path, slug, rel_path, phase=phase)

    assert decision == expected, f"{row_id} slug={slug}"
    if decision == Decision.BLOCK:
        assert message, f"{row_id}: BLOCK must carry an actionable message"

    record_present = lease._record_path(tmp_path, slug).exists()
    if lease_absent:
        assert not record_present, (
            f"{row_id}: a non-MUTATING in-repo write must take NO lease (lease-theft guard)"
        )
    else:
        assert record_present, f"{row_id}: MUTATING in-repo write must acquire the lease"


def test_in_repo_memory_phase_rule_branch_is_live(tmp_path: Path) -> None:
    """gate_policy.py:137-143 (RULE A) executes for in-repo memory — was dead pre-WS-R1."""
    slug = _DEFAULT_SLUG
    block, msg = _evaluate(tmp_path, slug, f"repos/{slug}/specs/memory/a.md", phase="PLAN")
    assert block == Decision.BLOCK
    assert "RULE A" in msg and "DEFINITION or CLOSURE" in msg


def test_in_repo_frozen_block_branch_is_live(tmp_path: Path) -> None:
    """gate_policy.py:134-135 (RULE B) executes for in-repo _archive — was dead pre-WS-R1."""
    slug = _NONDEFAULT_SLUG
    block, msg = _evaluate(tmp_path, slug, f"repos/{slug}/specs/_archive/x.md")
    assert block == Decision.BLOCK
    assert "RULE B" in msg and "frozen" in msg


def test_per_class_archive_prefixes_are_frozen_before_additive(tmp_path: Path) -> None:
    """Per-class archives sit under additive dirs but must classify FROZEN first."""
    slug = _DEFAULT_SLUG
    for ctx_rel in (
        "specs/backlog/_archive/item.md",
        "specs/bugs/_archive/bug.md",
        "specs/audits/_archive/audit.md",
    ):
        block, msg = _evaluate(tmp_path, slug, f"repos/{slug}/{ctx_rel}")
        assert block == Decision.BLOCK
        assert "RULE B" in msg


# ---------------------------------------------------------------------------
# AC-R1-02 — Full-pipeline lease-theft incident regression (FR-R1-08).
# Bug: lease-stolen-from-live-session-during-long-bash. Closed later by T-010-12.
# ---------------------------------------------------------------------------


def test_lease_theft_incident_in_repo_additive_does_not_steal(tmp_path: Path) -> None:
    """The 2026-06-10 incident, reproduced as a regression.

    Session A holds the lease on context ``dadaia-workspace``. The clock advances 130 s
    (> 120 s TTL) with no Write/Edit from A (A is inside a long Bash/pytest call, the exact
    starvation in the incident). Session B then does an **in-repo** ``specs/bugs`` write —
    the very write the constitution promises is ADDITIVE and lock-free. Pre-WS-R1 this
    classified MUTATING (because ``repos/`` won first) and B's evaluate auto-TAKEOVER'd A's
    TTL-stale lease — stealing it mid-CLOSURE. Post-re-root it classifies ADDITIVE: B is
    ALLOWed with **no lease interaction at all**, and the lock record still names A.
    """
    slug = "dadaia-workspace"
    holder = "session-A-holder"
    foreign = "session-B-foreign"

    # Session A acquires the lease (in-repo MUTATING write at T0).
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


def test_lease_theft_dual_session_foreign_mutating_still_blocks_live_holder(
    tmp_path: Path,
) -> None:
    """Counterpart guard: a foreign *MUTATING* write does NOT silently steal a live holder.

    With WS-R1, B's in-repo MUTATING write classifies MUTATING and goes through the lease.
    Within TTL (holder still live by write-recency), the foreign session is BLOCKed with the
    no-rebind yield message — it does not take over. (TTL-stale + dead-pid TAKEOVER is the
    province of WS-R2 / T-010-05; here the holder is fresh.)
    """
    slug = "dadaia-workspace"
    holder = "session-A-holder"
    _seed_lease(tmp_path, slug, holder, BASE)  # fresh heartbeat, live by recency

    decision, message = evaluate(
        tmp_path,
        f"repos/{slug}/specs/releases/v0.1.10/SPEC.md",
        ctx=slug,
        phase="SPEC",
        session_id="session-B-foreign",
        release="v0.1.10",
        mode="IMPLEMENTATION",
        clock=fixed(BASE + timedelta(seconds=30)),
    )
    assert decision == Decision.BLOCK
    record = lease.read_record(tmp_path, slug)
    assert record is not None and record["session_id"] == holder
    for forbidden in ("bind --mode write", "relaunch", "lock steal"):
        assert forbidden not in message
