"""WorkflowProvider Protocol for the governed Python lifecycle catalog."""

from typing import Any, Protocol


class WorkflowProvider(Protocol):
    """Read surface consumed by panel views."""

    def list_dadaia_workflows(self) -> list[Any]: ...

    def get_dadaia_workflow(self, name: str) -> Any | None: ...
