"""T-010-03 / WS-R1 (AC-R1-02 / FR-R1-08): lease-theft incident — hook-subprocess regression.

This is the incident reproduced at the **real hook boundary**: the ``sdd_gate`` hook invoked
as a subprocess exactly the way a harness spawns it, via ``run_hook_subprocess`` +
``claude_hook_env()`` (no hand-planted ``DADAIA_SESSION_ID`` — the simulated-env blind spot
the v0.1.10 harness-env fixture exists to kill). A companion in-process pipeline test lives in
``test_classifier_reroot_matrix.py``; this one closes the loop end-to-end through stdin,
``resolve_session_id``, classification, and the lease.

Scenario (the 2026-06-10 production theft): holder session A owns the lease; the clock is
advanced past TTL with no Write/Edit from A; foreign session B performs an **in-repo**
``specs/bugs`` write. Post-re-root that write is ADDITIVE → ALLOW with the lock record's
holder unchanged. The clock is injected by seeding the holder's heartbeat in the past, so no
wall-clock sleep is needed (slop-test discipline: no ``time.sleep``).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = pytest.mark.integration

_SLUG = "dadaia-workspace"


def _now() -> datetime:
    """Real wall-clock anchor — the hook subprocess uses ``datetime.now``, not an injected clock.

    Staleness in the hook is judged against real now, so the holder heartbeat must be seeded
    relative to it: in the past for the stale (theft-precondition) case, recent for the fresh
    case. No ``time.sleep`` is used — the clock is injected purely via the seeded heartbeat.
    """
    return datetime.now(tz=UTC)


def _make_workspace(tmp_path: Path) -> Path:
    rel = tmp_path / "repos" / _SLUG / "specs" / "releases"
    rel.mkdir(parents=True)
    (rel / "ACTIVE.md").write_text("release: v0.1.10\nphase: SPEC\n", encoding="utf-8")
    (tmp_path / "repos" / _SLUG / "specs" / "bugs").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    return tmp_path


def _seed_holder_lease(tmp_path: Path, holder: str, heartbeat: datetime) -> None:
    """Seed A's lease record with a heartbeat in the past (the injected clock)."""
    lease._record_path(tmp_path, _SLUG).write_text(
        json.dumps(
            {
                "context": _SLUG,
                "release": "v0.1.10",
                "session_id": holder,
                "mode": "IMPLEMENTATION",
                "acquired_at": heartbeat.isoformat(),
                "heartbeat": heartbeat.isoformat(),
                "ttl": lease.LEASE_TTL_SECONDS,
            }
        ),
        encoding="utf-8",
    )


def test_incident_foreign_in_repo_bug_write_allows_and_holder_unchanged(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    holder = "session-A-holder"
    foreign = "session-B-foreign"

    # Holder A's lease is TTL-stale (heartbeat 130 s in the past) — A is starving inside a
    # long Bash/pytest call, the incident precondition. Clock injected via the past heartbeat.
    _seed_holder_lease(ws, holder, _now() - timedelta(seconds=130))
    record_before = lease.read_record(ws, _SLUG)
    assert record_before is not None and record_before["session_id"] == holder

    # Foreign session B writes an in-repo bug file through the REAL hook subprocess, with the
    # harness-native session id (CLAUDE_CODE_SESSION_ID) — never DADAIA_SESSION_ID.
    target = ws / "repos" / _SLUG / "specs" / "bugs" / "lease-stolen-incident.md"
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
        "session_id": foreign,
    }
    result = run_hook_subprocess("sdd_gate", payload, claude_hook_env(ws, session_id=foreign))

    # ADDITIVE ⇒ ALLOW (no block envelope on stdout).
    assert result.returncode == 0
    assert result.block_envelope() is None, (
        "in-repo specs/bugs write must be ADDITIVE → ALLOW; a block means the re-root regressed"
    )

    # THE INVARIANT — asserted on the lock-record file, not the hook's exit/stdout:
    record_after = lease.read_record(ws, _SLUG)
    assert record_after is not None
    assert record_after["session_id"] == holder, (
        "lease-theft regression: the foreign in-repo ADDITIVE write must NOT change the lock "
        "holder; B's session id must never appear in the lock record"
    )
    assert record_after["acquired_at"] == record_before["acquired_at"], (
        "the holder's lease record must be untouched by the foreign ADDITIVE write"
    )


def test_incident_foreign_mutating_does_not_steal_within_ttl(tmp_path: Path) -> None:
    """Counterpart at the hook boundary: a fresh holder is not stolen by a foreign MUTATING write."""
    ws = _make_workspace(tmp_path)
    holder = "session-A-holder"
    foreign = "session-B-foreign"
    _seed_holder_lease(ws, holder, _now())  # fresh — live by recency

    target = ws / "repos" / _SLUG / "specs" / "releases" / "v0.1.10" / "SPEC.md"
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
        "session_id": foreign,
    }
    result = run_hook_subprocess("sdd_gate", payload, claude_hook_env(ws, session_id=foreign))

    assert result.returncode == 0
    envelope = result.block_envelope()
    assert envelope is not None, "a foreign MUTATING write must BLOCK against a live holder"
    record = lease.read_record(ws, _SLUG)
    assert record is not None and record["session_id"] == holder
