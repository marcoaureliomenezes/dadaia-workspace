"""CLI ``dadaia lock steal`` — pid-probe threaded through the side door (T-011-01).

AC-W1-01 (CLI half): ``dadaia lock steal`` consults the pid-liveness probe.

    TTL-expired record + recorded pid ALIVE  -> refuse, exit 1, "holder alive"
    TTL-expired record + recorded pid DEAD   -> steal, exit 0
    record with NO ``pid`` field             -> TTL rule (steals when stale)

The probe is built from the production wiring (``hooks.sdd_gate._build_pid_probe``,
the container's ``OsProcessProbe``). These tests monkeypatch that builder so the
liveness verdict is deterministic and platform-seamed (no real ``os.kill``).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import lock as lock_cmd
from dadaia_workspace.features.spec_context import lease

runner = CliRunner()

CTX = "probectx"
TTL = lease.LEASE_TTL_SECONDS


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


def _patch_workspace_and_probe(monkeypatch: pytest.MonkeyPatch, ws: Path, *, alive: bool) -> None:
    monkeypatch.setattr(lock_cmd, "resolve_workspace_root", lambda: ws)
    monkeypatch.setattr(lock_cmd, "_build_pid_probe", lambda: lambda _pid: alive)


def test_steal_refuses_when_recorded_pid_alive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TTL-expired record + alive recorded pid ⇒ refuse, exit 1, message says holder alive."""
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed_stale_record(ws, pid=4242)
    _patch_workspace_and_probe(monkeypatch, ws, alive=True)

    result = runner.invoke(lock_cmd.app, [CTX])

    assert result.exit_code == 1, result.output
    assert "alive" in result.output.lower() or "live" in result.output.lower()
    # Record untouched — still the original holder.
    stored = json.loads(lease._record_path(ws, CTX).read_text())
    assert stored["session_id"] == "dead-holder"


def test_steal_succeeds_when_recorded_pid_dead(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TTL-expired record + dead recorded pid ⇒ steal, exit 0, new session written."""
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed_stale_record(ws, pid=4242)
    _patch_workspace_and_probe(monkeypatch, ws, alive=False)

    result = runner.invoke(lock_cmd.app, [CTX])

    assert result.exit_code == 0, result.output
    stored = json.loads(lease._record_path(ws, CTX).read_text())
    assert stored["session_id"] != "dead-holder"


def test_steal_pidless_record_uses_ttl_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Record without a ``pid`` field ⇒ TTL rule: a stale pid-less record is stealable."""
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed_stale_record(ws, pid=None)
    # Probe reports alive — but with no pid field there is nothing to veto on.
    _patch_workspace_and_probe(monkeypatch, ws, alive=True)

    result = runner.invoke(lock_cmd.app, [CTX])

    assert result.exit_code == 0, result.output
    stored = json.loads(lease._record_path(ws, CTX).read_text())
    assert stored["session_id"] != "dead-holder"
