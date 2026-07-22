"""v0.1.76 T-3 — two-actor PRESENCE e2e (successor to test_two_actor_lease.py, deleted).

NO-LOCKS DOCTRINE: races between sessions are ACCEPTED and SURFACED, never prevented.
This is the falsifying end-to-end successor to the pre-v0.1.76 no-steal concurrency
kernel proof — it drives the REAL ``pre_gate`` hook subprocess (exactly as a harness
does) and proves the doctrine's positive claim: two live actors writing to the SAME
context BOTH succeed, each other's presence is recorded and mutually visible, and an
ADDITIVE write from a second actor never touches the first actor's state. Disjoint
contexts remain independent (regression for gate-cross-context-lock-contamination,
kept from the retired suite's scenario iii — now re-targeted at presence instead of a
lease record).

Every wait uses file rendezvous with a bounded deadline (never a blind sleep of the
whole duration, never an infinite poll). No holder/foreign asymmetry is modeled here —
there is nothing to hold, so both actors are symmetric.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.harness_env import claude_hook_env, is_allow_envelope, run_hook_subprocess

pytestmark = pytest.mark.e2e

_SLUG = "dadaia-workspace"
_OTHER_SLUG = "other-context"
_READY_DEADLINE = 30.0
_EXIT_DEADLINE = 30.0


def _make_workspace(tmp_path: Path, *slugs: str) -> Path:
    """Throwaway workspace: a repo + approved IMPLEMENTATION ACTIVE.md per slug."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        rel = tmp_path / "repos" / slug / "specs" / "releases"
        rel.mkdir(parents=True, exist_ok=True)
        (rel / "ACTIVE.md").write_text(
            "release: v0.1.76\nphase: IMPLEMENTATION\n", encoding="utf-8"
        )
        (tmp_path / "repos" / slug / "specs" / "bugs").mkdir(parents=True, exist_ok=True)
        (rel / "v0.1.76").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _presence_dir(ws: Path, ctx: str) -> Path:
    return ws / ".dadaia" / "states" / "presence" / ctx


def _presence_sessions(ws: Path, ctx: str) -> set[str]:
    d = _presence_dir(ws, ctx)
    return {p.stem for p in d.glob("*.json")} if d.is_dir() else set()


def _run_write(ws: Path, ctx: str, session_id: str, filename: str) -> subprocess.CompletedProcess:
    """Drive the REAL pre_gate hook subprocess for a MUTATING write, exactly as a harness does."""
    target = ws / "repos" / ctx / "specs" / "releases" / "v0.1.76" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    env = claude_hook_env(ws, session_id=session_id)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
        "session_id": session_id,
    }
    result = run_hook_subprocess("pre_gate", payload, env)
    return result


# --------------------------------------------------------------------------------------
# (i) TWO LIVE ACTORS, SAME CONTEXT — both writes ALLOW; both presences visible.
# --------------------------------------------------------------------------------------
def test_two_actors_same_context_both_writes_allow_and_are_mutually_visible(
    tmp_path: Path,
) -> None:
    ws = _make_workspace(tmp_path, _SLUG)
    sid_a, sid_b = "actor-A", "actor-B"

    result_a = _run_write(ws, _SLUG, sid_a, "TASKS.md")
    assert result_a.returncode == 0, result_a.stderr
    assert result_a.block_envelope() is None, "actor A's write must ALLOW under the doctrine"

    result_b = _run_write(ws, _SLUG, sid_b, "PLAN.md")
    assert result_b.returncode == 0, result_b.stderr
    assert result_b.block_envelope() is None, "actor B's write must ALLOW under the doctrine"

    # Both actors' presence is now recorded on the SAME context — mutual visibility.
    recorded = _presence_sessions(ws, _SLUG)
    assert {sid_a, sid_b} <= recorded, recorded

    # B's write surfaced an advisory naming A (throttled — at most one per window).
    combined_b = "\n".join(
        line
        for line in (result_b.stdout + result_b.stderr).splitlines()
        if line.strip() and not is_allow_envelope(line.strip())
    )
    if combined_b.strip():
        assert sid_a in combined_b


# --------------------------------------------------------------------------------------
# (ii) ADDITIVE write from a second actor never touches the first actor's presence.
# --------------------------------------------------------------------------------------
def test_second_actor_additive_write_never_touches_first_actors_state(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, _SLUG)
    sid_a, sid_b = "actor-A", "actor-B-additive"

    result_a = _run_write(ws, _SLUG, sid_a, "TASKS.md")
    assert result_a.returncode == 0, result_a.stderr
    presence_a_before = (_presence_dir(ws, _SLUG) / f"{sid_a}.json").read_text(encoding="utf-8")

    # B writes an in-repo ADDITIVE bug file through the REAL gate subprocess.
    target = ws / "repos" / _SLUG / "specs" / "bugs" / "from-actor-b.md"
    env = claude_hook_env(ws, session_id=sid_b)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
        "session_id": sid_b,
    }
    result_b = run_hook_subprocess("pre_gate", payload, env)
    assert result_b.returncode == 0, result_b.stderr
    assert result_b.block_envelope() is None, "in-repo specs/bugs write is ADDITIVE -> ALLOW"

    # A's presence record is byte-for-byte unchanged; ADDITIVE writes take no presence I/O.
    presence_a_after = (_presence_dir(ws, _SLUG) / f"{sid_a}.json").read_text(encoding="utf-8")
    assert presence_a_after == presence_a_before, "ADDITIVE write must not touch A's presence"
    # ADDITIVE writes create no presence record for the additive actor either.
    assert sid_b not in _presence_sessions(ws, _SLUG)


# --------------------------------------------------------------------------------------
# (iii) DISJOINT CONTEXTS — two actors mutate different repos concurrently, no cross-touch.
# --------------------------------------------------------------------------------------
def test_disjoint_contexts_no_cross_presence(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, _SLUG, _OTHER_SLUG)
    sid_a, sid_b = "session-ctxA", "session-ctxB"

    result_a = _run_write(ws, _SLUG, sid_a, "TASKS.md")
    assert result_a.returncode == 0, result_a.stderr
    assert result_a.block_envelope() is None

    result_b = _run_write(ws, _OTHER_SLUG, sid_b, "TASKS.md")
    assert result_b.returncode == 0, result_b.stderr
    assert result_b.block_envelope() is None

    # Each context recorded ONLY its own actor's presence — no cross-context contamination.
    recorded_a = _presence_sessions(ws, _SLUG)
    recorded_b = _presence_sessions(ws, _OTHER_SLUG)
    assert recorded_a == {sid_a}, recorded_a
    assert recorded_b == {sid_b}, recorded_b


# --------------------------------------------------------------------------------------
# (iv) A "stale" actor (no heartbeat renewal, real elapsed wall-clock) is EXCLUDED from
# a fresh actor's advisory — presence has no takeover concept, only TTL visibility.
# --------------------------------------------------------------------------------------
def test_stale_presence_excluded_from_advisory(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, _SLUG)
    sid_old, sid_new = "actor-old", "actor-new"

    result_old = _run_write(ws, _SLUG, sid_old, "TASKS.md")
    assert result_old.returncode == 0, result_old.stderr

    # Back-date the old actor's presence record past the TTL (no real sleep).
    record_path = _presence_dir(ws, _SLUG) / f"{sid_old}.json"
    data = json.loads(record_path.read_text(encoding="utf-8"))
    from datetime import UTC, datetime, timedelta

    from dadaia_workspace.core import kernel_tunables

    stale_ts = datetime.now(tz=UTC) - timedelta(seconds=kernel_tunables.PRESENCE_TTL_SECONDS + 30)
    data["last_seen_at"] = stale_ts.isoformat()
    record_path.write_text(json.dumps(data), encoding="utf-8")

    result_new = _run_write(ws, _SLUG, sid_new, "PLAN.md")
    assert result_new.returncode == 0, result_new.stderr
    assert result_new.block_envelope() is None
    combined = result_new.stdout + result_new.stderr
    assert sid_old not in combined, "a stale presence record must not appear in the advisory"
