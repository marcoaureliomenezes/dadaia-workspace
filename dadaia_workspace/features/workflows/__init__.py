"""features/workflows — WorkflowsService, DTOs, and DAG renderer.

Public API:
    WorkflowsService   — wraps MarkdownWorkflowStore; mtime-cached list + detail
    WorkflowSummaryDTO — card summary (no stages[], no diagram_svg); per SPEC §5.3
    WorkflowDetailDTO  — full detail with stages[] + diagram_svg; per SPEC §5.4
    StageDTO           — per-stage shape used in WorkflowDetailDTO.stages
    render_dag_svg     — pure function: list[StageDTO] → SVG string (PR3-13)
"""

from dadaia_workspace.features.workflows.dag import render_dag_svg
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
    "render_dag_svg",
]
