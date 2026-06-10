"""Unit tests for views/workflows.py.

Covers the static HTML skeleton contract (T-016-P09): workflows are a sub-section
inside the Ops tab (no longer a top-level tabpanel). Workflow cards are populated
client-side via JS fetch; no hardcoded card count is asserted.

The skeleton is exercised by asserting on its rendered structure (distinct ids,
region role, aria-live) rather than smoke-asserting a non-empty string — each
assertion fails on a real regression that drops a DOM hook the client JS depends on.
"""

from dadaia_workspace.features.panel.views.workflows import render_workflows_section


def test_workflows_subsection_structure() -> None:
    """The Ops workflows sub-section exposes every DOM hook the client JS targets.

    After T-016-P09 the container is a sub-section (``ops-subsection-workflows``),
    NOT a ``role="tabpanel"`` target. The grid, empty-state, list nav, and detail
    region (panel-defects Bug 4) must all be present with a polite aria-live so the
    fetch-driven master/detail UI can render.
    """
    html = render_workflows_section()

    # Sub-section container (replaces the former top-level tabpanel).
    assert 'id="ops-subsection-workflows"' in html
    # Grid + empty-state the client JS targets.
    assert 'id="workflows-grid"' in html
    assert 'id="workflows-empty"' in html
    # panel-defects Bug 4: master/detail panes with a live region.
    assert 'id="workflows-list"' in html
    assert 'id="workflows-detail"' in html
    assert 'role="region"' in html
    assert 'aria-live="polite"' in html
