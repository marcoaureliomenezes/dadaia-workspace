"""WCAG contrast ratio tests for the canonical PALETTE.

Spec: dadaia-workspace-brand-identity-v1 SPEC.md §3 acceptance criteria.
"""
from __future__ import annotations

import re

from dadaia_workspace.features.panel.views._assets import PANEL_CSS


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


def test_text_on_accent_aa() -> None:
    assert _contrast("#222222", "#9cddc8") >= 4.5


def test_text_on_warning_aa() -> None:
    assert _contrast("#3d3600", "#ddd9ab") >= 4.5


def test_text_on_accent_secondary_aa() -> None:
    assert _contrast("#222222", "#bfd8ad") >= 4.5


def test_cost_on_white_aaa() -> None:
    assert _contrast("#633d2e", "#ffffff") >= 7.0


def test_accent_never_used_as_text_color() -> None:
    """#9cddc8 must never appear as a `color:` value in PANEL_CSS."""
    bad = re.findall(r"color\s*:\s*#9cddc8", PANEL_CSS, flags=re.IGNORECASE)
    assert not bad, f"accent (#9cddc8) used as text color: {bad}"


def test_alert_never_used_as_text_color() -> None:
    """#f7af63 must never appear as a `color:` value in PANEL_CSS."""
    bad = re.findall(r"color\s*:\s*#f7af63", PANEL_CSS, flags=re.IGNORECASE)
    assert not bad, f"alert (#f7af63) used as text color: {bad}"
