"""TelemetryService — skeleton for Phase 2. Wired in Phase 6 (T-AM-12)."""
from __future__ import annotations

from typing import Any


class TelemetryService:
    """Aggregate entry-point for telemetry: ingest, cache, and query.

    Dependencies are injected at construction time so that each can be
    swapped with a fake in tests (no mocks).

    Parameters
    ----------
    reader_factory:
        Callable that returns a list of reader instances for a given
        workspace root.  Implemented in P3/P4 (T-AM-06, T-AM-07).
    dao:
        TelemetryDao instance (store/dao.py).  Implemented in T-AM-04.
    aggregator:
        Aggregator/queries module handle.  Implemented in T-AM-11.
    pricing_table:
        PRICING_TABLE dict from features/telemetry/pricing.py (T-AM-10).
    workspace_root:
        pathlib.Path pointing to the workspace root (~/.dadaia or the
        local repo root, depending on context).
    spec_context_service:
        SpecContextService instance for cwd→context resolution (T-AM-11).
    """

    def __init__(
        self,
        reader_factory: Any,
        dao: Any,
        aggregator: Any,
        pricing_table: Any,
        workspace_root: Any,
        spec_context_service: Any,
    ) -> None:
        pass
