"""Unit tests for views/workflows.py — T-AM-17.

Covers:
  - render_workflows_section() returns a non-empty string
  - Section carries role="tabpanel" and aria-labelledby="tab-workflows"
  - Grid container id="workflows-grid" is present
  - Empty-state id="workflows-empty" element is present
"""

from dadaia_workspace.features.panel.views.workflows import render_workflows_section


def test_render_workflows_section_returns_string() -> None:
    """render_workflows_section() must return a non-empty string."""
    result = render_workflows_section()
    assert isinstance(result, str)
    assert len(result) > 0


def test_section_has_role_tabpanel() -> None:
    """Section must carry role="tabpanel" and aria-labelledby="tab-workflows"."""
    html = render_workflows_section()
    assert 'role="tabpanel"' in html
    assert 'aria-labelledby="tab-workflows"' in html


def test_section_has_grid_container() -> None:
    """Section must include a grid container with id="workflows-grid"."""
    html = render_workflows_section()
    assert 'id="workflows-grid"' in html


def test_section_has_empty_state() -> None:
    """Section must include empty-state element with id="workflows-empty"."""
    html = render_workflows_section()
    assert 'id="workflows-empty"' in html
