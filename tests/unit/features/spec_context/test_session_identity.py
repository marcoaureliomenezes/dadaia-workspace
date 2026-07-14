"""Caller-scoped session identity and bind-epoch storage tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import session_identity as si

CTX = "myctx"
SID = "my-session-id"


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    return ws


# --------------------------------------------------------------------------- paths + traversal


@pytest.mark.parametrize(
    "bad_name",
    ["../escape", "a/b", "a.b"],
)
def test_path_validation_rejects_traversal(tmp_path: Path, bad_name: str) -> None:
    """FR-R3-03: every artifact lives under PROTECTED .dadaia/sessions/, and any name
    carrying a path separator or traversal segment is rejected (CWE-22)."""
    ws = _ws(tmp_path)
    path = si.session_record_path(ws, SID)
    assert path.relative_to(ws).as_posix().startswith(".dadaia/sessions/")
    with pytest.raises(ValueError, match="CWE-22"):
        si.session_record_path(ws, bad_name)


# --------------------------------------------------------------------------- record: roundtrip/atomic/fail-soft


def test_record_roundtrip_atomicity_and_fail_soft(tmp_path: Path) -> None:
    ws = _ws(tmp_path)

    # session record: absent -> None, write -> read roundtrip.
    assert si.read_session(ws, SID) is None
    record = {"id": SID, "mode": "READ", "pid": 4242, "context": CTX}
    si.write_session(ws, SID, record)
    assert si.read_session(ws, SID) == record
    sessions = ws / ".dadaia" / "sessions"
    assert [p.name for p in sessions.iterdir() if p.name.endswith(".tmp")] == []

    # fail-soft: corrupt JSON, non-dict content, and an invalid id all yield None.
    si.session_record_path(ws, "corrupt", create=True).write_text("{not json", encoding="utf-8")
    assert si.read_session(ws, "corrupt") is None
    si.session_record_path(ws, "nondict", create=True).write_text("[1, 2, 3]", encoding="utf-8")
    assert si.read_session(ws, "nondict") is None
    assert si.read_session(ws, "../bad") is None

    # Pre-existing session JSON remains fail-soft.
    (ws / ".dadaia" / "sessions" / "old-layout.json").write_text(
        json.dumps({"legacy": True}), encoding="utf-8"
    )
    assert si.read_session(ws, "old-layout") == {"legacy": True}


# --------------------------------------------------------------------------- last_seen_at / liveness_timestamp (T-011-04)


def test_last_seen_at_and_liveness_timestamp_matrix(tmp_path: Path) -> None:
    ws = _ws(tmp_path)

    # touch_last_seen_at stamps and persists.
    si.write_session(
        ws, SID, {"id": SID, "mode": "READ", "last_seen_at": "2020-01-01T00:00:00+00:00"}
    )
    updated = si.touch_last_seen_at(ws, SID, now="2030-06-10T12:00:00+00:00")
    assert updated is not None
    assert updated["last_seen_at"] == "2030-06-10T12:00:00+00:00"
    reread = si.read_session(ws, SID)
    assert reread is not None and reread["last_seen_at"] == "2030-06-10T12:00:00+00:00"

    # missing record -> None (fail-soft, no-op).
    assert si.touch_last_seen_at(ws, "ghost", now="2030-06-10T12:00:00+00:00") is None

    # liveness_timestamp: prefers last_seen_at, falls back to bound_at/created_at, else "".
    assert (
        si.liveness_timestamp(
            {"last_seen_at": "2030-06-10T12:00:00+00:00", "bound_at": "2020-01-01T00:00:00+00:00"}
        )
        == "2030-06-10T12:00:00+00:00"
    )
    assert (
        si.liveness_timestamp({"bound_at": "2020-01-01T00:00:00+00:00"})
        == "2020-01-01T00:00:00+00:00"
    )
    assert (
        si.liveness_timestamp({"created_at": "2019-01-01T00:00:00+00:00"})
        == "2019-01-01T00:00:00+00:00"
    )
    assert si.liveness_timestamp({"mode": "READ"}) == ""


# --------------------------------------------------------------------------- bind-epoch marker mtime/iter/garbage — 1 param


def test_bind_epoch_marker_lifecycle_and_fail_soft_matrix(tmp_path: Path) -> None:
    ws = _ws(tmp_path)

    # creates marker + dir; refreshes mtime on re-write; rejects traversal names.
    marker_dir = ws / ".dadaia" / "states" / "bind_epoch"
    assert not marker_dir.exists()
    si.write_bind_epoch(ws, CTX)
    marker = marker_dir / CTX
    assert marker.is_file()
    assert si.bind_epoch_path(ws, CTX) == marker
    base = marker.stat().st_mtime
    os.utime(marker, (base - 100, base - 100))
    backdated = marker.stat().st_mtime
    si.write_bind_epoch(ws, CTX)
    assert marker.stat().st_mtime > backdated
    with pytest.raises(ValueError):
        si.write_bind_epoch(ws, "../escape")

    # iter_bind_epochs: slug/mtime pairs; empty when absent; skips invalid names.
    si.write_bind_epoch(ws, "alpha")
    si.write_bind_epoch(ws, "beta")
    epochs = dict(si.iter_bind_epochs(ws))
    assert {"alpha", "beta"} <= set(epochs)
    assert all(isinstance(m, float) for m in epochs.values())
    empty_ws = _ws(tmp_path.parent / (tmp_path.name + "-empty-epochs"))
    assert si.iter_bind_epochs(empty_ws) == []
    bad = si.bind_epoch_dir(ws, create=True) / "bad name!"
    bad.write_text("x", encoding="utf-8")
    assert "bad name!" not in dict(si.iter_bind_epochs(ws))

    # garbage-tolerant reads: absent marker, all-garbage content, blank/garbage lines
    # interleaved with real pids, and a traversal ctx name — all fail-soft, never raise.
    absent_ws = _ws(tmp_path.parent / (tmp_path.name + "-absent"))
    assert si.read_bind_epoch_pids(absent_ws, CTX) == []
    assert si.read_bind_epoch_pid(absent_ws, CTX) is None

    garbage_marker = si.bind_epoch_dir(ws, create=True) / "garbage-ctx"
    for bad_content in ("not-a-pid", "0", "-7", ""):
        garbage_marker.write_text(bad_content, encoding="utf-8")
        assert si.read_bind_epoch_pids(ws, "garbage-ctx") == []
        assert si.read_bind_epoch_pid(ws, "garbage-ctx") is None

    mixed_marker = si.bind_epoch_dir(ws, create=True) / "mixed-ctx"
    mixed_marker.write_text("4242\n\ngarbage\n-1\n0\n5353\n", encoding="utf-8")
    assert si.read_bind_epoch_pids(ws, "mixed-ctx") == [4242, 5353]
    assert si.read_bind_epoch_pid(ws, "mixed-ctx") == 4242

    assert si.read_bind_epoch_pids(ws, "../escape") == []
    assert si.read_bind_epoch_pid(ws, "../escape") is None


# --------------------------------------------------------------------------- ancestry-chain content contract — CRITICAL, kept


def test_write_bind_epoch_records_ancestry_chain_as_content(tmp_path: Path) -> None:
    """W1-7/W1-8 (v0.1.47): the marker file CONTENT carries the bind process's
    nearest-first ANCESTRY PID CHAIN (one decimal pid per line, capped at 8, with
    non-positive pids filtered) so ctx-inject and the specs resolver attribute by
    MEMBERSHIP, surviving the ephemeral harness shell that dies between calls."""
    ws = _ws(tmp_path)

    si.write_bind_epoch(ws, CTX, pids=[4242, 5353, 6464])
    # One decimal pid per line, nearest-first.
    assert si.bind_epoch_path(ws, CTX).read_text(encoding="utf-8") == "4242\n5353\n6464\n"
    assert si.read_bind_epoch_pids(ws, CTX) == [4242, 5353, 6464]
    # The single-pid compat reader returns the FIRST (nearest) chain entry.
    assert si.read_bind_epoch_pid(ws, CTX) == 4242

    # Cap at 8 entries.
    long_chain = list(range(100, 100 + 20))  # 20 > the 8-entry cap
    si.write_bind_epoch(ws, CTX, pids=long_chain)
    capped = si.read_bind_epoch_pids(ws, CTX)
    assert capped == long_chain[:8]
    assert len(capped) == 8

    # Non-positive pids are filtered out of the chain.
    si.write_bind_epoch(ws, CTX, pids=[0, -7, 4242, 5353])
    assert si.read_bind_epoch_pids(ws, CTX) == [4242, 5353]

    # A re-write with a new chain refreshes mtime and content together.
    marker = si.bind_epoch_path(ws, CTX)
    base = marker.stat().st_mtime
    os.utime(marker, (base - 100, base - 100))
    backdated = marker.stat().st_mtime
    si.write_bind_epoch(ws, CTX, pids=[9999, 8888])
    assert marker.stat().st_mtime > backdated
    assert si.read_bind_epoch_pids(ws, CTX) == [9999, 8888]

    # Legacy shape (no pids arg) writes an EMPTY marker — never attributable. ``touch()``
    # does not truncate an existing file, so this is asserted against a FRESH context
    # (matching production: an empty marker is the initial/legacy shape, not a reset).
    fresh_ctx = "legacy-empty-ctx"
    si.write_bind_epoch(ws, fresh_ctx)
    assert si.bind_epoch_path(ws, fresh_ctx).read_text(encoding="utf-8") == ""
    assert si.read_bind_epoch_pids(ws, fresh_ctx) == []
    assert si.read_bind_epoch_pid(ws, fresh_ctx) is None
    # An explicit empty list is equally unattributable, on another fresh context.
    fresh_ctx2 = "legacy-empty-ctx-2"
    si.write_bind_epoch(ws, fresh_ctx2, pids=[])
    assert si.bind_epoch_path(ws, fresh_ctx2).read_text(encoding="utf-8") == ""
