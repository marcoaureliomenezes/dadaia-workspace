"""Lifecycle-kernel tunables — one home for live timing (and sizing) constants.

This module is the **single source of truth**: pure constants, **zero I/O** (no ``os``,
``subprocess``, ``pathlib``, ``time`` — it imports nothing). It lives in ``core`` because
core is the bottom layer every other layer may legally import (constitution §6); hooks,
features, and cli all hold a legal edge to it. An import-linter contract pins the one-way
edge (kernel modules → tunables; never the reverse).

Retired lease/CAS constants are intentionally absent; no tunable in this module can make a workspace operation wait or block.
"""

from __future__ import annotations

__all__ = [
    "BACKLOG_SCRIPT",
    "DADAIA_BIN",
    "RECONCILER_THROTTLE_TTL_SECONDS",
    "SENTINEL_GC_TTL_SECONDS",
    "SESSION_GC_TTL_SECONDS",
]

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
#: BEFORE any subprocess is spawned. Consumed by ``hooks/sdd_post_gate.py`` (TG-5) and, on
#: the same cadence, gates the ONE GC reaper's call (0.4.7 FR6b:
#: ``features.spec_context.doctor.reap``).
RECONCILER_THROTTLE_TTL_SECONDS: int = 30

#: The one spelling of the workspace CLI every ``fix:`` line names — the venv-rooted
#: relative path the venv guard accepts (``hooks/venv_guard``). One home, so a refusal
#: can never teach an agent a command the guard will block.
DADAIA_BIN: str = ".dadaia/.venv/bin/dadaia"

#: The backlog ledger's ONE writer since 0.4.7 c7 — every `fix:` naming a backlog
#: repair names the script that can perform it, never a retired CLI verb.
BACKLOG_SCRIPT: str = "python3 .agents/skills/dd-backlog-definition/scripts/backlog.py"
