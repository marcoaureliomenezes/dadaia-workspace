"""T-016-02: 9-row fail-safe property table (SPEC §8 AC-04).

Every row's decision is one of {ALLOW, BLOCK}; every BLOCK carries an actionable
message; every MUTATING live-conflict BLOCK contains ``dadaia lock steal``; no row
raises an unhandled exception. All timing uses FakeClock.
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

    # MUTATING live-other must always print the steal unblock path.
    if row_id == "4_live_other_mutating":
        assert "dadaia lock steal" in message
