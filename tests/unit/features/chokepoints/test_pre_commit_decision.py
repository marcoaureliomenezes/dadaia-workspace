"""Unit tests for the pre-commit lease-gate decision (FR-W1-01 / DP-4).

Every fact is synthetic — a hand-written lease record, a fake pid probe, and a fake
ancestry callable. No real process, no subprocess, no ``os.kill``. The probe chain is
exercised as a single parametrized allow/block decision table covering the full
v0.1.9-v0.1.11 zero-false-block history, plus 3 verbatim-kept named regressions that
are the strongest individual proofs: the genuine live-foreign-holder BLOCK, the
relaunch-window advisory-allow (the exact ADR-G1 false-block reproduction), and the
block-branch probe-exception fail-safe.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

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
    legacy_no_pid: bool = False,
) -> None:
    lock_dir = workspace / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    hb = (heartbeat or _NOW).isoformat()
    record: dict[str, object] = {
        "context": ctx,
        "session_id": session_id,
        "heartbeat": hb,
        "ttl": ttl,
    }
    if not legacy_no_pid:
        record.update(
            {"release": "v0.1.14", "mode": "IMPLEMENTATION", "pid": pid, "acquired_at": hb}
        )
    (lock_dir / f"{ctx}.lock.json").write_text(json.dumps(record), encoding="utf-8")


def _always_alive(_pid: int) -> bool:
    return True


def _always_dead(_pid: int) -> bool:
    return False


def _boom_probe(_pid: int) -> bool:
    raise RuntimeError("probe blew up")


def _ancestry_const(result: Ancestry) -> Callable[[int, int], Ancestry]:
    def _probe(_ancestor: int, _descendant: int) -> Ancestry:
        return result

    return _probe


def _ancestry_boom(_a: int, _d: int) -> Ancestry:
    raise RuntimeError("probe blew up")


# ---------------------------------------------------------------------------
# Allow/block decision table — the full zero-false-block history as named rows.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "write_record", "env_sid", "pid_probe", "ancestry", "expect_warn_contains"),
    [
        pytest.param(
            "no-lease",
            False,
            None,
            _always_alive,
            Ancestry.NOT_ANCESTOR,
            None,
            id="no-lease-allows",
        ),
        pytest.param(
            "stale-dead",
            {"heartbeat": _NOW - timedelta(seconds=300)},
            None,
            _always_dead,
            Ancestry.NOT_ANCESTOR,
            None,
            id="stale-heartbeat-dead-pid-allows",
        ),
        pytest.param(
            "fresh",
            {},
            "holder-sid",
            _always_alive,
            Ancestry.NOT_ANCESTOR,
            None,
            id="env-sid-match-allows",
        ),
        pytest.param(
            "fresh",
            {},
            None,
            _always_alive,
            Ancestry.ANCESTOR,
            None,
            id="ancestor-allows",
        ),
        pytest.param(
            "fresh",
            {},
            None,
            _always_alive,
            Ancestry.UNKNOWN,
            "advisory",
            id="indeterminate-ancestry-allows-with-warn",
        ),
        pytest.param(
            "fresh",
            {},
            None,
            _always_alive,
            None,  # ancestry callable raises
            "advisory",
            id="ancestry-probe-exception-degrades-to-warn-allow",
        ),
        pytest.param(
            "legacy-no-pid",
            {"legacy_no_pid": True},
            None,
            _always_alive,
            Ancestry.NOT_ANCESTOR,
            "advisory",
            id="legacy-record-no-pid-allows-with-warn",
        ),
        pytest.param(
            "none-context",
            None,  # no record at all — context is None, no lookup
            None,
            _always_alive,
            Ancestry.NOT_ANCESTOR,
            None,
            id="none-context-allows",
        ),
        # v0.1.9-v0.1.11 relaunch-window regression matrix: non-stale record (fresh to
        # near-TTL heartbeat), recorded holder pid is DEAD ⇒ zero-false-block allow+WARN.
        pytest.param(
            "fresh",
            {"heartbeat": _NOW - timedelta(seconds=0)},
            None,
            _always_dead,
            Ancestry.NOT_ANCESTOR,
            "advisory",
            id="v0.1.9-fresh-heartbeat-dead-pid",
        ),
        pytest.param(
            "fresh",
            {"heartbeat": _NOW - timedelta(seconds=60)},
            None,
            _always_dead,
            Ancestry.NOT_ANCESTOR,
            "advisory",
            id="v0.1.10-mid-ttl-dead-pid",
        ),
        pytest.param(
            "fresh",
            {"heartbeat": _NOW - timedelta(seconds=119)},
            None,
            _always_dead,
            Ancestry.NOT_ANCESTOR,
            "advisory",
            id="v0.1.11-near-ttl-floor-dead-pid",
        ),
    ],
)
def test_pre_commit_allow_decision_table(
    tmp_path: Path,
    case: str,
    write_record: dict[str, Any] | bool | None,
    env_sid: str | None,
    pid_probe: Callable[[int], bool] | None,
    ancestry: Ancestry | None,
    expect_warn_contains: str | None,
) -> None:
    if write_record not in (False, None):
        kwargs = dict(write_record) if isinstance(write_record, dict) else {}
        legacy_no_pid = bool(kwargs.pop("legacy_no_pid", False))
        heartbeat = kwargs.pop("heartbeat", None)
        ttl = int(kwargs.pop("ttl", 120))
        _write_record(
            tmp_path,
            _CTX,
            session_id="holder-sid",
            pid=4321,
            legacy_no_pid=legacy_no_pid,
            heartbeat=heartbeat,
            ttl=ttl,
        )
    ctx = None if case == "none-context" else _CTX
    ancestry_fn = _ancestry_boom if ancestry is None else _ancestry_const(ancestry)
    d = pre_commit_decision(
        tmp_path,
        ctx,
        caller_pid=999,
        env_sid=env_sid,
        pid_probe=pid_probe,
        ancestry=ancestry_fn,
        now=_NOW,
    )
    assert d.allowed, f"{case}: expected allow, got block: {d.message}"
    if expect_warn_contains is not None:
        assert d.warn is not None
        assert expect_warn_contains in d.warn.lower()
    else:
        assert d.warn is None


# ---------------------------------------------------------------------------
# Named regressions — kept verbatim (strongest individual failure detectors)
# ---------------------------------------------------------------------------


def test_live_foreign_non_ancestor_blocks(tmp_path: Path) -> None:
    """A genuinely live foreign holder must never be stolen — the core no-steal veto."""
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


def test_relaunch_dead_pid_fresh_heartbeat_allows_with_warn(tmp_path: Path) -> None:
    """Relaunch window: dead recorded pid + fresh heartbeat + NOT_ANCESTOR ⇒ allow + WARN.

    This is the exact scenario the qa-gate reproduced as an ADR-G1 false-block. Before the
    fix the decision fell through to BLOCK; the dead-holder pid probe on the block branch
    now degrades it to an advisory allow. Kept verbatim as the named regression, distinct
    from the decision-table rows above by asserting the WARN names the holder.
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


def test_block_branch_pid_probe_exception_keeps_block(tmp_path: Path) -> None:
    """A probe that raises on the block branch must not flip a genuine block to allow —
    cannot confirm dead ⇒ stay conservative ⇒ block holds (fail-safe, not fail-open)."""
    _write_record(tmp_path, _CTX, session_id="holder-sid", pid=4321)
    d = pre_commit_decision(
        tmp_path,
        _CTX,
        caller_pid=999,
        env_sid="some-other-session",
        pid_probe=_boom_probe,
        ancestry=_ancestry_const(Ancestry.NOT_ANCESTOR),
        now=_NOW,
    )
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
