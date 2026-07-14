"""Fragment-driven lifecycle workflow bodies (WS-5+).

Each module here implements one workflow's §6.1 step sequence as a Python-owned
procedure: Python owns step order and gate decisions, while each model step's prompt
is assembled from a fragment bundle + the dynamically selected context + the output
schema + a discrete ``(harness, model)`` selection. This replaces the generic
``"Run the {label} step"`` suffix for the migrated workflows.

The public workflow roster is backlog definition, release definition,
implementation plus reviews, and audit. Research and bug intake are part of backlog
definition; closure is part of implementation plus reviews.
"""

from __future__ import annotations

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
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    ReleaseDefinitionResult,
    ReleaseDefinitionWorkflow,
    ReleaseStepResult,
)

#: Deferred-workflow names, in catalog order. Empty since v0.1.30 Wave E — every workflow
#: now ships a real fragment+gate body. Kept as the declared seam the panel catalog and
#: tests read, so a future deferral is enumerated without a code change. Inlined here in
#: v0.1.53 when the standalone ``_deferred`` module was retired.
DEFERRED_WORKFLOWS: tuple[str, ...] = ()


__all__ = [
    "DEFERRED_WORKFLOWS",
    "AuditResult",
    "AuditStepResult",
    "AuditWorkflow",
    "BacklogDefinitionResult",
    "BacklogDefinitionWorkflow",
    "BacklogDemand",
    "BacklogStepResult",
    "ReleaseDefinitionResult",
    "ReleaseDefinitionWorkflow",
    "ReleaseStepResult",
]
