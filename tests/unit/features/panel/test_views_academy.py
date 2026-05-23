"""Tests for views/academy.py scaffold — T-P5-26.

Covers:
  - render_academy_section() returns a non-empty string.
  - The returned string contains the section element with correct id.
  - The section contains a heading "Academy".
  - The section has proper ARIA attributes (role="tabpanel", aria-labelledby="tab-academy").
  - The section contains the empty-state loading placeholder.
  - The function is importable from the correct module path.
"""

from __future__ import annotations

from dadaia_workspace.features.panel.views.academy import render_academy_section


def test_render_academy_section_returns_string() -> None:
    """render_academy_section() must return a non-empty string."""
    result = render_academy_section()
    assert isinstance(result, str)
    assert len(result) > 0


def test_render_academy_section_has_correct_id() -> None:
    """Section must have id='section-academy'."""
    result = render_academy_section()
    assert 'id="section-academy"' in result


def test_render_academy_section_has_role_tabpanel() -> None:
    """Section must carry role='tabpanel' for tab navigation."""
    result = render_academy_section()
    assert 'role="tabpanel"' in result


def test_render_academy_section_has_aria_labelledby() -> None:
    """Section must have aria-labelledby='tab-academy'."""
    result = render_academy_section()
    assert 'aria-labelledby="tab-academy"' in result


def test_render_academy_section_has_heading() -> None:
    """Section must contain an <h2>Academy</h2> heading."""
    result = render_academy_section()
    assert "Academy" in result
    assert "<h2>" in result or "<h2 " in result


def test_render_academy_section_has_academy_content_div() -> None:
    """Section must contain id='academy-content' div for JS population."""
    result = render_academy_section()
    assert 'id="academy-content"' in result


def test_render_academy_section_has_empty_state() -> None:
    """Section must contain an empty-state/loading placeholder for client-side use."""
    result = render_academy_section()
    assert "empty-state" in result or "Loading" in result


def test_render_academy_section_is_section_element() -> None:
    """The root element must be a <section> tag."""
    result = render_academy_section().strip()
    assert result.startswith("<section")
    assert "</section>" in result


def test_render_academy_section_has_tabindex() -> None:
    """Section must be focusable (tabindex='0') for keyboard navigation."""
    result = render_academy_section()
    assert "tabindex" in result
