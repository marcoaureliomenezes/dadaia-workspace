"""Unit tests for views/workflows.py.

Covers:
  - render_workflows_section() returns a non-empty string
  - Section carries role="tabpanel" and aria-labelledby="tab-workflows"
  - Grid container id="workflows-grid" is present
  - Empty-state id="workflows-empty" element is present

render_workflows_section() is a static HTML skeleton; workflow cards are
populated client-side via JS fetch. No hardcoded card count is asserted here.
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


def test_section_has_workflows_list() -> None:
    """panel-defects Bug 4: left pane must include workflows-list nav."""
    html = render_workflows_section()
    assert 'id="workflows-list"' in html


def test_section_has_workflows_detail() -> None:
    """panel-defects Bug 4: right pane must include workflows-detail region."""
    html = render_workflows_section()
    assert 'id="workflows-detail"' in html
    assert 'role="region"' in html


def test_section_detail_has_aria_live() -> None:
    """panel-defects Bug 4: detail pane must have aria-live for dynamic updates."""
    html = render_workflows_section()
    assert 'aria-live="polite"' in html
