"""Fragment-driven lifecycle workflow bodies (WS-5+).

Each module here implements one workflow's §6.1 step sequence as a Python-owned
procedure: Python owns step order and gate decisions, while each model step's prompt
is assembled from a fragment bundle + the dynamically selected context + the output
schema + a discrete ``(harness, model)`` selection. This replaces the generic
``"Run the {label} step"`` suffix for the migrated workflows.

As of v0.1.30 Wave E (T-30-E-01..04) the ``audit`` / ``research`` / ``bug_report``
workflows ship real fragment+gate bodies (mirroring ``release_definition``) and have left
the deferred set — :data:`DEFERRED_WORKFLOWS` is now empty.
"""

from __future__ import annotations

from dadaia_workspace.features.lifecycle.workflows._deferred import DEFERRED_WORKFLOWS
from dadaia_workspace.features.lifecycle.workflows.audit import (
    AuditResult,
    AuditStepResult,
    AuditWorkflow,
)
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    BacklogDefinitionResult,
    BacklogDefinitionWorkflow,
    BacklogDemand,
    BacklogStepResult,
)
from dadaia_workspace.features.lifecycle.workflows.bug_report import (
    BugReportResult,
    BugReportStepResult,
    BugReportWorkflow,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    ReleaseDefinitionResult,
    ReleaseDefinitionWorkflow,
    ReleaseStepResult,
)
from dadaia_workspace.features.lifecycle.workflows.research import (
    ResearchResult,
    ResearchStepResult,
    ResearchWorkflow,
)

__all__ = [
    "DEFERRED_WORKFLOWS",
    "AuditResult",
    "AuditStepResult",
    "AuditWorkflow",
    "BacklogDefinitionResult",
    "BacklogDefinitionWorkflow",
    "BacklogDemand",
    "BacklogStepResult",
    "BugReportResult",
    "BugReportStepResult",
    "BugReportWorkflow",
    "ReleaseDefinitionResult",
    "ReleaseDefinitionWorkflow",
    "ReleaseStepResult",
    "ResearchResult",
    "ResearchStepResult",
    "ResearchWorkflow",
]
