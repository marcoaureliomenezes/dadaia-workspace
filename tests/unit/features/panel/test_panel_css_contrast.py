"""Structural CSS guard for panel decorative-color misuse.

Contrast ownership moved to ``test_theme_palettes.py`` (which parses the ACTUAL
served CSS, not hardcoded literals). This file keeps the one merged structural
guard that has no other owner: the accent/alert decorative tokens must never be
used as text `color:` (they are background/border-only), and every brand-token
`var()` usage carries a fallback value.
"""

from __future__ import annotations

import re

import pytest

from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS
from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

pytestmark = pytest.mark.unit

PANEL_CSS = TOKENS_CSS + STRUCTURE_CSS + WORKFLOWS_CSS + SESSIONS_CSS


def test_decorative_tokens_never_used_as_text_color_and_brand_tokens_have_fallbacks() -> None:
    # accent (#9cddc8) and alert (#f7af63) are background/border/outline-only —
    # never foreground text (would fail contrast on dark backgrounds).
    for hex_val, name in (("#9cddc8", "accent"), ("#f7af63", "alert")):
        matches = re.findall(
            rf"(?<!\bbackground-)color\s*:\s*{re.escape(hex_val)}", PANEL_CSS, re.IGNORECASE
        )
        assert not matches, (
            f"{name} ({hex_val}) used as text `color:` in PANEL_CSS — "
            f"it is a decorative token only. Found: {matches}"
        )

    # Every brand-identity var() usage outside :root carries a comma-separated
    # fallback, e.g. var(--color-cost, #633d2e), so the panel renders if the
    # token is unset.
    brand_tokens = [
        "--color-cost",
        "--color-warning-bg",
        "--color-alert",
        "--color-accent",
        "--color-accent-secondary",
        "--color-primary-ring",
        "--color-primary-bg",
    ]
    for token in brand_tokens:
        bare_pattern = re.compile(r"var\(" + re.escape(token) + r"\)", re.IGNORECASE)
        matches = bare_pattern.findall(PANEL_CSS)
        assert not matches, (
            f"Token `{token}` used without a fallback in PANEL_CSS: {matches}. "
            f"Add var({token}, <hex>) so the panel renders if the token is unset."
        )
