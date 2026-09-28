"""Advisory throttle/sentinel markers under ``.dadaia/tmp/`` — the ONE mtime-throttle
idiom. Writers: ``hooks.sdd_post_gate`` (reconciler throttle), ``hooks.ctx_inject``
(sentinel/compact markers). A spent marker is an ordinary tmp entry: the doctor's one
zone walk expires it at the tmp TTL (sa-expiry-has-two-clocks).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.models.spec_context import CONTEXT_NAME_RE

__all__ = ["stamp_throttle", "throttled"]


def _valid_name(name: str) -> bool:
    return bool(CONTEXT_NAME_RE.fullmatch(name))


def throttled(workspace: Path, marker_name: str, *, window_seconds: float, now: float) -> bool:
    """True iff ``marker_name`` under ``.dadaia/tmp/`` was stamped within
    ``window_seconds`` of ``now`` (an epoch float, matching ``time.time()``).

    A traversal-shaped or otherwise invalid ``marker_name`` (anything outside
    ``[A-Za-z0-9_-]+`` — CWE-22/CWE-59) is never throttled: the caller degrades to
    "run now". A missing/unreadable marker is likewise never throttled (fail-open).
    """
    if not _valid_name(marker_name):
        return False
    marker = workspace / ".dadaia" / "tmp" / marker_name
    try:
        last = marker.stat().st_mtime
    except OSError:
        return False
    return (now - last) < window_seconds


def stamp_throttle(workspace: Path, marker_name: str) -> None:
    """Record that ``marker_name`` fired now (best-effort; never raises). An invalid
    ``marker_name`` is rejected outright — never written outside ``.dadaia/tmp/``."""
    if not _valid_name(marker_name):
        return
    marker = workspace / ".dadaia" / "tmp" / marker_name
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
    except OSError:
        return
