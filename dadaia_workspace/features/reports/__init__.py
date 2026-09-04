"""Reports feature: the ``dadaia reports validate|doctor`` surface.

Handoff discovery, schema-version routing, artifact-path resolution and validation live in
:mod:`dadaia_workspace.core.handoff_index` — the one module several mutually-independent
feature packages import directly, never duplicated per reader. The CLI is
``cli/commands/reports.py``; wiring is resolved in :mod:`dadaia_workspace.container`.
"""
