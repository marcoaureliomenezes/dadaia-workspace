"""Intent: CONTRACT — K1 ("One Invocation") + F002 (20260830 audit): ``core.session_store``
owns the session-binding record — its path, schema, liveness rule and stale selection."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core import session_store as si

SID = "my-session-id"


@pytest.mark.parametrize("bad_name", ["../escape", "a/b", "a.b"])
def test_path_validation_rejects_traversal(tmp_path: Path, bad_name: str) -> None:
    """FR-R3-03: records live under PROTECTED .dadaia/sessions/; a traversal name is CWE-22."""
    assert si.session_record_path(tmp_path, SID).relative_to(tmp_path).as_posix() == (
        f".dadaia/sessions/{SID}.json"
    )
    with pytest.raises(ValueError, match="CWE-22"):
        si.session_record_path(tmp_path, bad_name)


def test_record_roundtrip_atomicity_and_fail_soft(tmp_path: Path) -> None:
    """A write reads back with no temp sibling; absent, corrupt, non-dict or invalid ids read None."""
    assert si.read_session(tmp_path, SID) is None
    record = {"id": SID, "mode": "READ", "pid": 4242, "context": "myctx"}
    si.write_session(tmp_path, SID, record)
    assert si.read_session(tmp_path, SID) == record
    assert [p.name for p in si.sessions_dir(tmp_path).iterdir()] == [f"{SID}.json"]
    si.session_record_path(tmp_path, "corrupt", create=True).write_text("{not json", "utf-8")
    si.session_record_path(tmp_path, "nondict", create=True).write_text("[1, 2, 3]", "utf-8")
    for name in ("corrupt", "nondict", "../bad"):
        assert si.read_session(tmp_path, name) is None


def test_touch_last_seen_at(tmp_path: Path) -> None:
    """The heartbeat stamps and persists ``last_seen_at``; a missing record is a no-op None."""
    si.write_session(tmp_path, SID, {"id": SID, "last_seen_at": "2020-01-01T00:00:00+00:00"})
    updated = si.touch_last_seen_at(tmp_path, SID, now="2030-06-10T12:00:00+00:00")
    assert updated is not None and updated["last_seen_at"] == "2030-06-10T12:00:00+00:00"
    assert si.read_session(tmp_path, SID) == updated
    assert si.touch_last_seen_at(tmp_path, "ghost", now="2030-06-10T12:00:00+00:00") is None


def test_new_binding_record_authors_the_schema_and_retired_keys_still_parse() -> None:
    """F002 schema; 0.4.7 FR4: an old record with ``mode``/``release`` keys still reads live."""
    now = datetime.now(tz=UTC).isoformat()
    record = si.new_binding_record(
        session_id="s1", context="alpha", runtime="claude-code", pid=1234, now=now
    )
    assert record == {
        "session_id": "s1",
        "context": "alpha",
        "runtime": "claude-code",
        "pid": 1234,
        "bound_at": now,
        "last_seen_at": now,
        "ttl_seconds": 300,
    }
    assert si.is_live({**record, "mode": "BOUND_IMPLEMENTATION", "release": "0.5.3"})


@pytest.mark.parametrize(
    ("record", "live"),
    [
        ({"last_seen_at": "2026-06-06T11:59:59+00:00", "ttl_seconds": 1800}, True),
        ({"last_seen_at": "2026-06-06T11:59:59Z", "ttl_seconds": 1800}, True),
        ({"last_seen_at": "2026-06-06T11:59:59", "ttl_seconds": 1800}, True),
        ({"last_seen_at": "2026-06-06T11:30:00+00:00", "ttl_seconds": 1800}, False),
        ({"last_seen_at": "2026-06-06T11:59:59+00:00", "ttl_seconds": 0}, False),
        ({"last_seen_at": "2026-06-06T11:59:59+00:00", "ttl_seconds": "x"}, False),
        ({"last_seen_at": "not-a-date", "ttl_seconds": 1800}, False),
        ({"last_seen_at": "", "ttl_seconds": 1800}, False),
        ({"bound_at": "2026-06-06T11:59:59+00:00", "ttl_seconds": 1800}, False),
        ({}, False),
    ],
)
def test_is_live_is_the_one_liveness_rule(record: dict[str, object], live: bool) -> None:
    """Intent: CONTRACT — sa-session-liveness-has-two-rules: ``last_seen_at`` younger than
    ``ttl_seconds`` (boundary stale) is live; a record without it (``bound_at`` only, the
    retired creation-time fallback, §4a item 13) or with a corrupt clock/TTL is not."""
    assert si.is_live(record, clock=lambda: datetime(2026, 6, 6, 12, tzinfo=UTC)) is live


def test_live_session_and_stale_records_select_by_the_same_rule(tmp_path: Path) -> None:
    """A fresh record is the live session; an expired one is the only stale record."""
    fresh = si.new_binding_record(
        session_id="live-1",
        context="a",
        runtime="unknown",
        pid=1,
        now=datetime.now(tz=UTC).isoformat(),
    )
    si.write_session(tmp_path, "live-1", fresh)
    si.write_session(tmp_path, "dead-1", {**fresh, "last_seen_at": "2000-01-01T00:00:00+00:00"})
    (si.sessions_dir(tmp_path) / "not-a-record.txt").write_text("", encoding="utf-8")
    assert si.live_session(tmp_path, "live-1") == fresh
    assert si.live_session(tmp_path, "dead-1") is None
    assert si.live_session(tmp_path, "absent") is None
    assert si.stale_records(tmp_path) == [si.sessions_dir(tmp_path) / "dead-1.json"]


def test_gc_check_assembly_has_one_home() -> None:
    """F002: no module hand-builds the ``gc_check`` liveness input outside session_store."""
    import dadaia_workspace

    pkg_root = Path(dadaia_workspace.__file__).parent
    offenders = [p for p in pkg_root.rglob("*.py") if "gc_check" in p.read_text(encoding="utf-8")]
    assert offenders == []
