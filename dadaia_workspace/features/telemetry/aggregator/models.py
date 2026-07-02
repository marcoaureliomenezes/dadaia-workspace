"""Backward-compatible re-export shim for telemetry aggregator models.

The canonical definitions moved to ``dadaia_workspace.core.models.telemetry``
(NEW-01 / AR-03 boundary) so the panel view layer can depend on core types
instead of importing this feature module. Every existing
``from dadaia_workspace.features.telemetry.aggregator.models import X`` keeps
working through this shim.
"""

from __future__ import annotations

from dadaia_workspace.core.models.telemetry import (
    AgentListResult,
    AgentSummary,
    ContextBreakdown,
    RecentSession,
    SessionAggregate,
    SessionDetail,
    SessionListResult,
    SessionRow,
    TokenTotals,
    TopAgent,
    WorkflowListResult,
    WorkflowSummary,
)

__all__ = [
    "AgentListResult",
    "AgentSummary",
    "ContextBreakdown",
    "RecentSession",
    "SessionAggregate",
    "SessionDetail",
    "SessionListResult",
    "SessionRow",
    "TokenTotals",
    "TopAgent",
    "WorkflowListResult",
    "WorkflowSummary",
]
