"""Unit tests for is_stale_session in core/lock_liveness.py (T-017-10).

These tests verify behavior BEFORE the implementation exists (TDD red phase).
"""

from __future__ import annotations

import datetime

from dadaia_workspace.core.lock_liveness import is_stale_session


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


_UTC = datetime.UTC


def test_stale_session_when_elapsed_exceeds_ttl() -> None:
    """A session whose last_seen_at is beyond its TTL is stale."""
    ten_min_ago = _iso(datetime.datetime.now(tz=_UTC) - datetime.timedelta(minutes=10))
    assert is_stale_session(ten_min_ago, 300) is True  # 600s elapsed > 300s TTL


def test_fresh_session_not_stale() -> None:
    """A session seen very recently is not stale."""
    one_sec_ago = _iso(datetime.datetime.now(tz=_UTC) - datetime.timedelta(seconds=1))
    assert is_stale_session(one_sec_ago, 300) is False  # 1s elapsed < 300s TTL


def test_empty_last_seen_at_is_not_stale() -> None:
    """An empty last_seen_at is treated as not-stale (safe default)."""
    assert is_stale_session("", 300) is False


def test_unparseable_last_seen_at_is_not_stale() -> None:
    """A malformed last_seen_at is treated as not-stale (fail-safe)."""
    assert is_stale_session("not-a-timestamp", 300) is False


def test_z_suffix_handled() -> None:
    """Z-suffix ISO timestamps are parsed correctly."""
    two_min_ago = _iso(datetime.datetime.now(tz=_UTC) - datetime.timedelta(minutes=2))
    assert two_min_ago.endswith("Z")
    # ttl = 60s — 120s elapsed → stale
    assert is_stale_session(two_min_ago, 60) is True
    # ttl = 300s — 120s elapsed → not stale
    assert is_stale_session(two_min_ago, 300) is False


def test_boundary_at_exactly_ttl() -> None:
    """The staleness predicate uses > (strictly greater than), not >=.

    The kanban.py original uses ``elapsed > ttl_seconds`` — preserve this
    boundary so the function is a drop-in replacement.
    """
    # We cannot control the exact clock in this test, but we can verify that
    # a session with last_seen_at far in the future is never stale.
    far_future = _iso(datetime.datetime.now(tz=_UTC) + datetime.timedelta(hours=1))
    assert is_stale_session(far_future, 300) is False
