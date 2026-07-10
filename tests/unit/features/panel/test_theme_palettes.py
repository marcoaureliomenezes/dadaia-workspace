"""Unit contracts for panel theme palettes — the single a11y-contrast owner.

Real detector: WCAG AA contrast computed from the PARSED CSS (never hardcoded
literals — see ``test_panel_css_contrast.py``'s replaced role). Two survivors:
  1. Required tokens per theme are declared.
  2. Body/link contrast meets WCAG AA, computed from real parsed CSS + the warm
     focus-visible token folds in as an extra assertion.
"""

from __future__ import annotations

import re

import pytest

from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS

pytestmark = pytest.mark.unit


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def _channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast(fg: str, bg: str) -> float:
    lighter, darker = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _theme_block(theme: str) -> str:
    match = re.search(rf'\[data-theme="{theme}"\][^{{]*\{{([^}}]+)\}}', TOKENS_CSS, re.DOTALL)
    assert match, f"No [data-theme={theme!r}] block found"
    return match.group(1)


def _root_block() -> str:
    match = re.search(r":root\s*\{([^}]+)\}", TOKENS_CSS, re.DOTALL)
    assert match, "No :root token block found"
    return match.group(1)


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"(--color-[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})", block))


def _theme_tokens(theme: str) -> dict[str, str]:
    tokens = _tokens(_root_block())
    tokens.update(_tokens(_theme_block(theme)))
    return tokens


@pytest.mark.parametrize("theme", ["mint", "sage", "warm"])
def test_theme_declares_required_color_tokens(theme: str) -> None:
    """Every selectable theme must provide the tokens used by the panel shell."""
    tokens = _theme_tokens(theme)
    for name in ["--color-bg", "--color-surface", "--color-text", "--color-accent-dark"]:
        assert name in tokens


@pytest.mark.parametrize("theme", ["mint", "sage", "warm"])
def test_theme_body_and_link_contrast_meet_wcag_aa(theme: str) -> None:
    """Theme text and link colors must meet WCAG AA contrast on their surfaces
    (computed from parsed CSS, never hardcoded literals)."""
    tokens = _theme_tokens(theme)
    assert _contrast(tokens["--color-text"], tokens["--color-bg"]) >= 4.5
    assert _contrast(tokens["--color-accent-dark"], tokens["--color-surface"]) >= 4.5

    if theme != "warm":
        return

    # Warm focus-visible styling uses the darker accent token for visible focus.
    warm_focus_match = re.search(
        r'\[data-theme="warm"\][^{]*focus-visible[^{]*\{([^}]+)\}',
        STRUCTURE_CSS,
        re.DOTALL,
    )
    if warm_focus_match:
        assert "--color-accent-dark" in warm_focus_match.group(1)
    else:
        assert '[data-theme="warm"]' in STRUCTURE_CSS
        assert "--color-accent-dark" in STRUCTURE_CSS
