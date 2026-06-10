"""Unit tests for the session_identity consolidation module (T-010-07, WS-R3).

Covers FR-R3-01 (single owner: read/write of both pointer namespaces + session record),
FR-R3-02 (coherence contract), FR-R3-03 (PROTECTED storage paths), and the
ignored-and-superseded legacy-artifact law. No real time.sleep; tmp_path workspace.
"""

from __future__ import annotations

import json
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


# --------------------------------------------------------------------------- paths


def test_path_schemas_are_under_protected_dadaia_sessions(tmp_path: Path) -> None:
    """FR-R3-03: every artifact lives under .dadaia/sessions/ (PROTECTED)."""
    ws = _ws(tmp_path)
    for path in (
        si.ptr_path(ws, CTX),
        si.session_record_path(ws, SID),
    ):
        rel = path.relative_to(ws).as_posix()
        assert rel.startswith(".dadaia/sessions/"), rel


def test_path_validation_rejects_traversal(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    for bad in ("../escape", "a/b", "a.b"):
        with pytest.raises(ValueError, match="CWE-22"):
            si.ptr_path(ws, bad)
        with pytest.raises(ValueError, match="CWE-22"):
            si.session_record_path(ws, bad)


# --------------------------------------------------------------------------- incumbent ptr


def test_write_and_read_incumbent_ptr_roundtrip(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    assert si.read_incumbent_ptr(ws, CTX) is None
    si.write_incumbent_ptr(ws, CTX, SID)
    assert si.read_incumbent_ptr(ws, CTX) == SID


def test_write_incumbent_ptr_is_atomic_replace(tmp_path: Path) -> None:
    """A second write overwrites cleanly and leaves no .tmp residue."""
    ws = _ws(tmp_path)
    si.write_incumbent_ptr(ws, CTX, SID)
    si.write_incumbent_ptr(ws, CTX, OTHER)
    assert si.read_incumbent_ptr(ws, CTX) == OTHER
    runtime = ws / ".dadaia" / "sessions" / "runtime"
    assert [p.name for p in runtime.iterdir() if p.name.endswith(".tmp")] == []


def test_set_incumbent_alias_writes(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    si.set_incumbent(ws, CTX, SID)
    assert si.read_incumbent_ptr(ws, CTX) == SID


# --------------------------------------------------------------------------- session record


def test_session_record_roundtrip(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    assert si.read_session(ws, SID) is None
    record = {"id": SID, "mode": "READ", "pid": 4242, "context": CTX}
    si.write_session(ws, SID, record)
    got = si.read_session(ws, SID)
    assert got == record


def test_session_record_fail_soft_on_corrupt_json(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    si.session_record_path(ws, SID, create=True).write_text("{not json", encoding="utf-8")
    assert si.read_session(ws, SID) is None


def test_session_record_fail_soft_on_non_dict(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    si.session_record_path(ws, SID, create=True).write_text("[1, 2, 3]", encoding="utf-8")
    assert si.read_session(ws, SID) is None


def test_read_session_invalid_id_returns_none(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    assert si.read_session(ws, "../bad") is None


# --------------------------------------------------------------------------- resolve_identity


def test_resolve_identity_returns_incumbent_and_mode(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    si.write_incumbent_ptr(ws, CTX, SID)
    si.write_session(ws, SID, {"id": SID, "mode": "IMPLEMENTATION"})
    assert si.resolve_identity(ws, CTX) == {"incumbent": SID, "mode": "IMPLEMENTATION"}


def test_resolve_identity_no_state_returns_nones(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    assert si.resolve_identity(ws, CTX) == {"incumbent": None, "mode": None}


def test_resolve_identity_ptr_without_record_yields_no_mode(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    si.write_incumbent_ptr(ws, CTX, SID)
    assert si.resolve_identity(ws, CTX) == {"incumbent": SID, "mode": None}


# --------------------------------------------------------------------------- coherence (FR-R3-02)


def test_coherence_all_agree_is_none(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    si.write_incumbent_ptr(ws, CTX, SID)
    si.write_session(ws, SID, {"id": SID})
    assert si.coherence(ws, CTX, lock_holder=SID) is None


def test_coherence_absent_sources_are_not_a_violation(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    # only the lock holder is present — partial state during acquire is legal.
    assert si.coherence(ws, CTX, lock_holder=SID) is None


def test_coherence_three_disagreeing_sessions_is_reported(tmp_path: Path) -> None:
    """The canonical incoherence: lock holder, ptr, and record name 3 sessions."""
    ws = _ws(tmp_path)
    si.write_incumbent_ptr(ws, CTX, OTHER)
    si.write_session(ws, OTHER, {"id": "third-session"})
    msg = si.coherence(ws, CTX, lock_holder=SID)
    assert msg is not None
    assert CTX in msg
    assert SID in msg and OTHER in msg


def test_coherence_holder_vs_incumbent_disagree(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    si.write_incumbent_ptr(ws, CTX, OTHER)
    msg = si.coherence(ws, CTX, lock_holder=SID)
    assert msg is not None and SID in msg and OTHER in msg


# --------------------------------------------------------------------------- legacy / GC


def test_iter_ptr_files_collects_incumbent_namespace(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    si.write_incumbent_ptr(ws, CTX, SID)
    names = {p.name for p in si.iter_ptr_files(ws)}
    assert names == {f"{CTX}.ptr"}


def test_iter_ptr_files_empty_when_dir_absent(tmp_path: Path) -> None:
    ws = tmp_path / "bare"
    ws.mkdir()
    assert si.iter_ptr_files(ws) == []


def test_legacy_junk_ptr_is_ignored_not_fatal(tmp_path: Path) -> None:
    """Planted legacy/garbage .ptr content is read fail-soft, never crashes."""
    ws = _ws(tmp_path)
    runtime = ws / ".dadaia" / "sessions" / "runtime"
    (runtime / "legacy.ptr").write_text("", encoding="utf-8")  # empty → None
    assert si.read_incumbent_ptr(ws, "legacy") is None
    # planted pre-existing session json from an older layout: ignored-and-superseded.
    (ws / ".dadaia" / "sessions" / "old-layout.json").write_text(
        json.dumps({"legacy": True}), encoding="utf-8"
    )
    assert si.resolve_identity(ws, CTX) == {"incumbent": None, "mode": None}
