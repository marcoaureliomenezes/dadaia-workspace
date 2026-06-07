"""T-016-02 + T-016-14: fail-safe property table (SPEC §8 AC-04).

Every row's decision is one of {ALLOW, BLOCK}; every BLOCK carries an actionable
message; no row raises an unhandled exception. D1 soul-fold: a MUTATING live-other
conflict BLOCKS with yield-iff-live-foreign (FR-P1-15) when no .ptr match; a
relaunched session with .ptr match RENEWs (ALLOW). All timing uses FakeClock.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.features.spec_context.gate_policy import Decision, evaluate

BASE = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
CTX = "myctx"


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def _seed(workspace: Path, session_id: str, heartbeat: datetime, ttl: int = 1800) -> None:
    path = lease._record_path(workspace, CTX)
    path.write_text(
        json.dumps(
            {
                "context": CTX,
                "release": "v0.2.0",
                "session_id": session_id,
                "mode": "IMPLEMENTATION",
                "acquired_at": heartbeat.isoformat(),
                "heartbeat": heartbeat.isoformat(),
                "ttl": ttl,
            }
        ),
        encoding="utf-8",
    )


# (row_id, rel_path, phase, seed_fn, expected_decision)
# seed_fn(workspace) sets up the lease state, or None for absent.
_ROWS = [
    ("1_absent_mutating", "specs/releases/v0.2.0/SPEC.md", "SPEC", None, Decision.ALLOW),
    (
        "2_stale_mutating",
        "specs/releases/v0.2.0/SPEC.md",
        "SPEC",
        lambda ws: _seed(ws, "other", BASE - timedelta(seconds=4000)),
        Decision.ALLOW,
    ),
    (
        "3_live_mine_mutating",
        "specs/releases/v0.2.0/SPEC.md",
        "SPEC",
        lambda ws: _seed(ws, "mine", BASE),
        Decision.ALLOW,
    ),
    (
        # D1 soul-fold: foreign live lease → yield-iff-live-foreign BLOCK (FR-P1-15).
        # No .ptr file → session "mine" sees live foreign "other" and is blocked.
        "4_live_other_mutating",
        "specs/releases/v0.2.0/SPEC.md",
        "SPEC",
        lambda ws: _seed(ws, "other", BASE),
        Decision.BLOCK,
    ),
    ("5_absent_additive", "specs/backlog/x.md", "SPEC", None, Decision.ALLOW),
    (
        "6_live_other_additive",
        "specs/backlog/x.md",
        "SPEC",
        lambda ws: _seed(ws, "other", BASE),
        Decision.ALLOW,
    ),
    ("7_any_frozen", "specs/_archive/x.md", "SPEC", None, Decision.BLOCK),
    ("8_memory_non_write_phase", "specs/memory/x.md", "SPEC", None, Decision.BLOCK),
    ("9_memory_definition", "specs/memory/x.md", "DEFINITION", None, Decision.ALLOW),
]


@pytest.mark.parametrize("row", _ROWS, ids=[r[0] for r in _ROWS])
def test_fail_safe_property(row: tuple, tmp_path: Path) -> None:  # type: ignore[type-arg]
    row_id, rel_path, phase, seed_fn, expected = row
    if seed_fn is not None:
        seed_fn(tmp_path)

    decision, message = evaluate(
        tmp_path,
        rel_path,
        ctx=CTX,
        phase=phase,
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )

    # Property: output is one of the two actionable decisions.
    assert decision in (Decision.ALLOW, Decision.BLOCK)
    assert decision == expected, f"row {row_id}: expected {expected}, got {decision}"

    if decision == Decision.BLOCK:
        assert message, f"row {row_id}: BLOCK must carry an actionable message"

    # D1 soul-fold: a MUTATING live-other conflict BLOCKS with yield-iff-live-foreign
    # message (FR-P1-15). The message is informative and actionable, and per the operator
    # forbidden-law contains NO manual unblock ceremony — neither "bind --mode write",
    # "relaunch", nor "lock steal" — because reclaim-iff-stale frees a dead holder by itself.
    if row_id == "4_live_other_mutating":
        assert decision == Decision.BLOCK
        assert message, "yield-iff-live-foreign BLOCK must carry an actionable message"
        for forbidden in ("bind --mode write", "relaunch", "lock steal"):
            assert forbidden not in message, f"forbidden-law: BLOCK message must not contain {forbidden!r}"


# ---------------------------------------------------------------------------
# T-016-14: soul-fold property rows (D1) — stable-identity renewal + yield block
# ---------------------------------------------------------------------------


def test_mutating_stable_identity_match_live_foreign_renews(tmp_path: Path) -> None:
    """D1 soul-fold row: MUTATING + stable-identity-match + live-foreign-lock → RENEW (ALLOW).

    When a .ptr file matches the caller's session_id, acquire() RENEWs regardless
    of whether the lock record shows a different (foreign-looking) session_id. This
    is the relaunched-session scenario: the session is recognised as the incumbent.
    """
    # Seed lock record with "foreign-looking" session_id (simulating a relaunch that
    # caused the session env var to diverge from the record).
    _seed(tmp_path, "old-session-id", BASE)
    # Write .ptr for "mine" — signals that "mine" is the incumbent for this context.
    ptr = lease._ptr_path(tmp_path, CTX)
    ptr.write_text("mine", encoding="utf-8")

    decision, _msg = evaluate(
        tmp_path,
        "specs/releases/v0.2.0/SPEC.md",
        ctx=CTX,
        phase="SPEC",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.ALLOW, (
        "Stable-identity match (.ptr == session_id) must RENEW even when lock record "
        "shows a foreign-looking session_id (D1 soul-fold, FR-P1-15)"
    )


def test_mutating_no_ptr_match_live_foreign_yields(tmp_path: Path) -> None:
    """D1 soul-fold row: MUTATING + no-ptr-match + live-foreign-lock → yield BLOCK (ALLOW escape).

    When no .ptr matches and the lock record has a live foreign session_id,
    acquire() raises LockHeldError with yield-iff-live-foreign message. The block
    is always escapable (via additive writes; steal only as conditional emergency).
    """
    # Seed a live foreign lock record with no .ptr for "mine".
    _seed(tmp_path, "genuinely-other-session", BASE)

    decision, message = evaluate(
        tmp_path,
        "specs/releases/v0.2.0/SPEC.md",
        ctx=CTX,
        phase="SPEC",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.BLOCK, (
        "No-.ptr-match + live-foreign lease must BLOCK with yield message (D1, FR-P1-15)"
    )
    assert message, "Yield block must carry an informative, actionable message"
    assert "bind --mode write" not in message, "Yield message must never instruct to bind --mode write"
    assert "relaunch" not in message, "Yield message must never instruct to relaunch"
