"""Caller-scoped session identity tests."""

from __future__ import annotations

import json
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
