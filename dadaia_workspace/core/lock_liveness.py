"""Pure liveness predicate for the single-record TTL-lease (v0.1.6).

This is the *only* place ``(now - heartbeat) >= ttl`` is evaluated. It is a pure
model-layer function: zero I/O, stdlib-only imports, and every time/process/session
seam is injected so callers (and tests) stay deterministic.

Design decisions (state-model redesign, OQ-1):
  * **No PID.** Liveness is TTL-only so the lease is cross-platform (Windows-safe).
    ``pid_probe`` is accepted for injection-signature compatibility but never used.
  * **Fail-open on corrupt.** A record that is absent, missing required fields, or
    has an unparseable heartbeat is treated as *stale* (acquirable), never as a
    live lock. This is the operator's overriding mandate: the lease must never
    deadlock a session. A corrupt record is reclaimed inline by ``lease.acquire``.
  * **Boundary inclusive.** ``elapsed == ttl`` is stale (``>=``), and ``ttl == 0``
    is always stale.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

__all__ = ["is_stale", "is_stale_session"]

#: Fields a lease record must carry for staleness to be evaluable. Anything else
#: missing makes the record corrupt → stale (fail-open).
_REQUIRED_FIELDS: tuple[str, ...] = ("heartbeat", "ttl")


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def is_stale(
    data: dict[str, object] | None,
    *,
    clock: Callable[[], datetime] = _utcnow,
    pid_probe: Callable[[int], bool] | None = None,
    session_exists: Callable[[str], bool] | None = None,
) -> bool:
    """Return ``True`` if a lease record is stale (absent, corrupt, or TTL-expired).

    Parameters
    ----------
    data:
        The deserialized lease record, or ``None`` when no record exists.
    clock:
        Injectable wall-clock; defaults to UTC ``now``. Tests inject a
        ``FakeClock`` so the predicate body contains zero direct ``datetime.now``
        calls.
    pid_probe:
        Accepted for injection-signature compatibility only. **Never used**
        (OQ-1: liveness is TTL-only, no PID).
    session_exists:
        Accepted for injection-signature compatibility only. Reserved for a
        future fast-path identity check; not consulted by the TTL rule.

    Returns
    -------
    bool
        ``True`` when the record should be treated as reclaimable.
    """
    if data is None:
        return True

    for field in _REQUIRED_FIELDS:
        if field not in data:
            logger.warning("lease record missing required field %r; treating as stale", field)
            return True

    try:
        ttl = int(data["ttl"])  # type: ignore[call-overload]
    except (TypeError, ValueError):
        logger.warning("lease record has non-integer ttl %r; treating as stale", data["ttl"])
        return True

    heartbeat_raw = data["heartbeat"]
    if not isinstance(heartbeat_raw, str) or not heartbeat_raw:
        logger.warning("lease record has empty/non-string heartbeat; treating as stale")
        return True

    try:
        heartbeat_dt = datetime.fromisoformat(heartbeat_raw.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("lease record heartbeat %r is unparseable; treating as stale", heartbeat_raw)
        return True

    if heartbeat_dt.tzinfo is None:
        heartbeat_dt = heartbeat_dt.replace(tzinfo=UTC)

    elapsed = (clock() - heartbeat_dt).total_seconds()
    return bool(elapsed >= ttl)


def is_stale_session(last_seen_at: str, ttl_seconds: int) -> bool:
    """Return ``True`` if a session's ``last_seen_at`` is beyond its TTL.

    Single source of truth for session-staleness evaluation in both the
    Kanban view (``panel/views/kanban.py``) and any other consumer that
    needs to classify a session file as stale.

    Boundary semantics: uses ``>`` (strictly greater than) to match the
    original ``_is_stale`` behaviour in ``kanban.py``.

    Parameters
    ----------
    last_seen_at:
        ISO-8601 timestamp string (``Z`` suffix supported).  An empty or
        missing value is treated as *not stale* (fail-safe default).
    ttl_seconds:
        Session time-to-live in seconds.

    Returns
    -------
    bool
        ``True`` when the session should be considered expired/stale.
    """
    if not last_seen_at:
        return False
    try:
        last_seen_dt = datetime.fromisoformat(last_seen_at.replace("Z", "+00:00"))
        elapsed = (datetime.now(tz=UTC) - last_seen_dt).total_seconds()
        return bool(elapsed > ttl_seconds)
    except Exception:  # noqa: BLE001
        return False
