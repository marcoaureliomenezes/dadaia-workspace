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
    # Single visible Validate / Save toolbar (v0.1.45: pickers live inline in the cards).
    assert 'id="wfp-validate-btn"' in html
    assert 'id="wfp-save-btn"' in html
    # Validate-before-save banner.
    assert 'id="wfp-banner"' in html


def test_first_class_section_carries_ssr_catalog() -> None:
    # The server-rendered dadaia-workflow catalog leads the tab.
    html = render_workflows_first_class_section()
    assert "dadaia-wf-catalog" in html
    # The server-rendered SVG DAG is present (browser-Mermaid is never an exec dep).
    assert "dadaia-wf-diagram-svg" in html


def test_model_governance_is_merged_into_the_card_expand() -> None:
    """v0.1.45 redesign (operator directive): the per-step model pickers live INSIDE the
    workflow card expand — the old separate collapsed "Model policy" matrix is folded away.
    """
    html = render_workflows_first_class_section()
    # The removed matrix / disclosure DOM is gone.
    assert 'id="wfp-root"' not in html
    assert '<details class="wfp-policy">' not in html
    assert "wfp-policy-title" not in html
    # Inline per-step picker mounts are present (keyed by workflow + step).
    assert 'class="wf-step-picker"' in html
    assert 'data-wfp-workflow="release_definition"' in html
    assert "data-wfp-step=" in html
    # The Validate / Save affordance the policy mutation needs is still present.
    assert 'id="wfp-validate-btn"' in html
    assert 'id="wfp-save-btn"' in html


def test_dadaia_cards_are_expandable_details_disclosures() -> None:
    """v0.1.45: each dadaia-workflow card is a native <details> disclosure (CSP-clean).

    Collapsed face carries header + purpose + compact step-chain; the expand carries the
    legible fluxogram + one formatted step card per step + inline model pickers. No dead
    client-Mermaid block; not a <dialog>.
    """
    html = render_dadaia_workflows_section()
    assert '<details class="dadaia-wf-card"' in html
    assert '<summary class="dadaia-wf-card-summary">' in html
    assert '<div class="dadaia-wf-detail">' in html
    # Compact step-chain summary on the collapsed face.
    assert "dadaia-wf-step-chain" in html
    # The fluxogram is the expand centrepiece; formatted step cards + inline pickers follow.
    assert "dadaia-wf-flux" in html
    assert "dadaia-wf-step-head" in html
    assert 'class="wf-step-picker"' in html
    # No monospace comma-dump of every allowed model any more.
    assert "dadaia-wf-step-harness" not in html
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
    # v0.1.45 redesign: per-step model governance moved into the inline expand pickers;
    # the run-history ("Run snapshots") view was dropped from this JS, so it no longer
    # fetches /api/lifecycle-runs. The endpoint itself remains served (handler.py) for
    # API consumers; if a run-history UI returns it will re-reference the route.
