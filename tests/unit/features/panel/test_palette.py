"""Tests for canonical brand PALETTE and CSS token discipline.

Spec: dadaia-workspace-brand-identity-v1 SPEC.md.

T-P5-01: PALETTE and PANEL_CSS removed from _assets.py. PALETTE is defined
inline here (spec values are load-bearing). PANEL_CSS is assembled from slices.
"""

from __future__ import annotations

import re

from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS
from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS
from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

PANEL_CSS = TOKENS_CSS + STRUCTURE_CSS + AGENTS_CSS + WORKFLOWS_CSS + SESSIONS_CSS

PALETTE: dict[str, str] = {
    "accent": "#9cddc8",
    "accent_secondary": "#bfd8ad",
    "warning_bg": "#ddd9ab",
    "alert": "#f7af63",
    "cost": "#633d2e",
}


def test_palette_has_five_canonical_keys() -> None:
    assert set(PALETTE.keys()) == {"accent", "accent_secondary", "warning_bg", "alert", "cost"}


def test_palette_values_are_canonical_hex() -> None:
    assert PALETTE["accent"] == "#9cddc8"
    assert PALETTE["accent_secondary"] == "#bfd8ad"
    assert PALETTE["warning_bg"] == "#ddd9ab"
    assert PALETTE["alert"] == "#f7af63"
    assert PALETTE["cost"] == "#633d2e"


def test_palette_hex_only_in_token_definitions() -> None:
    """Each PALETTE hex appears only in --color-* definitions or var(...) fallbacks.

    The fallback form `var(--color-X, #hex)` is required by D-AM-22 (agent-monitoring-v1)
    so the panel renders correctly even if brand-identity tokens are missing.
    """
    pattern = re.compile(
        r"(--color-[a-z-]+\s*:\s*|var\(--color-[a-z-]+\s*,\s*)",
    )
    for hex_value in PALETTE.values():
        occurrences = [line for line in PANEL_CSS.splitlines() if hex_value.lower() in line.lower()]
        for line in occurrences:
            assert pattern.search(line), (
                f"hex {hex_value} found outside token definition or var() fallback: {line!r}"
            )
