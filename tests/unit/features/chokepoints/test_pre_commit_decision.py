"""Unit tests for the pre-commit lease-gate decision (FR-W1-01 / DP-4).

Every fact is synthetic — a hand-written lease record, a fake pid probe, and a fake
ancestry callable. No real process, no subprocess, no ``os.kill``. The probe chain is
exercised case-by-case (no/stale-dead lease → allow; env-sid match → allow; ancestor →
allow; indeterminate → allow+WARN; live foreign non-ancestor → block).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.process_ancestry import Ancestry
from dadaia_workspace.features.chokepoints import pre_commit_decision
from dadaia_workspace.features.chokepoints.service import context_slug_for_path

_CTX = "demo-ctx"
_NOW = datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC)


def _write_record(
    workspace: Path,
    ctx: str,
    *,
    session_id: str,
    pid: int,
    heartbeat: datetime | None = None,
    ttl: int = 120,
) -> None:
    lock_dir = workspace / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    hb = (heartbeat or _NOW).isoformat()
    (lock_dir / f"{ctx}.lock.json").write_text(
        json.dumps(
            {
                "context": ctx,
                "release": "v0.1.14",
                "session_id": session_id,
                "mode": "IMPLEMENTATION",
                "pid": pid,
                "acquired_at": hb,
                "heartbeat": hb,
                "ttl": ttl,
            }
        ),
        encoding="utf-8",
    )


def _always_alive(_pid: int) -> bool:
    return True


def _always_dead(_pid: int) -> bool:
    return False


def _ancestry_const(result: Ancestry):
    def _probe(_ancestor: int, _descendant: int) -> Ancestry:
        return result

    return _probe


def test_no_lease_allows(tmp_path: Path) -> None:
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid=None,
        pid_probe=_always_alive,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    assert d.allowed
    assert d.warn is None


def test_stale_dead_lease_allows(tmp_path: Path) -> None:
    # Heartbeat aged well past TTL and the holder pid is dead ⇒ stale ⇒ allow.
    _write_record(
        tmp_path,
        _CTX,
        session_id="holder",
        pid=4321,
        heartbeat=_NOW - timedelta(seconds=300),
    )
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid=None,
        pid_probe=_always_dead,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    assert d.allowed


def test_env_sid_match_allows(tmp_path: Path) -> None:
    _write_record(tmp_path, _CTX, session_id="holder-sid", pid=4321)
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid="holder-sid",
        pid_probe=_always_alive,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    assert d.allowed
    assert d.warn is None


def test_ancestor_allows(tmp_path: Path) -> None:
    _write_record(tmp_path, _CTX, session_id="holder-sid", pid=4321)
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid=None,
        pid_probe=_always_alive,
        ancestry=_ancestry_const(Ancestry.ANCESTOR),
        now=_NOW,
    )
    assert d.allowed
    assert d.warn is None


def test_indeterminate_ancestry_allows_with_warn(tmp_path: Path) -> None:
    _write_record(tmp_path, _CTX, session_id="holder-sid", pid=4321)
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid=None,
        pid_probe=_always_alive,
        ancestry=_ancestry_const(Ancestry.UNKNOWN),
        now=_NOW,
    )
    assert d.allowed
    assert d.warn is not None
    assert "advisory" in d.warn.lower()


def test_live_foreign_non_ancestor_blocks(tmp_path: Path) -> None:
    _write_record(tmp_path, _CTX, session_id="holder-sid", pid=4321)
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid="some-other-session",
        pid_probe=_always_alive,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    assert not d.allowed
    assert "holder-sid" in d.message
    # Forbidden-law: the block message never instructs a manual unblock ceremony.
    lowered = d.message.lower()
    for forbidden in ("rebind", "relaunch", "lock steal"):
        assert forbidden not in lowered, d.message


def test_block_message_states_holder_and_age(tmp_path: Path) -> None:
    _write_record(
        tmp_path,
        _CTX,
        session_id="holder-sid",
        pid=4321,
        heartbeat=_NOW - timedelta(seconds=30),
    )
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid=None,
        pid_probe=_always_alive,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    assert not d.allowed
    assert "30s" in d.message
    assert "frees itself" in d.message


def test_ancestry_probe_exception_degrades_to_warn_allow(tmp_path: Path) -> None:
    _write_record(tmp_path, _CTX, session_id="holder-sid", pid=4321)

    def _boom(_a: int, _d: int) -> Ancestry:
        raise RuntimeError("probe blew up")

    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid=None,
        pid_probe=_always_alive,
        ancestry=_boom,
        now=_NOW,
    )
    assert d.allowed
    assert d.warn is not None


def test_legacy_record_no_pid_allows_with_warn(tmp_path: Path) -> None:
    lock_dir = tmp_path / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / f"{_CTX}.lock.json").write_text(
        json.dumps(
            {
                "context": _CTX,
                "session_id": "holder-sid",
                "heartbeat": _NOW.isoformat(),
                "ttl": 120,
            }
        ),
        encoding="utf-8",
    )
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid=None,
        pid_probe=_always_alive,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    assert d.allowed
    assert d.warn is not None


def test_none_context_allows(tmp_path: Path) -> None:
    d = pre_commit_decision(
        tmp_path,
        None,
        caller_pid=999,
        env_sid=None,
        pid_probe=_always_alive,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    assert d.allowed


# ---------------------------------------------------------------------------------------
# Relaunch window (FR-W4 / ADR-G1) — the v0.1.9–v0.1.11 false-block regression class.
#
# Root cause the qa-gate REJECT reproduced: ``is_stale`` keeps a fresh-heartbeat record
# live, and ``renew_heartbeat`` never refreshes ``pid``. So a same-sid relaunch (new pid,
# same .ptr) leaves a DEAD recorded pid while the heartbeat stays fresh. The relaunched
# incumbent commits from a new process tree (no env sid) ⇒ ancestry(dead_pid, caller)
# walks to init = NOT_ANCESTOR. The dead holder is NOT a live foreign identity, so the
# block branch must consult the pid probe and ALLOW + WARN rather than false-block.
# ---------------------------------------------------------------------------------------
def test_relaunch_dead_pid_fresh_heartbeat_allows_with_warn(tmp_path: Path) -> None:
    """Relaunch window: dead recorded pid + fresh heartbeat + NOT_ANCESTOR ⇒ allow + WARN.

    This is the exact scenario the qa-gate reproduced as an ADR-G1 false-block. Before the
    fix the decision fell through to BLOCK; the dead-holder pid probe on the block branch
    now degrades it to an advisory allow.
    """
    _write_record(tmp_path, _CTX, session_id="holder-sid", pid=4321)  # fresh heartbeat
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid=None,  # relaunched incumbent re-runs `git commit` with no exported sid
        pid_probe=_always_dead,  # the recorded holder pid is dead
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),  # dead pid is in nobody's tree
        now=_NOW,
    )
    assert d.allowed, "relaunched incumbent (dead recorded pid) must NOT be blocked"
    assert d.warn is not None
    assert "relaunch" in d.warn.lower()
    assert "advisory" in d.warn.lower()
    # The corrective WARN names the holder so the advisory is auditable.
    assert "holder-sid" in d.warn


@pytest.mark.parametrize(
    ("scenario", "heartbeat_age_seconds"),
    [
        # v0.1.9: lease-theft class — long-running pytest starves heartbeat renewal;
        # here the relaunch keeps the heartbeat fresh but the recorded pid is dead.
        ("v0.1.9_fresh_heartbeat_dead_pid", 0),
        # v0.1.10: the heartbeat is mid-TTL — still not stale, dead recorded pid.
        ("v0.1.10_mid_ttl_dead_pid", 60),
        # v0.1.11: heartbeat almost at the TTL floor but strictly below it; the pid-veto
        # in is_stale would keep a *live* pid's lease, but this pid is dead.
        ("v0.1.11_near_ttl_dead_pid", 119),
    ],
)
def test_v019_to_v0111_false_block_regression_matrix(
    tmp_path: Path, scenario: str, heartbeat_age_seconds: int
) -> None:
    """Parametrized v0.1.9–v0.1.11 false-block history (TASKS T-014-14 declared matrix).

    Every scenario is a non-stale record (heartbeat strictly within TTL) whose recorded
    holder pid is DEAD — the relaunched-incumbent state. None may block the commit.
    """
    _write_record(
        tmp_path,
        _CTX,
        session_id="holder-sid",
        pid=4321,
        heartbeat=_NOW - timedelta(seconds=heartbeat_age_seconds),
    )
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid=None,
        pid_probe=_always_dead,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    assert d.allowed, f"{scenario}: dead-holder relaunch must flow (zero-false-block)"
    assert d.warn is not None, f"{scenario}: advisory degradation must be logged"


def test_live_foreign_non_ancestor_still_blocks_after_relaunch_fix(tmp_path: Path) -> None:
    """The fix must NOT weaken the genuine-foreign-holder block: live pid ⇒ still BLOCK."""
    _write_record(tmp_path, _CTX, session_id="holder-sid", pid=4321)
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid="some-other-session",
        pid_probe=_always_alive,  # genuinely live foreign holder
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    assert not d.allowed
    assert "holder-sid" in d.message


def test_block_branch_pid_probe_exception_keeps_block(tmp_path: Path) -> None:
    """A probe that raises on the block branch must not flip a genuine block to allow."""
    _write_record(tmp_path, _CTX, session_id="holder-sid", pid=4321)

    def _boom_probe(_pid: int) -> bool:
        raise RuntimeError("probe blew up")

    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid="some-other-session",
        pid_probe=_boom_probe,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
    # Cannot confirm dead ⇒ stay conservative ⇒ block holds.
    assert not d.allowed


def test_context_slug_for_path(tmp_path: Path) -> None:
    workspace = tmp_path
    repo = workspace / "repos" / "my-service"
    repo.mkdir(parents=True)
    assert context_slug_for_path(workspace, repo) == "my-service"
    # The workspace root itself is not a Spec Context repo.
    assert context_slug_for_path(workspace, workspace) is None
    # A nested dir inside a repo is not the repo root.
    nested = repo / "src"
    nested.mkdir()
    assert context_slug_for_path(workspace, nested) is None
