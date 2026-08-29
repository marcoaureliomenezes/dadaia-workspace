"""Reports feature: agent-comms report/handoff behaviors as flat submodules.

* :mod:`~dadaia_workspace.features.reports.next` — discover the next expected
  agent handoff for the active release.
* :mod:`~dadaia_workspace.features.reports.retention` — TTL cleanup of workspace
  report/handoff runtime state.

Handoff discovery, schema-version routing, artifact-path resolution and validation
(formerly this package's ``validation.py``, release 0.5.1 K6) now live in
:mod:`dadaia_workspace.core.handoff_index` (public facade:
:mod:`dadaia_workspace.features.handoff`) — the one module several mutually-independent
feature packages read through, never duplicated per reader.

Submodules are imported directly (``features.reports.<submodule>``); wiring is
resolved in :mod:`dadaia_workspace.container`, never here.
"""
