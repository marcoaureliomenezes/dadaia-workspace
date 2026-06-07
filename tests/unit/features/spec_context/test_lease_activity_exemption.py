"""T-016-02: 16-cell activity-class exemption matrix (SPEC §8 AC-05).

4 path classes (MUTATING, ADDITIVE, MEMORY, FROZEN) × 4 lease states
(absent, live-mine, live-other, expired). Plus the two named RULE A exemption
tests (FR-P1-13). All timing uses FakeClock; phase fixed to SPEC for the matrix
so MEMORY rows block (the ALLOW phases are covered by the named tests).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.features.spec_context.gate_policy import Decision, evaluate
from dadaia_workspace.features.spec_context.lease import LEASE_TTL_SECONDS

BASE = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
CTX = "myctx"

_PATHS = {
    "mutating": "specs/releases/v0.2.0/SPEC.md",
    "additive": "specs/backlog/x.md",
    "memory": "specs/memory/x.md",
    "frozen": "specs/_archive/x.md",
}


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def _seed(workspace: Path, session_id: str, heartbeat: datetime, ttl: int = LEASE_TTL_SECONDS) -> None:
    lease._record_path(workspace, CTX).write_text(
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


def _apply_state(workspace: Path, state: str) -> None:
    if state == "absent":
        return
    if state == "live_mine":
        _seed(workspace, "mine", BASE)
    elif state == "live_other":
        _seed(workspace, "other", BASE)
    elif state == "expired":
        _seed(workspace, "other", BASE - timedelta(seconds=LEASE_TTL_SECONDS + 60))


# 16 cells: (path_class, lease_state) -> expected. Phase=SPEC throughout.
# With D1 stable-identity: live_other → BLOCK (yield-iff-live-foreign, FR-P1-15).
# No .ptr file is seeded, so session "mine" sees a live foreign lease and blocks.
_EXPECTED = {
    ("mutating", "absent"): Decision.ALLOW,
    ("mutating", "live_mine"): Decision.ALLOW,
    # Foreign live lease → yield-iff-live-foreign BLOCK (D1 soul-fold, FR-P1-15).
    ("mutating", "live_other"): Decision.BLOCK,
    ("mutating", "expired"): Decision.ALLOW,
    ("additive", "absent"): Decision.ALLOW,
    ("additive", "live_mine"): Decision.ALLOW,
    ("additive", "live_other"): Decision.ALLOW,
    ("additive", "expired"): Decision.ALLOW,
    ("memory", "absent"): Decision.BLOCK,
    ("memory", "live_mine"): Decision.BLOCK,
    ("memory", "live_other"): Decision.BLOCK,
    ("memory", "expired"): Decision.BLOCK,
    ("frozen", "absent"): Decision.BLOCK,
    ("frozen", "live_mine"): Decision.BLOCK,
    ("frozen", "live_other"): Decision.BLOCK,
    ("frozen", "expired"): Decision.BLOCK,
}


@pytest.mark.parametrize(
    ("path_class", "lease_state"),
    list(_EXPECTED.keys()),
    ids=[f"{c}_{s}_{_EXPECTED[(c, s)].value}" for (c, s) in _EXPECTED],
)
def test_exemption_matrix(path_class: str, lease_state: str, tmp_path: Path) -> None:
    _apply_state(tmp_path, lease_state)
    decision, _msg = evaluate(
        tmp_path,
        _PATHS[path_class],
        ctx=CTX,
        phase="SPEC",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == _EXPECTED[(path_class, lease_state)]


def test_memory_definition_allow(tmp_path: Path) -> None:
    decision, _msg = evaluate(
        tmp_path,
        _PATHS["memory"],
        ctx=CTX,
        phase="DEFINITION",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.ALLOW


def test_memory_closure_allow(tmp_path: Path) -> None:
    decision, _msg = evaluate(
        tmp_path,
        _PATHS["memory"],
        ctx=CTX,
        phase="CLOSURE",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.ALLOW


def test_audits_path_additive_allow(tmp_path: Path) -> None:
    """T-016-13 AC-14: specs/audits/** is classified ADDITIVE — always ALLOW (D2 soul-fold).

    Audit dirs use collision-safe naming: specs/audits/<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/
    The gate never requires a lease check for audit writes.
    """
    decision, _msg = evaluate(
        tmp_path,
        "specs/audits/2026-01-01T000000Z-abc12345/audit.md",
        ctx=CTX,
        phase="SPEC",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.ALLOW
