"""Tests for views/academy.py scaffold — T-P5-26.

Covers the static Academy tabpanel skeleton: it is a focusable ``<section>`` tab
target carrying the correct id, ARIA wiring, heading, content div, and a loading
placeholder for client-side population.

The skeleton is exercised by asserting on its rendered structure rather than
smoke-asserting a non-empty string — each assertion fails on a real regression that
drops a DOM hook (tab wiring, content div, or the loading placeholder).
"""

from __future__ import annotations

from dadaia_workspace.features.panel.views.academy import render_academy_section


def test_academy_section_is_focusable_tabpanel() -> None:
    """The root is a focusable ``<section>`` tab target with correct id + ARIA wiring."""
    result = render_academy_section()
    stripped = result.strip()

    # Root element is a <section> ... </section>.
    assert stripped.startswith("<section")
    assert "</section>" in stripped
    # Tab identity + ARIA wiring (id, role, labelledby, focusable).
    assert 'id="section-academy"' in result
    assert 'role="tabpanel"' in result
    assert 'aria-labelledby="tab-academy"' in result
    assert "tabindex" in result


def test_academy_section_has_heading_content_and_placeholder() -> None:
    """The section carries its heading, the JS content div, and a loading placeholder."""
    result = render_academy_section()

    # Heading.
    assert "Academy" in result
    assert "<h2>" in result or "<h2 " in result
    # Content div the client JS populates.
    assert 'id="academy-content"' in result
    # Empty-state / loading placeholder for client-side use.
    assert "empty-state" in result or "Loading" in result
