"""Shared fixtures for the panel unit-test cluster.

FR4 (v0.1.75): single-source the panel primary tab list here so a future tab
change (e.g. v0.1.77) edits ONE list and every DOM-contract test that walks
the tab/section/tabpanel set picks it up automatically.

v0.1.79 (panel agentic-layers reorg): 7 -> 6 primary tabs. The standalone
Sessions tab/section is REMOVED — the cost/telemetry dashboard relocates into
the "1º Agentic Layer" (subagents) tabpanel as a sub-section (still rendered
via ``#section-sessions``, just no longer a top-level ``.section``/tabpanel).
"Sub-agents" -> "1º Agentic Layer" (id stays ``tab-subagents`` /
``section-subagents``); "Workflows" -> "2º Agentic Layer" (id stays
``tab-workflows`` / ``section-workflows``).
"""

from __future__ import annotations

# Canonical panel primary tab order, in the order they render (nav + section
# ids follow ``tab-<slug>`` / ``section-<slug>``). Keep this list in sync with
# ``dadaia_workspace/features/panel/views/index.py`` — it is the single
# consumption point for every surviving DOM-contract test in this cluster.
PANEL_PRIMARY_TABS: list[tuple[str, str]] = [
    ("memories", "Projects"),
    ("subagents", "1º Agentic Layer"),
    ("reports", "Reports"),
    ("academy", "Academy"),
    ("servers", "Servers"),
]

# Convenience derived views used across the surviving test files.
PANEL_PRIMARY_TAB_SLUGS: list[str] = [slug for slug, _label in PANEL_PRIMARY_TABS]
