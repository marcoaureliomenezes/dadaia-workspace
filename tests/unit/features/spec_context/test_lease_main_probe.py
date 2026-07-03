"""``lease._main`` threads the pid-liveness probe (T-011-01, FR-W1-01).

The CLI entrypoint ``lease._main`` is the SDD gate's single acquisition point. Its
``acquire``/``steal`` paths must consult the same probe the gate uses, so a
TTL-expired-but-still-running foreign holder is not taken over via the side door.

    acquire: TTL-expired record + alive recorded pid  -> exit 1 (yield, holder live)
    acquire: TTL-expired record + dead recorded pid    -> exit 0 (TAKEOVER)
    steal:   TTL-expired record + alive recorded pid    -> exit 1 (LIVE, refuse)
    steal:   TTL-expired record + dead recorded pid      -> exit 0 (STOLEN)

The probe is monkeypatched at its builder so the verdict is deterministic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.features.spec_context import lease

CTX = "mainctx"
TTL = kernel_tunables.LEASE_TTL_SECONDS


def _seed_stale_record(ws: Path, *, pid: int | None) -> None:
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


def _patch_probe(monkeypatch: pytest.MonkeyPatch, ws: Path, *, alive: bool) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setattr(lease, "_main_pid_probe", lambda: lambda _pid: alive)


def test_main_acquire_yields_when_pid_alive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed_stale_record(ws, pid=4242)
    _patch_probe(monkeypatch, ws, alive=True)

    rc = lease._main(["acquire", CTX, "newsess", "v0.1.11", "IMPLEMENTATION"])

    assert rc == 1
    stored = json.loads(lease._record_path(ws, CTX).read_text())
    assert stored["session_id"] == "dead-holder"


def test_main_acquire_takes_over_when_pid_dead(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed_stale_record(ws, pid=4242)
    _patch_probe(monkeypatch, ws, alive=False)

    rc = lease._main(["acquire", CTX, "newsess", "v0.1.11", "IMPLEMENTATION"])

    assert rc == 0
    stored = json.loads(lease._record_path(ws, CTX).read_text())
    assert stored["session_id"] == "newsess"


def test_main_steal_refuses_when_pid_alive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed_stale_record(ws, pid=4242)
    _patch_probe(monkeypatch, ws, alive=True)

    rc = lease._main(["steal", CTX, "thief"])

    assert rc == 1
    stored = json.loads(lease._record_path(ws, CTX).read_text())
    assert stored["session_id"] == "dead-holder"


def test_main_steal_succeeds_when_pid_dead(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed_stale_record(ws, pid=4242)
    _patch_probe(monkeypatch, ws, alive=False)

    rc = lease._main(["steal", CTX, "thief"])

    assert rc == 0
    stored = json.loads(lease._record_path(ws, CTX).read_text())
    assert stored["session_id"] == "thief"
