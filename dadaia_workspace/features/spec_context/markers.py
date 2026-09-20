"""Advisory throttle/sentinel markers under ``.dadaia/tmp/`` — the ONE mtime-throttle
idiom and the ONE reaper of the markers it leaves behind.

Writers: ``hooks.sdd_post_gate`` (reconciler throttle), ``hooks.ctx_inject``
(sentinel/compact markers). Every marker is a spent throttle stamp: no session
cross-reference exists to get wrong, so :func:`reap_markers` reaps by mtime alone.
Owned by the reaper lane (``spec_context.doctor.reap``), not by presence (0.4.7 c5 FR2).
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.core.models.spec_context import CONTEXT_NAME_RE

__all__ = ["MARKER_PREFIXES", "reap_markers", "stamp_throttle", "throttled"]

#: The marker-name prefixes the reaper owns. A prefix listed here is never "reaped by
#: nobody"; a prefix not listed here is not a throttle marker.
MARKER_PREFIXES: tuple[str, ...] = (
    "reconciler-last-",
    "ctx-inject-fired-",
    "ctx-compact-",
)

#: GC TTL (mtime-only) for every marker :func:`reap_markers` owns — one generous floor.
_MARKER_GC_TTL_SECONDS = kernel_tunables.SENTINEL_GC_TTL_SECONDS


def _valid_name(name: str) -> bool:
    return bool(CONTEXT_NAME_RE.fullmatch(name))


def _within_dadaia(path: Path, workspace: Path) -> bool:
    """True iff *path*, fully resolved (symlinks included), falls under
    ``<workspace>/.dadaia`` — resolve then ``relative_to``, never a string-prefix check
    (CWE-22 class)."""
    boundary = (workspace / ".dadaia").resolve()
    try:
        path.resolve().relative_to(boundary)
    except (ValueError, OSError):
        return False
    return True


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


def reap_markers(workspace: Path, *, now: float) -> tuple[str, ...]:
    """Delete markers under ``.dadaia/tmp/`` matching :data:`MARKER_PREFIXES` whose mtime
    is older than the GC TTL. Never raises; returns the reaped names, sorted."""
    tmp_dir = workspace / ".dadaia" / "tmp"
    try:
        entries = sorted(tmp_dir.iterdir())
    except OSError:
        return ()
    reaped: list[str] = []
    for path in entries:
        if not path.name.startswith(MARKER_PREFIXES):
            continue
        if not _within_dadaia(path, workspace):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if (now - mtime) < _MARKER_GC_TTL_SECONDS:
            continue
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)
            reaped.append(path.name)
    return tuple(reaped)
