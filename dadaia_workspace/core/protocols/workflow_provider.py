"""WorkflowProvider Protocol — workflow summary enumeration for the panel."""

from typing import Protocol

from dadaia_workspace.core.models.workflow import WorkflowSummaryDTO


class WorkflowProvider(Protocol):
    """Minimum read surface that PanelService requires from the workflows feature."""

    def list_summaries(self) -> list[WorkflowSummaryDTO]: ...
