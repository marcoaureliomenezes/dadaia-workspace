"""Unit test for the first-class Workflows panel section (T-28-C-03, D-5).

The model-governance editor is JS-driven (workflow-policy.js populates
``#wfp-root``), so this asserts the server-rendered scaffold exposes every DOM
hook the client targets. The full editor interaction is covered by the
Playwright spec ``tests/e2e/panel/workflow-policy-editor.spec.ts`` (qa H1
obligation); the asset-served facet is owned by ``test_static.py``'s param;
the JS-endpoint-string greps are owned by the e2e editor spec driving the real
endpoints.

One merged SSR scaffold-hooks check: section tabpanel + wfp validate/save/
banner ids + ssr catalog + svg diagram + step-picker mounts + no wfp-root/
mermaid/dialog residue.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.panel.views.workflows import (
    render_dadaia_workflows_section,
    render_workflows_first_class_section,
)

pytestmark = pytest.mark.unit


def test_workflows_section_ssr_scaffold_hooks() -> None:
    html = render_workflows_first_class_section()

    # Top-level tabpanel identity.
    assert 'id="section-workflows"' in html
    assert 'role="tabpanel"' in html
    assert 'aria-labelledby="tab-workflows"' in html

    # Validate/Save toolbar + banner (v0.1.45: pickers live inline in the cards).
    assert 'id="wfp-validate-btn"' in html
    assert 'id="wfp-save-btn"' in html
    assert 'id="wfp-banner"' in html

    # Server-rendered dadaia-workflow catalog leads the tab, with server-SVG DAG.
    assert "dadaia-wf-catalog" in html
    assert "dadaia-wf-diagram-svg" in html

    # v0.1.45 redesign: the old separate collapsed "Model policy" matrix/disclosure
    # is gone — per-step pickers live inside the card expand instead.
    assert 'id="wfp-root"' not in html
    assert '<details class="wfp-policy">' not in html
    assert "wfp-policy-title" not in html
    assert 'class="wf-step-picker"' in html
    assert 'data-wfp-workflow="release_definition"' in html
    assert "data-wfp-step=" in html

    # Each dadaia-workflow card is a native <details> disclosure (CSP-clean, no
    # dead client-Mermaid block, not a <dialog>).
    cards_html = render_dadaia_workflows_section()
    assert '<details class="dadaia-wf-card"' in cards_html
    assert '<summary class="dadaia-wf-card-summary">' in cards_html
    assert '<div class="dadaia-wf-detail">' in cards_html
    assert "dadaia-wf-step-chain" in cards_html
    assert "dadaia-wf-flux" in cards_html
    assert "dadaia-wf-step-head" in cards_html
    assert 'class="wf-step-picker"' in cards_html
    assert "dadaia-wf-step-harness" not in cards_html
    assert 'class="mermaid"' not in cards_html
    assert "dadaia-wf-diagram-mermaid" not in cards_html
    assert "dadaia-wf-diagram-svg" in cards_html
    assert "<dialog" not in cards_html
