"""Shared fixtures for the panel unit-test cluster.

FR4 (v0.1.75): single-source the panel primary tab list here so a future tab
change (e.g. v0.1.77) edits ONE list and every DOM-contract test that walks
the tab/section/tabpanel set picks it up automatically.
"""

from __future__ import annotations

# Canonical panel primary tab order, in the order they render (nav + section
# ids follow ``tab-<slug>`` / ``section-<slug>``). Keep this list in sync with
# ``dadaia_workspace/features/panel/views/index.py`` — it is the single
# consumption point for every surviving DOM-contract test in this cluster.
PANEL_PRIMARY_TABS: list[tuple[str, str]] = [
    ("memories", "Projects"),
    ("workflows", "Workflows"),
    ("subagents", "Sub-agents"),
    ("sessions", "Sessions"),
    ("reports", "Reports"),
    ("academy", "Academy"),
    ("servers", "Servers"),
]

# Convenience derived views used across the surviving test files.
PANEL_PRIMARY_TAB_SLUGS: list[str] = [slug for slug, _label in PANEL_PRIMARY_TABS]
