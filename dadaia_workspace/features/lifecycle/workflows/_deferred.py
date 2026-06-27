"""Deferred workflow names (WS-6) — now empty.

This module historically scaffolded the ``audit`` / ``research`` / ``bug_report`` workflow
entry points as fail-loud stubs (each raised ``NotImplementedError``) while those bodies
were deferred. As of v0.1.30 Wave E (T-30-E-01..04) all three ship **real fragment+gate
workflow bodies**:

- :mod:`dadaia_workspace.features.lifecycle.workflows.audit`
- :mod:`dadaia_workspace.features.lifecycle.workflows.research`
- :mod:`dadaia_workspace.features.lifecycle.workflows.bug_report`

so they have **left** :data:`DEFERRED_WORKFLOWS` and their fail-loud stubs are removed
(``backlog_definition`` left earlier, in v0.1.26 R2). No workflow remains deferred, so this
set is now empty — it is kept (rather than deleted) as the single declared home of the
"deferred workflow" concept that the panel catalog and tests read.
"""

from __future__ import annotations

#: The deferred workflow names, in catalog order. Empty as of v0.1.30 Wave E — every
#: workflow now ships a real body. Kept as the declared seam the catalog iterates.
DEFERRED_WORKFLOWS: tuple[str, ...] = ()


__all__ = [
    "DEFERRED_WORKFLOWS",
]
