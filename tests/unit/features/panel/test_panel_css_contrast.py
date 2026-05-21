"""WCAG contrast ratio tests for brand-identity-v1 tokens in PANEL_CSS (T-AM-19).

Reuses the _luminance/_contrast helpers from test_contrast.py (same algorithm,
inlined here so this module is self-contained and does not create a circular
import between test modules).

Assertions cover:
  - Text-on-background pairs required by D-AM-22 / SPEC § Threat matrix T2.
  - Structural assertions that palette colors are NOT used as text `color:`
    values where they would fail contrast (accent / alert are decorative only).
"""

from __future__ import annotations

import re

from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS
from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS
from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

# T-P5-01: PALETTE and PANEL_CSS removed from _assets.py. Inline them here.
PANEL_CSS = TOKENS_CSS + STRUCTURE_CSS + AGENTS_CSS + WORKFLOWS_CSS + SESSIONS_CSS

PALETTE: dict[str, str] = {
    "accent": "#9cddc8",
    "accent_secondary": "#bfd8ad",
    "warning_bg": "#ddd9ab",
    "alert": "#f7af63",
    "cost": "#633d2e",
}

# ---------------------------------------------------------------------------
# WCAG relative-luminance + contrast-ratio helpers (stdlib only)
# ---------------------------------------------------------------------------


def _luminance(hex_color: str) -> float:
    """Return the WCAG relative luminance of a hex colour string."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def _channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast(fg: str, bg: str) -> float:
    """Return the WCAG contrast ratio between two hex colours."""
    l1 = _luminance(fg)
    l2 = _luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Contrast assertions (WCAG AA = 4.5:1; AAA = 7:1)
# ---------------------------------------------------------------------------


def test_text_on_accent_aa() -> None:
    """Dark text on accent background meets WCAG AA (defensive; accent is decorative)."""
    # accent is used as background/border, not as text. Still verify dark text would pass.
    assert _contrast("#222", "#9cddc8") >= 4.5


def test_text_on_accent_secondary_aa() -> None:
    """Dark text on accent_secondary background meets WCAG AA."""
    assert _contrast("#222", "#bfd8ad") >= 4.5


def test_text_on_warning_bg_aa() -> None:
    """Dark brown text on warning_bg background meets WCAG AA."""
    assert _contrast("#3d3600", "#ddd9ab") >= 4.5


def test_cost_on_white_aaa() -> None:
    """Cost colour on white meets WCAG AAA (7:1) — topbar wordmark."""
    assert _contrast("#633d2e", "#ffffff") >= 7.0


def test_dark_on_alert_aa() -> None:
    """Dark text on alert badge background meets WCAG AA.

    Note: white (#fff) on #f7af63 amber is only ~1.86:1 and fails WCAG AA.
    The CSS uses #3d2a00 (dark brown) for ~6.3:1 contrast (AA-compliant).
    This test asserts the actual CSS text colour used on the alert badge.
    """
    assert _contrast("#3d2a00", "#f7af63") >= 4.5


# ---------------------------------------------------------------------------
# Structural assertions: palette tokens used only as background/border, not text
# ---------------------------------------------------------------------------


def test_accent_not_used_as_text_color() -> None:
    """`#9cddc8` must not appear as a CSS `color:` property value in PANEL_CSS.

    It is used only as background / outline / border — never as foreground text.
    This guards against a regression where the decorative accent is accidentally
    used as text (which would fail contrast on dark backgrounds).
    """
    matches = re.findall(r"(?<!\bbackground-)color\s*:\s*#9cddc8", PANEL_CSS, re.IGNORECASE)
    assert not matches, (
        f"accent (#9cddc8) used as text `color:` in PANEL_CSS — "
        f"it is a decorative token only. Found: {matches}"
    )


def test_alert_not_used_as_text_color() -> None:
    """`#f7af63` must not appear as a CSS `color:` property value in PANEL_CSS.

    It is used only as background (alert badge) — never as foreground text.
    """
    matches = re.findall(r"(?<!\bbackground-)color\s*:\s*#f7af63", PANEL_CSS, re.IGNORECASE)
    assert not matches, (
        f"alert (#f7af63) used as text `color:` in PANEL_CSS — "
        f"it is a decorative token only. Found: {matches}"
    )


# ---------------------------------------------------------------------------
# Palette completeness: all PALETTE values have a CSS token entry
# ---------------------------------------------------------------------------


def test_palette_tokens_present_in_root() -> None:
    """Every PALETTE hex value appears in the :root block of PANEL_CSS."""
    for name, hex_val in PALETTE.items():
        assert hex_val in PANEL_CSS, (
            f"PALETTE['{name}'] = {hex_val!r} is not present in PANEL_CSS — "
            "missing brand token definition."
        )


def test_brand_tokens_have_fallbacks() -> None:
    """All brand-identity-v1 var() usages in PANEL_CSS include a fallback value.

    Checks that every `var(--color-cost)`, `var(--color-warning-bg)`,
    `var(--color-alert)`, `var(--color-accent)`, and `var(--color-accent-secondary)`
    call outside of `:root` has a comma-separated fallback, e.g.
    `var(--color-cost, #633d2e)`.

    The `:root` block itself only contains *definitions* (no `var()` calls), so
    the regex only needs to inspect the non-:root portion.
    """
    brand_tokens = [
        "--color-cost",
        "--color-warning-bg",
        "--color-alert",
        "--color-accent",
        "--color-accent-secondary",
        "--color-primary-ring",
        "--color-primary-bg",
    ]
    # Bare var(--color-X) with no comma fallback.
    for token in brand_tokens:
        bare_pattern = re.compile(
            r"var\(" + re.escape(token) + r"\)",  # var(--color-X) with NO fallback
            re.IGNORECASE,
        )
        matches = bare_pattern.findall(PANEL_CSS)
        assert not matches, (
            f"Token `{token}` used without a fallback in PANEL_CSS: {matches}. "
            "Add var({token}, <hex>) so the panel renders if the token is unset."
        )
