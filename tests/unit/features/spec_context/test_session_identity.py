"""Unit tests for the session_identity consolidation module (T-010-07, WS-R3).

Covers FR-R3-01 (single owner: read/write of both pointer namespaces + session record),
FR-R3-02 (coherence contract), FR-R3-03 (PROTECTED storage paths), and the
ignored-and-superseded legacy-artifact law. No real time.sleep; tmp_path workspace.

CRITICAL bind attribution (v0.1.47 W1-7/8): the ancestry-chain content contract
(nearest-first, 8-cap, garbage-tolerant) is preserved as a dedicated kept pair (write +
read), since ctx-inject attribution parses this exact format. The three-way coherence
incoherence report is the other CRITICAL kept test — the operator-facing diagnostic for
lock-holder / incumbent-ptr / session-record disagreement.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import session_identity as si

CTX = "myctx"
SID = "my-session-id"
OTHER = "foreign-session-id"


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (ws / ".dadaia" / "sessions" / "runtime").mkdir(parents=True)
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
    for path in (si.ptr_path(ws, CTX), si.session_record_path(ws, SID)):
        rel = path.relative_to(ws).as_posix()
        assert rel.startswith(".dadaia/sessions/"), rel
    with pytest.raises(ValueError, match="CWE-22"):
        si.ptr_path(ws, bad_name)
    with pytest.raises(ValueError, match="CWE-22"):
        si.session_record_path(ws, bad_name)


# --------------------------------------------------------------------------- ptr + record: roundtrip/atomic/fail-soft


def test_ptr_and_record_roundtrip_atomicity_and_fail_soft(tmp_path: Path) -> None:
    ws = _ws(tmp_path)

    # incumbent ptr: absent -> None, write -> read roundtrip.
    assert si.read_incumbent_ptr(ws, CTX) is None
    si.write_incumbent_ptr(ws, CTX, SID)
    assert si.read_incumbent_ptr(ws, CTX) == SID

    # a second write overwrites atomically and leaves no .tmp residue.
    si.write_incumbent_ptr(ws, CTX, OTHER)
    assert si.read_incumbent_ptr(ws, CTX) == OTHER
    runtime = ws / ".dadaia" / "sessions" / "runtime"
    assert [p.name for p in runtime.iterdir() if p.name.endswith(".tmp")] == []

    # session record: absent -> None, write -> read roundtrip.
    assert si.read_session(ws, SID) is None
    record = {"id": SID, "mode": "READ", "pid": 4242, "context": CTX}
    si.write_session(ws, SID, record)
    assert si.read_session(ws, SID) == record

    # fail-soft: corrupt JSON, non-dict content, and an invalid id all yield None.
    si.session_record_path(ws, "corrupt", create=True).write_text("{not json", encoding="utf-8")
    assert si.read_session(ws, "corrupt") is None
    si.session_record_path(ws, "nondict", create=True).write_text("[1, 2, 3]", encoding="utf-8")
    assert si.read_session(ws, "nondict") is None
    assert si.read_session(ws, "../bad") is None

    # legacy/garbage .ptr and pre-existing session json are ignored-and-superseded, never fatal.
    (runtime / "legacy.ptr").write_text("", encoding="utf-8")  # empty → None
    assert si.read_incumbent_ptr(ws, "legacy") is None
    (ws / ".dadaia" / "sessions" / "old-layout.json").write_text(
        json.dumps({"legacy": True}), encoding="utf-8"
    )
    assert si.resolve_identity(ws, "unrelated-ctx") == {"incumbent": None, "mode": None}

    # iter_ptr_files: collects the incumbent namespace; empty when the dir is absent.
    names = {p.name for p in si.iter_ptr_files(ws)}
    assert f"{CTX}.ptr" in names
    bare_ws = tmp_path / "bare"
    bare_ws.mkdir()
    assert si.iter_ptr_files(bare_ws) == []


# --------------------------------------------------------------------------- resolve_identity states


def _write_ptr_and_session(ws: Path) -> None:
    si.write_incumbent_ptr(ws, CTX, SID)
    si.write_session(ws, SID, {"id": SID, "mode": "IMPLEMENTATION"})


@pytest.mark.parametrize(
    ("setup", "expected"),
    [
        pytest.param(
            _write_ptr_and_session,
            {"incumbent": SID, "mode": "IMPLEMENTATION"},
            id="incumbent-and-mode-present",
        ),
        pytest.param(
            lambda ws: None,
            {"incumbent": None, "mode": None},
            id="no-state-returns-nones",
        ),
        pytest.param(
            lambda ws: si.write_incumbent_ptr(ws, CTX, SID),
            {"incumbent": SID, "mode": None},
            id="ptr-without-record-yields-no-mode",
        ),
    ],
)
def test_resolve_identity_states(tmp_path: Path, setup, expected: dict[str, str | None]) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(tmp_path)
    setup(ws)
    assert si.resolve_identity(ws, CTX) == expected


# --------------------------------------------------------------------------- coherence (FR-R3-02) — CRITICAL, kept


def test_coherence_three_way_incoherence_report(tmp_path: Path) -> None:
    """The canonical incoherence: lock holder, ptr, and record name disagreeing
    sessions must be reported by name; agreement and partial-absence are non-violations."""
    ws = _ws(tmp_path)

    # All agree -> no report.
    si.write_incumbent_ptr(ws, CTX, SID)
    si.write_session(ws, SID, {"id": SID})
    assert si.coherence(ws, CTX, lock_holder=SID) is None

    # Only the lock holder present (partial state during acquire) -> not a violation.
    ws2 = _ws(tmp_path.parent / (tmp_path.name + "-partial"))
    assert si.coherence(ws2, CTX, lock_holder=SID) is None

    # Three disagreeing sessions -> reported by name.
    ws3 = _ws(tmp_path.parent / (tmp_path.name + "-disagree"))
    si.write_incumbent_ptr(ws3, CTX, OTHER)
    si.write_session(ws3, OTHER, {"id": "third-session"})
    msg = si.coherence(ws3, CTX, lock_holder=SID)
    assert msg is not None
    assert CTX in msg
    assert SID in msg and OTHER in msg

    # Holder vs incumbent disagree (two-way) -> also reported.
    ws4 = _ws(tmp_path.parent / (tmp_path.name + "-holder-vs-incumbent"))
    si.write_incumbent_ptr(ws4, CTX, OTHER)
    msg2 = si.coherence(ws4, CTX, lock_holder=SID)
    assert msg2 is not None and SID in msg2 and OTHER in msg2


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
