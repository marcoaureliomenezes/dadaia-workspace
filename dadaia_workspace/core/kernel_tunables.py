"""Lifecycle-kernel tunables — one home for live timing (and sizing) constants.

This module is the **single source of truth**: pure constants, **zero I/O** (no ``os``,
``subprocess``, ``pathlib``, ``time`` — it imports nothing). It lives in ``core`` because
core is the bottom layer every other layer may legally import (constitution §6); hooks,
features, and cli all hold a legal edge to it. An import-linter contract pins the one-way
edge (kernel modules → tunables; never the reverse).

Retired lease/CAS constants are intentionally absent. Context concurrency is advisory
presence only; no tunable in this module can make a workspace operation wait or block.
"""

from __future__ import annotations

__all__ = [
    "LOG_ROTATION_MAX_BYTES",
    "PRESENCE_TTL_SECONDS",
    "RECONCILER_REAP_TTL_MULTIPLIER",
    "RECONCILER_THROTTLE_TTL_SECONDS",
    "SENTINEL_GC_TTL_SECONDS",
    "SESSION_GC_TTL_SECONDS",
]

#: Advisory presence heartbeat TTL. Expiry only removes a warning signal; it never grants,
#: revokes, or blocks write authority.
PRESENCE_TTL_SECONDS: int = 120

#: Age after which a once-per-session ctx-inject sentinel (``ctx-inject-fired-<sid>``) is
#: considered stale and GC'd at inject time. Generous (24 h) so a long-running live session
#: is never disturbed; the worst case is one redundant bootstrap re-injection.
SENTINEL_GC_TTL_SECONDS: int = 24 * 60 * 60

#: Default TTL (seconds) for a session record's graveyard GC when the record itself carries
#: no explicit ``ttl_seconds`` field (pre-heartbeat / legacy records). The doctor decays
#: bind/session records against ``last_seen_at`` using this floor.
SESSION_GC_TTL_SECONDS: int = 300

#: Throttle window (seconds) for the advisory working-tree reconciler (FR-W1-03). A second
#: PostToolUse invocation inside this window emits nothing and spawns no git child — checked
#: BEFORE any subprocess is spawned. Consumed by ``hooks/sdd_post_gate.py`` (TG-5).
RECONCILER_THROTTLE_TTL_SECONDS: int = 30

#: Multiplier applied to the base session/presence TTL when the ADVISORY reconciler (not
#: the manually-invoked ``dadaia doctor --fix`` graveyard GC, which reaps at exactly 1×TTL)
#: reaps a stale record on its own throttled cadence (FR26, T-043-41). The reconciler fires
#: on every PostToolUse call — far more often than an operator runs the doctor — so its own
#: reap threshold is deliberately N times more conservative: a session/presence record must
#: be stale N times over before the reconciler ever deletes it unattended, so a merely idle
#: (but still bound, still heartbeating) session is never at risk of being auto-reaped.
RECONCILER_REAP_TTL_MULTIPLIER: int = 3

#: FR27 (T-043-42): the "~1 MB" cap every ``.dadaia/logs/*.jsonl`` appender rotates at
#: (decimal MB, matching the SPEC's own wording). Not a timing constant like its
#: siblings above, but co-located here anyway — it is the same kind of thing (a single
#: kernel-owned tunable hooks/features/cli all hold a legal ``core`` edge to), and the
#: mechanism that reads it (``infrastructure/jsonl_log_rotation.py``) is I/O, so it
#: cannot live there itself (this module is the zero-I/O leaf; see the module
#: docstring).
LOG_ROTATION_MAX_BYTES: int = 1_000_000
