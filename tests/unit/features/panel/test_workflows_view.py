"""Unit tests for the first-class Workflows panel section (T-28-C-03, D-5).

The model-governance editor is JS-driven (workflow-policy.js populates ``#wfp-root``),
so these assert the server-rendered scaffold exposes every DOM hook the client targets:
the section is a top-level tabpanel, the toolbar carries validate + save buttons, the
banner + editor root exist, and the server-rendered dadaia-workflow catalog is available
as the no-JS reference/fallback. The full editor interaction is covered by the Playwright
spec ``tests/e2e/panel/workflow-policy-editor.spec.ts`` (qa H1 obligation).
"""

from __future__ import annotations

from dadaia_workspace.features.panel.views.static import render_static
from dadaia_workspace.features.panel.views.workflows import (
    render_workflows_first_class_section,
)


def test_first_class_section_is_top_level_tabpanel() -> None:
    html = render_workflows_first_class_section()
    assert 'id="section-workflows"' in html
    assert 'role="tabpanel"' in html
    assert 'aria-labelledby="tab-workflows"' in html


def test_first_class_section_exposes_editor_dom_hooks() -> None:
    html = render_workflows_first_class_section()
    # Toolbar buttons the client wires up.
    assert 'id="wfp-validate-btn"' in html
    assert 'id="wfp-save-btn"' in html
    # Validate-before-save banner + editor root the JS populates.
    assert 'id="wfp-banner"' in html
    assert 'id="wfp-root"' in html


def test_first_class_section_carries_ssr_catalog_fallback() -> None:
    # The server-rendered dadaia-workflow catalog is the no-JS reference/fallback.
    html = render_workflows_first_class_section()
    assert "dadaia-wf-catalog" in html
    # The server-rendered SVG DAG is present (browser-Mermaid is never an exec dep).
    assert "dadaia-wf-diagram-svg" in html


def test_editor_assets_are_served() -> None:
    serve = render_static()
    for name, mime in (("workflow-policy.js", "javascript"), ("workflow-policy.css", "css")):
        status, content_type, body = serve(name=name)
        assert status == 200
        assert mime in content_type
        assert len(body) > 0


def test_editor_js_targets_the_control_plane_endpoints() -> None:
    # Guard the client/server contract: the JS must call the Wave C routes.
    serve = render_static()
    _status, _ct, body = serve(name="workflow-policy.js")
    js = body.decode("utf-8")
    assert "/api/workflow-catalog" in js
    assert "/api/workflow-model-profiles" in js
    assert "/api/workflow-model-policy" in js
    assert "/api/workflow-model-policy/validate" in js
    assert "/api/lifecycle-runs" in js
