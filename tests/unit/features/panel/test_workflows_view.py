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
    render_dadaia_workflows_section,
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


def test_diagram_cards_lead_and_policy_matrix_is_secondary() -> None:
    """v0.1.45 IA flip (T-45-08, operator directive): cards lead, policy is secondary.

    The diagram-card catalog must be the prominent, default-visible top of the Workflows
    tab (NOT buried in a collapsed <details>), and the model-governance policy matrix must
    be demoted below the cards into a collapsed ``Model policy`` disclosure.
    """
    html = render_workflows_first_class_section()
    # The card catalog appears BEFORE the policy editor root.
    assert html.index("dadaia-wf-catalog") < html.index('id="wfp-root"')
    # The card catalog is NOT inside the (now removed) collapsed reference disclosure.
    assert "wfp-reference" not in html
    assert "Reference: full step sequence" not in html
    # The policy matrix is demoted into the collapsed Model policy disclosure.
    assert '<details class="wfp-policy">' in html
    assert "wfp-policy-title" in html
    # The demoted disclosure is COLLAPSED by default (no `open` attribute on it).
    assert '<details class="wfp-policy" open' not in html
    # Both surfaces stay fully functional — the editor DOM hooks are still present.
    assert 'id="wfp-validate-btn"' in html
    assert 'id="wfp-save-btn"' in html
    assert 'id="wfp-root"' in html


def test_dadaia_cards_are_expandable_details_disclosures() -> None:
    """v0.1.45: each dadaia-workflow card is a native <details> disclosure (CSP-clean).

    Big-card face carries header + fluxogram + compact step-chain; the full per-step
    detail lives in the expandable body. No dead client-Mermaid block; not a <dialog>.
    """
    html = render_dadaia_workflows_section()
    assert '<details class="dadaia-wf-card"' in html
    assert '<summary class="dadaia-wf-card-summary">' in html
    assert '<div class="dadaia-wf-detail">' in html
    # Compact step-chain summary on the collapsed face.
    assert "dadaia-wf-step-chain" in html
    # The dead client-Mermaid layer is gone; server-SVG is the single diagram source.
    assert 'class="mermaid"' not in html
    assert "dadaia-wf-diagram-mermaid" not in html
    assert "dadaia-wf-diagram-svg" in html
    # No <dialog> — the accepted PE decision rejected it (avoid a new CSP hash).
    assert "<dialog" not in html


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
