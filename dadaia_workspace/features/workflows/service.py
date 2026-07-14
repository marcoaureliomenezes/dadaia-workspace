"""Read service for the governed Python lifecycle workflow catalog."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from dadaia_workspace.features.workflows.dag import StageDTO

if TYPE_CHECKING:
    from dadaia_workspace.features.workflows.dadaia_catalog import DadaiaWorkflowDTO


class WorkflowsService:
    """Expose the sole authoritative workflow catalog to panel consumers."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root

    def list_dadaia_workflows(self) -> list[DadaiaWorkflowDTO]:
        """Return all four governed workflows in catalog order."""
        from dadaia_workspace.features.workflows.dadaia_catalog import list_dadaia_workflows

        return list_dadaia_workflows()

    def get_dadaia_workflow(self, name: str) -> DadaiaWorkflowDTO | None:
        """Return one governed workflow, or ``None`` when unknown."""
        from dadaia_workspace.features.workflows.dadaia_catalog import get_dadaia_workflow

        return get_dadaia_workflow(name)


__all__ = ["StageDTO", "WorkflowsService"]
