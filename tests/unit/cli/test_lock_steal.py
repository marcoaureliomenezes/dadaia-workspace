"""CLI ``dadaia lock steal`` — pid-probe threaded through the side door (T-011-01).

AC-W1-01 (CLI half): ``dadaia lock steal`` consults the pid-liveness probe.

    TTL-expired record + recorded pid ALIVE  -> refuse, exit 1, "holder alive"
    TTL-expired record + recorded pid DEAD   -> steal, exit 0
    record with NO ``pid`` field             -> TTL rule (steals when stale)

The probe is built from the production wiring
(``infrastructure.process_probe_adapter.build_pid_probe``, the platform-seamed
``OsProcessProbe``). These tests monkeypatch that builder so the liveness verdict is
deterministic and platform-seamed (no real ``os.kill``).

CRIT: pid-veto through the CLI side door — all three verdicts survive below as
parametrized rows.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import lock as lock_cmd
from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.features.spec_context import lease

runner = CliRunner()

CTX = "probectx"
TTL = kernel_tunables.LEASE_TTL_SECONDS


def _seed_stale_record(ws: Path, *, pid: int | None) -> None:
    """Write a TTL-expired lease record (heartbeat well past TTL) directly to disk."""
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True, exist_ok=True)
    hb = (datetime.now(tz=UTC) - timedelta(seconds=TTL + 600)).isoformat()
    rec: dict[str, object] = {
        "context": CTX,
        "release": "v0.1.11",
        "session_id": "dead-holder",
        "mode": "IMPLEMENTATION",
        "acquired_at": hb,
        "heartbeat": hb,
        "ttl": TTL,
    }
    if pid is not None:
        rec["pid"] = pid
    lease._record_path(ws, CTX).write_text(json.dumps(rec), encoding="utf-8")
    # T-43-10: `lock steal` is release-aware — a lease pinned to a release that is NOT the
    # context's ACTIVE release is reclaimable regardless of holder-pid liveness. These tests
    # isolate the *holder-liveness* (pid-veto / TTL) behavior, so the lease must be the
    # ACTIVE-release lease; otherwise it is an orphaned/archived lease that always reclaims
    # (that release-awareness path is covered by tests/unit/core/test_lock_liveness_release_aware.py).
    active = ws / "specs" / "releases"
    active.mkdir(parents=True, exist_ok=True)
    (active / "ACTIVE.md").write_text(
        "release: v0.1.11\nsegment: alpha-1\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )


def _patch_workspace_and_probe(monkeypatch: pytest.MonkeyPatch, ws: Path, *, alive: bool) -> None:
    monkeypatch.setattr(lock_cmd, "resolve_workspace_root", lambda: ws)
    monkeypatch.setattr(lock_cmd, "build_pid_probe", lambda: lambda _pid: alive)


@pytest.mark.parametrize(
    ("name", "pid", "probe_alive", "expected_exit", "expect_stolen"),
    [
        (
            # TTL-expired record + alive recorded pid ⇒ refuse, exit 1, holder untouched.
            "recorded_pid_alive_refuses",
            4242,
            True,
            1,
            False,
        ),
        (
            # TTL-expired record + dead recorded pid ⇒ steal, exit 0, new session written.
            "recorded_pid_dead_steals",
            4242,
            False,
            0,
            True,
        ),
        (
            # Record without a pid field ⇒ TTL rule: a stale pid-less record is
            # stealable even though the probe reports alive (nothing to veto on).
            "pidless_record_uses_ttl_rule",
            None,
            True,
            0,
            True,
        ),
    ],
)
def test_lock_steal_verdict_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    pid: int | None,
    probe_alive: bool,
    expected_exit: int,
    expect_stolen: bool,
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed_stale_record(ws, pid=pid)
    _patch_workspace_and_probe(monkeypatch, ws, alive=probe_alive)

    result = runner.invoke(lock_cmd.app, [CTX])

    assert result.exit_code == expected_exit, result.output
    stored = json.loads(lease._record_path(ws, CTX).read_text())
    if expect_stolen:
        assert stored["session_id"] != "dead-holder"
    else:
        assert stored["session_id"] == "dead-holder"
        assert "alive" in result.output.lower() or "live" in result.output.lower()
