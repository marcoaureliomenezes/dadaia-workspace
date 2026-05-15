"""WorkflowStore protocol — reads workflow definitions from staged assets."""

from typing import Protocol

from dadaia_workspace.core.models.workflow import WorkflowDefinition


class WorkflowStore(Protocol):
    def list(self) -> tuple[WorkflowDefinition, ...]: ...
    def get(self, name: str) -> WorkflowDefinition: ...
    def validate(self, name: str) -> tuple[str, ...]: ...
