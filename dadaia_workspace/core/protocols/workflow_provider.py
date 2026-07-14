"""WorkflowProvider Protocol for the governed Python lifecycle catalog."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from dadaia_workspace.features.lifecycle.governed_catalog import DadaiaWorkflowDTO


class WorkflowProvider(Protocol):
    """Read surface consumed by panel views."""

    def list_dadaia_workflows(self) -> list["DadaiaWorkflowDTO"]: ...

    def get_dadaia_workflow(self, name: str) -> "DadaiaWorkflowDTO | None": ...
