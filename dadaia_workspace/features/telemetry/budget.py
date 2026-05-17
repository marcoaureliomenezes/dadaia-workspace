"""Telemetry read-budget constants. See PLAN.md § Performance budget."""
from __future__ import annotations

MAX_BYTES_PER_FILE_PER_CYCLE: int = 4 * 1024 * 1024   # 4 MB — devops T4
MAX_LINE_LENGTH: int = 64 * 1024                       # 64 KB — devops T4
MAX_EVENTS_PER_CYCLE: int = 10_000                     # devops T4
CACHE_TTL_SECONDS: int = 30                            # architect D5
PRICING_STALENESS_THRESHOLD_DAYS: int = 90             # devops + frontend D-10
MAX_TOKEN_COUNT_PER_EVENT: int = 2_000_000             # T7 suspect bound (D-AM-19)
