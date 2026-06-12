"""Lifecycle-kernel tunables — the single home for the workspace's timing constants.

FR-W4-05 (DP-1, v0.1.14). Before this module each kernel concern carried its own inline
magic number: the lease TTL in ``features/spec_context/lease.py``, the sentinel-orphan age
duplicated in ``lease.py`` AND ``spec_context/doctor.py``, the once-per-session sentinel GC
TTL in ``hooks/ctx_inject.py``, the CAS retry/back-off counts in ``lease.py``, and the
session-record GC default scattered across the doctor. A change to any of them risked
drift between the live path and its GC/diagnostic mirror.

This module is the **single source of truth**: pure constants, **zero I/O** (no ``os``,
``subprocess``, ``pathlib``, ``time`` — it imports nothing). It lives in ``core`` because
core is the bottom layer every other layer may legally import (constitution §6); hooks,
features, and cli all hold a legal edge to it. An import-linter contract pins the one-way
edge (kernel modules → tunables; never the reverse).

Each consumer imports the name it needs from here. ``lease.LEASE_TTL_SECONDS`` is retained
as a re-export for one release (deprecation note in that module) so external callers and
tests that import it keep working.
"""

from __future__ import annotations

__all__ = [
    "CAS_INITIAL_BACKOFF_SECONDS",
    "CAS_MAX_RETRIES",
    "LEASE_TTL_SECONDS",
    "RECONCILER_THROTTLE_TTL_SECONDS",
    "SENTINEL_GC_TTL_SECONDS",
    "SENTINEL_ORPHAN_AGE_SECONDS",
    "SESSION_GC_TTL_SECONDS",
]

#: Heartbeat TTL in seconds for the single-record context lease (OQ-1 operator decision
#: 2026-06-06, short heartbeat). A holder whose heartbeat ages past this is reclaimable
#: UNLESS its pid is still alive (pid-veto, ``core.lock_liveness.is_stale``). Every liveness
#: comparison references this constant — no inline magic number anywhere in the lease path.
LEASE_TTL_SECONDS: int = 120

#: A lease-acquire sentinel (``open(path, "x")``) older than this is an orphan — the process
#: was SIGKILLed between the O_EXCL CAS win and the record write. Both the lease (inline
#: cleanup) and the workspace doctor (SENTINEL-GC) measure against this same value.
SENTINEL_ORPHAN_AGE_SECONDS: float = 30.0

#: Age after which a once-per-session ctx-inject sentinel (``ctx-inject-fired-<sid>``) is
#: considered stale and GC'd at inject time. Generous (24 h) so a long-running live session
#: is never disturbed; the worst case is one redundant bootstrap re-injection.
SENTINEL_GC_TTL_SECONDS: int = 24 * 60 * 60

#: Default TTL (seconds) for a session record's graveyard GC when the record itself carries
#: no explicit ``ttl_seconds`` field (pre-heartbeat / legacy records). The doctor decays
#: bind/session records against ``last_seen_at`` using this floor.
SESSION_GC_TTL_SECONDS: int = 300

#: Maximum retry attempts for the lease's O_EXCL compare-and-swap on contention (the loop
#: runs ``range(CAS_MAX_RETRIES + 1)`` — one initial try plus this many retries).
CAS_MAX_RETRIES: int = 3

#: Initial exponential-backoff delay (seconds) between CAS retries.
CAS_INITIAL_BACKOFF_SECONDS: float = 0.1

#: Throttle window (seconds) for the advisory working-tree reconciler (FR-W1-03). A second
#: PostToolUse invocation inside this window emits nothing and spawns no git child — checked
#: BEFORE any subprocess is spawned. Consumed by ``hooks/sdd_post_gate.py`` (TG-5).
RECONCILER_THROTTLE_TTL_SECONDS: int = 30
