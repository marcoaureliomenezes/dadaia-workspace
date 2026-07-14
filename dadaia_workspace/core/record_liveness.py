"""Pure TTL predicate for disposable runtime records.

This helper performs no I/O and carries no concurrency authority. It is used only to
expire session metadata. Missing, corrupt, boundary-expired, and zero-TTL records are stale.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

__all__ = ["is_stale"]

_REQUIRED_FIELDS: tuple[str, ...] = ("heartbeat", "ttl")


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def is_stale(
    data: dict[str, object] | None,
    *,
    clock: Callable[[], datetime] = _utcnow,
) -> bool:
    """Return whether a record is absent, corrupt, or TTL-expired."""
    if data is None:
        return True

    for field in _REQUIRED_FIELDS:
        if field not in data:
            return True

    try:
        ttl = int(data["ttl"])  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return True

    heartbeat_raw = data["heartbeat"]
    if not isinstance(heartbeat_raw, str) or not heartbeat_raw:
        return True

    try:
        heartbeat_dt = datetime.fromisoformat(heartbeat_raw.replace("Z", "+00:00"))
    except ValueError:
        return True

    if heartbeat_dt.tzinfo is None:
        heartbeat_dt = heartbeat_dt.replace(tzinfo=UTC)

    return bool((clock() - heartbeat_dt).total_seconds() >= ttl)
