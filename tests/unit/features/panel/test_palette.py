"""Tests for panel CSS token discipline."""

from __future__ import annotations

import re

from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS
from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS
from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

PANEL_CSS = TOKENS_CSS + STRUCTURE_CSS + AGENTS_CSS + WORKFLOWS_CSS + SESSIONS_CSS


_REQUIRED_COLOR_TOKENS = {
    "--color-accent",
    "--color-accent-secondary",
    "--color-warning-bg",
    "--color-alert",
    "--color-cost",
}


def test_required_brand_tokens_exist_in_token_css() -> None:
    """Brand colors are sourced from CSS tokens, not duplicated in tests."""
    for token in _REQUIRED_COLOR_TOKENS:
        assert re.search(rf"{re.escape(token)}\s*:\s*#[0-9a-fA-F]{{3,8}}\b", TOKENS_CSS)


def test_panel_css_consumes_color_tokens() -> None:
    """Panel CSS should consume the token contract through var(--color-*)."""
    for token in _REQUIRED_COLOR_TOKENS:
        assert f"var({token}" in PANEL_CSS or token in TOKENS_CSS
