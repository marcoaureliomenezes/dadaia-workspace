"""Fragment-driven lifecycle workflow bodies (WS-5+).

Each module here implements one workflow's §6.1 step sequence as a Python-owned
procedure: Python owns step order and gate decisions, while each model step's prompt
is assembled from a fragment bundle + the dynamically selected context + the output
schema + a discrete ``(harness, model)`` selection. This replaces the generic
``"Run the {label} step"`` suffix for the migrated workflows.
"""

from __future__ import annotations

from dadaia_workspace.features.lifecycle.workflows._deferred import (
    DEFERRED_WORKFLOWS,
    audit,
    bug_report,
    research,
)
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    BacklogDefinitionResult,
    BacklogDefinitionWorkflow,
    BacklogDemand,
    BacklogStepResult,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    ReleaseDefinitionResult,
    ReleaseDefinitionWorkflow,
    ReleaseStepResult,
)

__all__ = [
    "DEFERRED_WORKFLOWS",
    "BacklogDefinitionResult",
    "BacklogDefinitionWorkflow",
    "BacklogDemand",
    "BacklogStepResult",
    "ReleaseDefinitionResult",
    "ReleaseDefinitionWorkflow",
    "ReleaseStepResult",
    "audit",
    "bug_report",
    "research",
]
