"""``presence.gc`` — the ONE reaper (release 0.5.1 K2: "presence owns liveness
end-to-end; delete the post-gate reaper").

Intent: CONTRACT — release 0.5.1 K2

Before this release four separate reapers (the workspace doctor's own sweep loop, the
PostToolUse reconciler's ``_reap_stale_records``, ``ctx_inject``'s own sentinel sweep,
and ``tmp gc``'s marker lane) each re-derived staleness for overlapping record classes
at four different TTLs/multipliers — evidenced by
``doctor-ptr-gc-deletes-valid-lock-free-bind``,
``context-release-leaves-lease-heartbeat-renewing``, and
``doctor-stale-lease-misdiagnosed-as-forgery`` (``specs/bugs/BUGS.jsonl``).
``presence.gc`` replaces all four: it is now the ONLY reaper of presence records,
throttle/sentinel markers under ``.dadaia/tmp/``, and now-empty presence context dirs.
Replaces: ``tests/unit/hooks/test_post_gate_reap.py`` (deleted — the reap machinery it
pinned no longer exists in ``hooks.sdd_post_gate``),
``tests/unit/features/spec_context/test_doctor_presence_sweep.py`` (deleted —
``DoctorService`` no longer has its own ``PRESENCE-GC`` check/sweep pair, it calls
``presence.gc`` directly, tested against the real clock in the SIBLING file
``test_presence_gc_doctor_fix.py`` — split out to keep this file's frozen ``_NOW`` clean
of any real-clock call, per ``tests/contract/test_frozen_clock_aging_ratchet.py``), and
the marker-lane half of ``tests/unit/features/tmp_gc/test_tmp_gc_service.py`` (deleted —
orphan-marker sweeping moved here), and the sentinel-GC half of
``tests/unit/hooks/test_ctx_inject_digest.py`` (deleted — sentinel sweeping moved here).
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.features.spec_context import presence

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
_PRESENCE_TTL = kernel_tunables.PRESENCE_TTL_SECONDS
_MARKER_TTL = kernel_tunables.SENTINEL_GC_TTL_SECONDS


def _presence_path(ws: Path, ctx: str, sid: str) -> Path:
    return ws / ".dadaia" / "states" / "presence" / ctx / f"{sid}.json"


def _write_presence(
    ws: Path, ctx: str, sid: str, *, age_seconds: float = 0.0, corrupt: bool = False
) -> Path:
    path = _presence_path(ws, ctx, sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    if corrupt:
        path.write_text("{not-json", encoding="utf-8")
        return path
    seen = (_NOW - timedelta(seconds=age_seconds)).isoformat()
    record = {"session_id": sid, "runtime": "claude", "pid": 1, "last_seen_at": seen}
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _write_marker(ws: Path, name: str, *, age_seconds: float) -> Path:
    path = ws / ".dadaia" / "tmp" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("marker", encoding="utf-8")
    mtime = _NOW.timestamp() - age_seconds
    os.utime(path, (mtime, mtime))
    return path


# --------------------------------------------------------------------------- #
# gc() — table-driven over (records on disk, now, own sid, ttl) -> what survives.
# --------------------------------------------------------------------------- #


def test_fresh_presence_record_survives(tmp_path: Path) -> None:
    _write_presence(tmp_path, "ctx-a", "sess-fresh", age_seconds=0.0)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="")

    assert report.presence == ()
    assert _presence_path(tmp_path, "ctx-a", "sess-fresh").exists()


def test_stale_presence_record_reaped(tmp_path: Path) -> None:
    _write_presence(tmp_path, "ctx-a", "sess-stale", age_seconds=_PRESENCE_TTL + 60)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="")

    assert report.presence == ("ctx-a/sess-stale",)
    assert not _presence_path(tmp_path, "ctx-a", "sess-stale").exists()


def test_boundary_exactly_at_ttl_is_stale(tmp_path: Path) -> None:
    """``is_stale`` is ``>=`` — exactly-at-TTL is reclaimable, matching the ONE predicate."""
    _write_presence(tmp_path, "ctx-a", "sess-boundary", age_seconds=_PRESENCE_TTL)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="")

    assert report.presence == ("ctx-a/sess-boundary",)


def test_corrupt_presence_record_reaped(tmp_path: Path) -> None:
    _write_presence(tmp_path, "ctx-a", "sess-corrupt", corrupt=True)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="")

    assert report.presence == ("ctx-a/sess-corrupt",)


def test_own_stale_presence_record_never_reaped(tmp_path: Path) -> None:
    """own_session_id is NEVER a candidate, however stale it looks — the exact bug the
    prior reaper carried (a calling session reaping its own record)."""
    _write_presence(tmp_path, "ctx-a", "sess-me", age_seconds=_PRESENCE_TTL + 999)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="sess-me")

    assert report.presence == ()
    assert _presence_path(tmp_path, "ctx-a", "sess-me").exists()


def test_foreign_stale_record_reaped_even_when_own_sid_present(tmp_path: Path) -> None:
    _write_presence(tmp_path, "ctx-a", "sess-me", age_seconds=0.0)
    _write_presence(tmp_path, "ctx-a", "sess-other", age_seconds=_PRESENCE_TTL + 60)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="sess-me")

    assert report.presence == ("ctx-a/sess-other",)
    assert _presence_path(tmp_path, "ctx-a", "sess-me").exists()


def test_empty_context_dir_removed_after_last_record_reaped(tmp_path: Path) -> None:
    _write_presence(tmp_path, "ctx-a", "sess-stale", age_seconds=_PRESENCE_TTL + 60)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="")

    assert report.empty_context_dirs == ("ctx-a",)
    assert not (tmp_path / ".dadaia" / "states" / "presence" / "ctx-a").exists()


def test_context_dir_survives_when_a_record_remains(tmp_path: Path) -> None:
    _write_presence(tmp_path, "ctx-a", "sess-fresh", age_seconds=0.0)
    _write_presence(tmp_path, "ctx-a", "sess-stale", age_seconds=_PRESENCE_TTL + 60)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="")

    assert report.empty_context_dirs == ()
    assert (tmp_path / ".dadaia" / "states" / "presence" / "ctx-a").exists()


def test_missing_presence_root_never_raises(tmp_path: Path) -> None:
    report = presence.gc(tmp_path, now=_NOW, own_session_id="sess-x")
    assert report.presence == ()
    assert report.empty_context_dirs == ()


@pytest.mark.parametrize(
    ("marker_name", "age_seconds", "should_survive"),
    [
        ("reconciler-last-ghost", _MARKER_TTL + 3600, False),
        ("presence-warn-sess1-myctx", _MARKER_TTL + 3600, False),
        ("ctx-inject-fired-ghost", _MARKER_TTL + 3600, False),
        ("ctx-compact-ghost", _MARKER_TTL + 3600, False),
        ("reconciler-last-fresh", 5.0, True),
        ("reconciler-last-fresh", _MARKER_TTL - 5, True),
        ("some-unrelated-file.json", _MARKER_TTL + 3600, True),
    ],
    ids=[
        "aged_reconciler_marker_reaped",
        "aged_advisory_marker_reaped",
        "aged_sentinel_reaped",
        "aged_compact_marker_reaped",
        "fresh_marker_survives",
        "just_under_ttl_survives",
        "unrecognized_prefix_never_touched",
    ],
)
def test_marker_gc_table(
    tmp_path: Path, marker_name: str, age_seconds: float, should_survive: bool
) -> None:
    marker = _write_marker(tmp_path, marker_name, age_seconds=age_seconds)

    presence.gc(tmp_path, now=_NOW, own_session_id="")

    assert marker.exists() == should_survive


def test_marker_gc_report_names_the_reaped_marker(tmp_path: Path) -> None:
    _write_marker(tmp_path, "reconciler-last-ghost", age_seconds=_MARKER_TTL + 3600)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="")

    assert report.markers == ("reconciler-last-ghost",)


def test_gc_never_raises_on_missing_tmp_dir(tmp_path: Path) -> None:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    report = presence.gc(tmp_path, now=_NOW, own_session_id="")
    assert report.markers == ()


def test_gc_total_sums_every_lane(tmp_path: Path) -> None:
    _write_presence(tmp_path, "ctx-a", "sess-stale", age_seconds=_PRESENCE_TTL + 60)
    _write_marker(tmp_path, "reconciler-last-ghost", age_seconds=_MARKER_TTL + 3600)

    report = presence.gc(tmp_path, now=_NOW, own_session_id="")

    # 1 presence record + 1 empty context dir + 1 marker.
    assert report.total == 3


# --------------------------------------------------------------------------- #
# throttled / stamp_throttle — the ONE mtime-throttle-marker idiom.
# --------------------------------------------------------------------------- #


def test_stamp_then_throttled_within_window(tmp_path: Path) -> None:
    presence.stamp_throttle(tmp_path, "reconciler-last-sess1")
    now = (tmp_path / ".dadaia" / "tmp" / "reconciler-last-sess1").stat().st_mtime + 5
    assert presence.throttled(tmp_path, "reconciler-last-sess1", window_seconds=30, now=now)


def test_throttled_false_after_window_expires(tmp_path: Path) -> None:
    presence.stamp_throttle(tmp_path, "reconciler-last-sess1")
    now = (tmp_path / ".dadaia" / "tmp" / "reconciler-last-sess1").stat().st_mtime + 31
    assert not presence.throttled(tmp_path, "reconciler-last-sess1", window_seconds=30, now=now)


def test_throttled_false_when_marker_absent(tmp_path: Path) -> None:
    assert not presence.throttled(tmp_path, "reconciler-last-nobody", window_seconds=30, now=0.0)


def test_throttled_rejects_traversal_shaped_marker_name(tmp_path: Path) -> None:
    escape_probe = tmp_path / "escape-probe"
    hostile = f"../../../{escape_probe.name}"

    presence.stamp_throttle(tmp_path, hostile)

    assert not escape_probe.exists()
    assert presence.throttled(tmp_path, hostile, window_seconds=300, now=0.0) is False
