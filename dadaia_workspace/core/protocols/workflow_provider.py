"""WorkflowProvider Protocol for the governed Python lifecycle catalog.

Core is the bottom layer: it cannot name the concrete
``features.lifecycle.governed_catalog.DadaiaWorkflowDTO`` (that would invert the layer
direction). The provider surface is typed against ``object`` — consumers in features/
(panel views) receive the concrete DTOs at runtime and the concrete provider
implementations (``features.workflows.service``) satisfy this Protocol structurally.
"""

from collections.abc import Sequence
from typing import Protocol


class WorkflowProvider(Protocol):
    """Read surface consumed by panel views."""

    def list_dadaia_workflows(self) -> Sequence[object]: ...

    def get_dadaia_workflow(self, name: str) -> object | None: ...
