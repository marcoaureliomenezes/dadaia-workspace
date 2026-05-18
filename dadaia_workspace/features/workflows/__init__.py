"""features/workflows — WorkflowsService and DTOs.

Public API:
    WorkflowsService   — wraps MarkdownWorkflowStore; mtime-cached list + detail
    WorkflowSummaryDTO — card summary (no stages[], no diagram_svg); per SPEC §5.3
    WorkflowDetailDTO  — full detail with stages[] + diagram_svg; per SPEC §5.4
    StageDTO           — per-stage shape used in WorkflowDetailDTO.stages
"""

from dadaia_workspace.features.workflows.service import (
    StageDTO,
    WorkflowDetailDTO,
    WorkflowSummaryDTO,
    WorkflowsService,
)

__all__ = [
    "StageDTO",
    "WorkflowDetailDTO",
    "WorkflowSummaryDTO",
    "WorkflowsService",
]
