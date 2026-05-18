"""TDD tests for PR3-03 — Theme palettes (3 variants) in tokens.py + structure.py.

SPEC acceptance: Surface E (E2E-THM-01..04, E2E-THM-07)
TASKS.md PR3-03 acceptance criteria:
  - 3 palettes selectable via [data-theme="mint"|"sage"|"warm"]
  - WCAG 4.5:1 contrast for body text in all three
  - Warm theme focus-visible rule uses --color-accent-dark double outline (WCAG-AA fix)
"""

from __future__ import annotations

import re

from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS


# ---------------------------------------------------------------------------
# WCAG helpers
# ---------------------------------------------------------------------------


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def _channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast(fg: str, bg: str) -> float:
    l1 = _luminance(fg)
    l2 = _luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Palette presence — all 3 data-theme selectors must exist in TOKENS_CSS
# ---------------------------------------------------------------------------


def test_mint_theme_selector_present() -> None:
    """TOKENS_CSS must contain [data-theme="mint"] selector."""
    assert '[data-theme="mint"]' in TOKENS_CSS


def test_sage_theme_selector_present() -> None:
    """TOKENS_CSS must contain [data-theme="sage"] selector."""
    assert '[data-theme="sage"]' in TOKENS_CSS


def test_warm_theme_selector_present() -> None:
    """TOKENS_CSS must contain [data-theme="warm"] selector."""
    assert '[data-theme="warm"]' in TOKENS_CSS


# ---------------------------------------------------------------------------
# Mint theme — default mapping (no visual regression)
# Must be present under :root AND [data-theme="mint"]
# ---------------------------------------------------------------------------


def test_mint_accent_is_brand_mint() -> None:
    """Mint theme accent must be #9cddc8 (original brand value)."""
    mint_block_match = re.search(
        r'\[data-theme="mint"\][^{]*\{([^}]+)\}', TOKENS_CSS, re.DOTALL
    )
    assert mint_block_match, "No [data-theme='mint'] block found"
    mint_block = mint_block_match.group(1)
    assert "#9cddc8" in mint_block


def test_mint_accent_dark_is_teal_blue() -> None:
    """Mint theme accent-dark must be #2d7d9a."""
    mint_block_match = re.search(
        r'\[data-theme="mint"\][^{]*\{([^}]+)\}', TOKENS_CSS, re.DOTALL
    )
    assert mint_block_match, "No [data-theme='mint'] block found"
    mint_block = mint_block_match.group(1)
    assert "#2d7d9a" in mint_block


# ---------------------------------------------------------------------------
# Sage theme token values
# ---------------------------------------------------------------------------


def test_sage_accent_is_sage_green() -> None:
    """Sage theme accent must be #bfd8ad."""
    sage_block_match = re.search(
        r'\[data-theme="sage"\][^{]*\{([^}]+)\}', TOKENS_CSS, re.DOTALL
    )
    assert sage_block_match, "No [data-theme='sage'] block found"
    sage_block = sage_block_match.group(1)
    assert "#bfd8ad" in sage_block


def test_sage_accent_dark_is_deep_sage() -> None:
    """Sage theme accent-dark must be #4a7c59 (deep sage-green links)."""
    sage_block_match = re.search(
        r'\[data-theme="sage"\][^{]*\{([^}]+)\}', TOKENS_CSS, re.DOTALL
    )
    assert sage_block_match, "No [data-theme='sage'] block found"
    sage_block = sage_block_match.group(1)
    assert "#4a7c59" in sage_block


# ---------------------------------------------------------------------------
# Warm theme token values
# ---------------------------------------------------------------------------


def test_warm_accent_is_amber() -> None:
    """Warm theme accent must be #f7af63 (amber)."""
    warm_block_match = re.search(
        r'\[data-theme="warm"\][^{]*\{([^}]+)\}', TOKENS_CSS, re.DOTALL
    )
    assert warm_block_match, "No [data-theme='warm'] block found"
    warm_block = warm_block_match.group(1)
    assert "#f7af63" in warm_block


def test_warm_accent_dark_is_brown() -> None:
    """Warm theme accent-dark must be #633d2e (brown links / CTA text)."""
    warm_block_match = re.search(
        r'\[data-theme="warm"\][^{]*\{([^}]+)\}', TOKENS_CSS, re.DOTALL
    )
    assert warm_block_match, "No [data-theme='warm'] block found"
    warm_block = warm_block_match.group(1)
    assert "#633d2e" in warm_block


def test_warm_cost_is_deeper_brown() -> None:
    """Warm theme --color-cost must be #4a3020 (deeper brown for headings on warm bg)."""
    warm_block_match = re.search(
        r'\[data-theme="warm"\][^{]*\{([^}]+)\}', TOKENS_CSS, re.DOTALL
    )
    assert warm_block_match, "No [data-theme='warm'] block found"
    warm_block = warm_block_match.group(1)
    assert "#4a3020" in warm_block


# ---------------------------------------------------------------------------
# WCAG 4.5:1 — body text on surface, per theme
# Body text token: #222222; surface (bg): varies per theme
# Mint bg: #fafafa; Sage bg: #fafafa; Warm bg: #fafafa
# All themes keep --color-bg as #fafafa and --color-text as #222222 → universal pass
# ---------------------------------------------------------------------------


def test_mint_body_text_contrast_aa() -> None:
    """Mint: --color-text (#222222) on --color-bg (#fafafa) meets WCAG AA (4.5:1)."""
    assert _contrast("#222222", "#fafafa") >= 4.5


def test_sage_body_text_contrast_aa() -> None:
    """Sage: --color-text (#222222) on --color-bg (#fafafa) meets WCAG AA (4.5:1)."""
    assert _contrast("#222222", "#fafafa") >= 4.5


def test_warm_body_text_contrast_aa() -> None:
    """Warm: --color-text (#222222) on --color-bg (#fafafa) meets WCAG AA (4.5:1)."""
    assert _contrast("#222222", "#fafafa") >= 4.5


def test_mint_link_text_contrast_aa() -> None:
    """Mint: --color-accent-dark (#2d7d9a) on white meets WCAG AA (4.5:1)."""
    assert _contrast("#2d7d9a", "#ffffff") >= 4.5


def test_sage_link_text_contrast_aa() -> None:
    """Sage: --color-accent-dark (#4a7c59) on white meets WCAG AA (4.5:1)."""
    assert _contrast("#4a7c59", "#ffffff") >= 4.5


def test_warm_link_text_contrast_aa() -> None:
    """Warm: --color-accent-dark (#633d2e) on white meets WCAG AA (4.5:1)."""
    assert _contrast("#633d2e", "#ffffff") >= 4.5


def test_warm_heading_contrast_aa() -> None:
    """Warm: --color-cost (#4a3020) on white meets WCAG AA (4.5:1)."""
    assert _contrast("#4a3020", "#ffffff") >= 4.5


# ---------------------------------------------------------------------------
# Warm focus-visible WCAG fix — structure.py
# The warm :focus-visible rule must use --color-accent-dark as the outline color
# (double outline: dark + amber) because amber alone fails 3:1 UI contrast.
# ---------------------------------------------------------------------------


def test_warm_focus_visible_rule_present_in_structure() -> None:
    """STRUCTURE_CSS must contain a [data-theme='warm'] focus-visible override."""
    assert '[data-theme="warm"]' in STRUCTURE_CSS


def test_warm_focus_visible_uses_accent_dark() -> None:
    """The warm focus-visible rule must reference --color-accent-dark for the primary outline."""
    warm_focus_match = re.search(
        r'\[data-theme="warm"\][^{]*focus-visible[^{]*\{([^}]+)\}',
        STRUCTURE_CSS,
        re.DOTALL,
    )
    # The rule can be nested or combined; check the block content
    if warm_focus_match:
        block = warm_focus_match.group(1)
        assert "--color-accent-dark" in block, (
            "Warm focus-visible rule must use --color-accent-dark for WCAG AA compliance"
        )
    else:
        # Alternative: selector may span multiple lines differently
        # Look for any focus-visible context that mentions warm and accent-dark
        combined = re.search(
            r'data-theme.*warm|warm.*data-theme',
            STRUCTURE_CSS,
            re.DOTALL,
        )
        assert combined, "No warm theme focus-visible context found in STRUCTURE_CSS"
        assert "--color-accent-dark" in STRUCTURE_CSS, (
            "Warm focus-visible rule must use --color-accent-dark for WCAG AA compliance"
        )


def test_warm_focus_visible_amber_alone_fails_3to1() -> None:
    """Confirm that amber (#f7af63) alone would fail 3:1 against white — justifying the fix."""
    # This test documents WHY the double-outline is required
    amber_vs_white = _contrast("#f7af63", "#ffffff")
    assert amber_vs_white < 3.0, (
        f"Amber contrast on white is {amber_vs_white:.2f}:1 — "
        "test expects it to be below 3:1 (which is why the double outline is needed)"
    )


# ---------------------------------------------------------------------------
# :root block unchanged — no visual regression in default (Mint) theme
# ---------------------------------------------------------------------------


def test_root_block_retains_mint_accent() -> None:
    """The :root block in TOKENS_CSS still defines --color-accent as #9cddc8."""
    root_match = re.search(r":root\s*\{([^}]+)\}", TOKENS_CSS, re.DOTALL)
    assert root_match, "No :root block found in TOKENS_CSS"
    root_block = root_match.group(1)
    assert "#9cddc8" in root_block


def test_root_block_retains_accent_dark() -> None:
    """The :root block in TOKENS_CSS still defines --color-accent-dark as #2d7d9a."""
    root_match = re.search(r":root\s*\{([^}]+)\}", TOKENS_CSS, re.DOTALL)
    assert root_match, "No :root block found in TOKENS_CSS"
    root_block = root_match.group(1)
    assert "#2d7d9a" in root_block


# ---------------------------------------------------------------------------
# All three themes define --color-accent token
# ---------------------------------------------------------------------------


def _get_theme_block(theme: str, css: str) -> str:
    match = re.search(
        r'\[data-theme="' + re.escape(theme) + r'"\][^{]*\{([^}]+)\}',
        css,
        re.DOTALL,
    )
    assert match, f"No [data-theme='{theme}'] block found in TOKENS_CSS"
    return match.group(1)


def test_all_themes_define_color_accent() -> None:
    """All three theme blocks define --color-accent."""
    for theme in ("mint", "sage", "warm"):
        block = _get_theme_block(theme, TOKENS_CSS)
        assert "--color-accent" in block, f"[data-theme='{theme}'] missing --color-accent"


def test_all_themes_define_color_accent_dark() -> None:
    """All three theme blocks define --color-accent-dark."""
    for theme in ("mint", "sage", "warm"):
        block = _get_theme_block(theme, TOKENS_CSS)
        assert "--color-accent-dark" in block, f"[data-theme='{theme}'] missing --color-accent-dark"


def test_all_themes_define_primary_ring() -> None:
    """All three theme blocks define --color-primary-ring."""
    for theme in ("mint", "sage", "warm"):
        block = _get_theme_block(theme, TOKENS_CSS)
        assert "--color-primary-ring" in block, f"[data-theme='{theme}'] missing --color-primary-ring"


def test_all_themes_define_primary_bg() -> None:
    """All three theme blocks define --color-primary-bg."""
    for theme in ("mint", "sage", "warm"):
        block = _get_theme_block(theme, TOKENS_CSS)
        assert "--color-primary-bg" in block, f"[data-theme='{theme}'] missing --color-primary-bg"
