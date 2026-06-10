"""Tests for views/reports.py scaffold — T-P5-32.

Covers the static Reports tabpanel skeleton: it is a focusable ``<section>`` tab
target carrying the correct id, ARIA wiring, heading, list/content sub-sections
(content hidden by default), and a loading placeholder for client-side population.

The skeleton is exercised by asserting on its rendered structure rather than
smoke-asserting a non-empty string — each assertion fails on a real regression that
drops a DOM hook (tab wiring, list/content divs, or the hidden-by-default content).
"""

from __future__ import annotations

from dadaia_workspace.features.panel.views.reports import render_reports_section


def test_reports_section_is_focusable_tabpanel() -> None:
    """The root is a focusable ``<section>`` tab target with correct id + ARIA wiring."""
    result = render_reports_section()
    stripped = result.strip()

    # Root element is a <section> ... </section>.
    assert stripped.startswith("<section")
    assert "</section>" in stripped
    # Tab identity + ARIA wiring (id, role, labelledby, focusable).
    assert 'id="section-reports"' in result
    assert 'role="tabpanel"' in result
    assert 'aria-labelledby="tab-reports"' in result
    assert "tabindex" in result


def test_reports_section_has_heading_list_and_hidden_content() -> None:
    """The section carries its heading, the list div, the content div (hidden by
    default), and a loading placeholder for client-side use."""
    result = render_reports_section()

    # Heading.
    assert "Reports" in result
    assert "<h2>" in result or "<h2 " in result
    # List div + content div for JS population.
    assert 'id="reports-list"' in result
    assert 'id="reports-content"' in result
    # Content section is hidden by default.
    assert "hidden" in result
    # Empty-state / loading placeholder.
    assert "empty-state" in result or "Loading" in result
