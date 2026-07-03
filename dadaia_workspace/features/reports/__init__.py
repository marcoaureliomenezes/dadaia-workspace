"""Reports feature: agent-comms report/handoff behaviors as flat submodules.

One package for the three former top-level ``reports_*`` packages (v0.1.55 FR3):

* :mod:`~dadaia_workspace.features.reports.next` — discover the next expected
  agent handoff for the active release.
* :mod:`~dadaia_workspace.features.reports.retention` — TTL cleanup of workspace
  report/handoff runtime state.
* :mod:`~dadaia_workspace.features.reports.validation` — stdlib-only handoff JSON
  validation.

Submodules are imported directly (``features.reports.<submodule>``); wiring is
resolved in :mod:`dadaia_workspace.container`, never here.
"""
