"""Governed workflow catalog service and DAG renderer.

Public API:
    WorkflowsService — reads the four Python-governed lifecycle workflows
    StageDTO         — minimal step shape consumed by the DAG renderer
    render_dag_svg   — pure function: list[StageDTO] → SVG string
"""

from dadaia_workspace.features.workflows.dag import StageDTO, render_dag_svg
from dadaia_workspace.features.workflows.service import WorkflowsService

__all__ = [
    "StageDTO",
    "WorkflowsService",
    "render_dag_svg",
]
