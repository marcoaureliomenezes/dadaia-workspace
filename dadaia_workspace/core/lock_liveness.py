"""Pure liveness predicate for the single-record TTL-lease (v0.1.6).

This is the *only* place ``(now - heartbeat) >= ttl`` is evaluated. It is a pure
model-layer function: zero I/O, stdlib-only imports, and every time/process/session
seam is injected so callers (and tests) stay deterministic.

Design decisions (state-model redesign, OQ-1; PID lesson restored WS-R2 FR-R2-03):
  * **TTL is the floor; PID is the veto (WS-R2).** The TTL rule decides reclaimability
    on its own, but when a record carries a ``pid`` and an injected ``pid_probe`` reports
    that pid is **still alive**, a TTL-expired record is treated as *live* (NOT stale) —
    this is the no-steal half: a foreign session that is genuinely still running keeps its
    lease past the heartbeat TTL, so ``lease.acquire`` BLOCKs instead of taking over. When
    ``pid_probe`` is ``None`` (no platform liveness, or the record has no ``pid``), the
    predicate falls back to TTL-only exactly as before — cross-platform safe, no regression.
    The probe is **only consulted to keep an otherwise-stale record alive**; it can never
    make a TTL-fresh record stale, and a dead/absent pid yields the plain TTL verdict
    (TTL-stale ⇒ reclaimable ⇒ TAKEOVER).
  * **Fail-open on corrupt.** A record that is absent, missing required fields, or
    has an unparseable heartbeat is treated as *stale* (acquirable), never as a
    live lock. This is the operator's overriding mandate: the lease must never
    deadlock a session. A corrupt record is reclaimed inline by ``lease.acquire``.
    A probe that itself raises is swallowed → fall back to the TTL verdict (never
    deadlock on a probe bug).
  * **Boundary inclusive.** ``elapsed == ttl`` is stale (``>=``), and ``ttl == 0``
    is always stale.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

__all__ = ["is_stale"]

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
    active_release: str | None = None,
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
        Optional liveness callable ``(pid: int) -> bool`` (WS-R2 FR-R2-03). When the
        record carries an integer ``pid`` and this probe reports it **alive**, an
        otherwise TTL-expired record is treated as *live* (returns ``False``) so a
        foreign holder that is still running is never taken over. ``None`` (default) ⇒
        TTL-only behavior, unchanged — the cross-platform fallback for hosts without a
        liveness seam, and for legacy records that carry no ``pid``. The probe is wired
        from ``hooks/sdd_gate.py`` via the container's ``OsProcessProbe`` (``features``
        never imports the adapter). A dead/absent pid, or a probe that raises, yields the
        plain TTL verdict.
    session_exists:
        Accepted for injection-signature compatibility only. Reserved for a
        future fast-path identity check; not consulted by the TTL rule.
    active_release:
        The context's live ACTIVE release id (T-43-10, bug
        ``lease-pid-veto-ignores-archived-release-blocks-next-release``). When provided and
        the TTL-expired record's ``release`` field is a non-empty string that **differs**
        from it, the lease is pinned to a non-ACTIVE (closed/archived) release — semantically
        dead, the holder is provably done with it — and is reclaimable **regardless of
        holder-pid liveness** (the pid-veto is bypassed). The pid-veto is retained ONLY when
        the record's ``release`` equals ``active_release``, i.e. a session genuinely mutating
        the current release is still never stolen. ``None`` (default) ⇒ the legacy
        release-agnostic behavior, full backward-compat (pid-veto applies as before).

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
    ttl_stale = bool(elapsed >= ttl)
    if not ttl_stale:
        return False

    # Release-aware reclaim (T-43-10, bug lease-pid-veto-ignores-archived-release-blocks-
    # next-release). A TTL-expired lease pinned to a release that is NOT the context's live
    # ACTIVE release is semantically dead — the holder is provably done with that release —
    # so it is reclaimable REGARDLESS of holder-pid liveness. This BYPASSES the pid-veto below
    # so an idle-but-alive session that finished an archived release can no longer deadlock the
    # next release. The pid-veto is retained ONLY for a lease pinned to the live ACTIVE release
    # (record.release == active_release), or when active_release is None (legacy path).
    if active_release is not None:
        record_release = data.get("release")
        if isinstance(record_release, str) and record_release and record_release != active_release:
            logger.info(
                "lease record release %r != active release %r; reclaimable despite holder pid "
                "(archived-release lease, T-43-10)",
                record_release,
                active_release,
            )
            return True

    # TTL says reclaimable. WS-R2 FR-R2-03: veto the takeover when the holder process is
    # demonstrably still alive. Only consulted on the TTL-stale branch — a fresh record is
    # already live above, so the probe can never *create* staleness, only suppress it.
    if pid_probe is None:
        return True
    pid = data.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        return True  # legacy/absent pid ⇒ no veto ⇒ TTL verdict (reclaimable).
    try:
        alive = pid_probe(pid)
    except Exception:  # noqa: BLE001 — a probe bug must never deadlock; fall back to TTL.
        logger.warning("lease pid_probe raised for pid %r; falling back to TTL verdict", pid)
        return True
    if alive:
        logger.info(
            "lease record TTL-expired but holder pid %d is alive; not stale (no takeover)", pid
        )
        return False
    return True
