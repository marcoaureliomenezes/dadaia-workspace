"""Tests for views/reports.py scaffold — T-P5-32.

Covers:
  - render_reports_section() returns a non-empty string.
  - The returned string contains the section element with correct id.
  - The section contains a heading "Reports".
  - The section has proper ARIA attributes (role="tabpanel", aria-labelledby="tab-reports").
  - The section contains the list and content sub-sections.
  - The content section is hidden by default.
  - The function is importable from the correct module path.
"""

from __future__ import annotations

from dadaia_workspace.features.panel.views.reports import render_reports_section


def test_render_reports_section_returns_string() -> None:
    """render_reports_section() must return a non-empty string."""
    result = render_reports_section()
    assert isinstance(result, str)
    assert len(result) > 0


def test_render_reports_section_has_correct_id() -> None:
    """Section must have id='section-reports'."""
    result = render_reports_section()
    assert 'id="section-reports"' in result


def test_render_reports_section_has_role_tabpanel() -> None:
    """Section must carry role='tabpanel' for tab navigation."""
    result = render_reports_section()
    assert 'role="tabpanel"' in result


def test_render_reports_section_has_aria_labelledby() -> None:
    """Section must have aria-labelledby='tab-reports'."""
    result = render_reports_section()
    assert 'aria-labelledby="tab-reports"' in result


def test_render_reports_section_has_heading() -> None:
    """Section must contain an <h2>Reports</h2> heading."""
    result = render_reports_section()
    assert "Reports" in result
    assert "<h2>" in result or "<h2 " in result


def test_render_reports_section_has_reports_list_div() -> None:
    """Section must contain id='reports-list' div for JS population."""
    result = render_reports_section()
    assert 'id="reports-list"' in result


def test_render_reports_section_has_reports_content_div() -> None:
    """Section must contain id='reports-content' div for inline report display."""
    result = render_reports_section()
    assert 'id="reports-content"' in result


def test_render_reports_section_content_is_hidden() -> None:
    """The reports-content section must be hidden by default."""
    result = render_reports_section()
    assert "hidden" in result


def test_render_reports_section_has_empty_state() -> None:
    """Section must contain an empty-state/loading placeholder for client-side use."""
    result = render_reports_section()
    assert "empty-state" in result or "Loading" in result


def test_render_reports_section_is_section_element() -> None:
    """The root element must be a <section> tag."""
    result = render_reports_section().strip()
    assert result.startswith("<section")
    assert "</section>" in result


def test_render_reports_section_has_tabindex() -> None:
    """Section must be focusable (tabindex='0') for keyboard navigation."""
    result = render_reports_section()
    assert "tabindex" in result
