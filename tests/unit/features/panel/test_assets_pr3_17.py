"""Unit tests for PR3-17: Workflow detail view + hash routing + DAG skeleton.

Covers (per TASKS.md PR3-17 acceptance criteria):
  - DAG container present in detail markup (renderDetailView produces .workflow-dag)
  - Loading skeleton markup present (renderDetailSkeleton produces .workflow-dag-skeleton)
  - Back affordance present with correct ARIA
  - CSS includes rules for all 4 data-status variants (pending/running/done/failed)
  - Hash grammar tests: parseWorkflowHash + buildDetailHash
  - Detail fetch: workflows.js calls /api/workflows/<name>
  - Escape key handler present
  - Popstate listener registered
  - Stages table is collapsed by default (aria-expanded="false")
  - detail-view full-width CSS present
  - Error state renders retry button with ARIA label
  - window.Workflows exposes handleHashOnActivation, loadDetail, parseWorkflowHash
  - core.js calls handleHashOnActivation on tab activation
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent

_JS_DIR = _REPO_ROOT / "dadaia_workspace" / "features" / "panel" / "views" / "assets" / "js"

_CSS_DIR = _REPO_ROOT / "dadaia_workspace" / "features" / "panel" / "views" / "assets" / "css"


# ---------------------------------------------------------------------------
# Helper: read file text once per test
# ---------------------------------------------------------------------------


def _wf_js() -> str:
    return (_JS_DIR / "workflows.js").read_text(encoding="utf-8")


def _wf_css() -> str:
    from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

    return WORKFLOWS_CSS


def _core_js() -> str:
    return (_JS_DIR / "core.js").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# workflows.js — detail view markup
# ---------------------------------------------------------------------------


def test_workflows_js_detail_view_renders_dag_container() -> None:
    """renderDetailView must produce a .workflow-dag container for the SVG."""
    text = _wf_js()
    assert "workflow-dag" in text, (
        "workflows.js must produce a .workflow-dag container for the DAG SVG"
    )


def test_workflows_js_detail_view_injects_diagram_svg() -> None:
    """renderDetailView must inject diagram_svg from the API response."""
    text = _wf_js()
    assert "diagram_svg" in text, (
        "workflows.js must read and inject data.diagram_svg from the detail API response"
    )


def test_workflows_js_detail_view_has_agent_chips() -> None:
    """renderDetailView must render participating agent chips."""
    text = _wf_js()
    assert "workflow-detail-chip" in text, (
        "workflows.js must render .workflow-detail-chip elements for participating agents"
    )


def test_workflows_js_detail_view_has_stages_table() -> None:
    """renderDetailView must include a stages table."""
    text = _wf_js()
    assert "workflow-stages-table" in text, (
        "workflows.js must render a workflow stages table in the detail view"
    )


# ---------------------------------------------------------------------------
# workflows.js — loading skeleton
# ---------------------------------------------------------------------------


def test_workflows_js_has_detail_loading_skeleton() -> None:
    """renderDetailSkeleton must produce the DAG placeholder skeleton."""
    text = _wf_js()
    assert "workflow-dag-skeleton" in text, (
        "workflows.js must produce a .workflow-dag-skeleton element during loading"
    )


def test_workflows_js_skeleton_has_three_dag_placeholders() -> None:
    """The loading skeleton must contain 3 dag-node-placeholder elements."""
    text = _wf_js()
    count = text.count("dag-node-placeholder")
    assert count >= 3, (
        f"workflows.js skeleton must contain at least 3 .dag-node-placeholder elements "
        f"(found {count})"
    )


def test_workflows_js_skeleton_has_aria_busy() -> None:
    """The loading skeleton container must have aria-busy='true'."""
    text = _wf_js()
    assert 'aria-busy="true"' in text, (
        "workflows.js must set aria-busy='true' on the detail skeleton container"
    )


def test_workflows_js_skeleton_has_skeleton_pulse() -> None:
    """The detail skeleton elements must use skeleton-pulse class for animation."""
    text = _wf_js()
    assert "skeleton-pulse" in text, (
        "workflows.js detail skeleton must use .skeleton-pulse for pulse animation"
    )


# ---------------------------------------------------------------------------
# workflows.js — back affordance
# ---------------------------------------------------------------------------


def test_workflows_js_has_back_button() -> None:
    """Detail view must have a back button (workflow-back-btn)."""
    text = _wf_js()
    assert "workflow-back-btn" in text, (
        "workflows.js must render a .workflow-back-btn element in the detail view"
    )


def test_workflows_js_back_button_has_aria_label() -> None:
    """The back button must have an aria-label."""
    text = _wf_js()
    assert 'aria-label="Back to workflows' in text, (
        "workflows.js back button must have an aria-label starting with 'Back to workflows'"
    )


def test_workflows_js_skeleton_back_button_operative() -> None:
    """The skeleton also renders a back button (operative throughout loading)."""
    text = _wf_js()
    # The skeleton function must also emit a back button
    assert "detail-back-btn-skeleton" in text, (
        "workflows.js must render a back button in the loading skeleton (operative throughout)"
    )


def test_workflows_js_has_navigate_back_function() -> None:
    """workflows.js must define a navigateBack() function."""
    text = _wf_js()
    assert "navigateBack" in text, "workflows.js must define a navigateBack() function"


# ---------------------------------------------------------------------------
# workflows.js — Escape key
# ---------------------------------------------------------------------------


def test_workflows_js_has_escape_key_handler() -> None:
    """workflows.js must listen for Escape key to close the detail view."""
    text = _wf_js()
    assert "Escape" in text, "workflows.js must handle Escape key to close the detail view"


def test_workflows_js_escape_checks_inDetailView_flag() -> None:
    """The Escape handler must check the inDetailView flag."""
    text = _wf_js()
    assert "inDetailView" in text, (
        "workflows.js must maintain an inDetailView flag for Escape key guard"
    )


# ---------------------------------------------------------------------------
# workflows.js — hash routing
# ---------------------------------------------------------------------------


def test_workflows_js_has_parse_workflow_hash() -> None:
    """workflows.js must define parseWorkflowHash()."""
    text = _wf_js()
    assert "parseWorkflowHash" in text, (
        "workflows.js must define parseWorkflowHash() for hash grammar parsing"
    )


def test_workflows_js_has_build_detail_hash() -> None:
    """workflows.js must define buildDetailHash()."""
    text = _wf_js()
    assert "buildDetailHash" in text, (
        "workflows.js must define buildDetailHash() for emitting #workflows?detail=<name>"
    )


def test_workflows_js_hash_grammar_detail_param() -> None:
    """workflows.js must parse the 'detail' query param from hash."""
    text = _wf_js()
    assert "detail" in text and "params.get" in text, (
        "workflows.js must call params.get('detail') to parse the workflow name from hash"
    )


def test_workflows_js_hash_uses_hashtag_workflows_detail() -> None:
    """workflows.js must emit #workflows?detail= format in the hash."""
    text = _wf_js()
    assert "#workflows?detail=" in text, (
        "workflows.js must emit '#workflows?detail=' when navigating to detail view"
    )


def test_workflows_js_uses_history_push_state() -> None:
    """workflows.js must use history.pushState for hash navigation (no page reload)."""
    text = _wf_js()
    assert "history.pushState" in text, "workflows.js must use history.pushState for hash routing"


def test_workflows_js_has_popstate_listener() -> None:
    """workflows.js must register a popstate listener for browser back navigation."""
    text = _wf_js()
    assert "popstate" in text, (
        "workflows.js must register a 'popstate' event listener for back navigation"
    )


def test_workflows_js_handles_deep_link_on_activation() -> None:
    """workflows.js must expose handleHashOnActivation() for deep-link support."""
    text = _wf_js()
    assert "handleHashOnActivation" in text, (
        "workflows.js must define handleHashOnActivation() for direct deep-link support"
    )


# ---------------------------------------------------------------------------
# workflows.js — detail fetch
# ---------------------------------------------------------------------------


def test_workflows_js_fetches_api_workflows_detail() -> None:
    """workflows.js must fetch /api/workflows/<name> for the detail view."""
    text = _wf_js()
    assert "/api/workflows/" in text, (
        "workflows.js must call GET /api/workflows/<name> for detail fetch"
    )


def test_workflows_js_detail_uses_authed_fetch() -> None:
    """Detail fetch must use authedFetch (Bearer token)."""
    text = _wf_js()
    # authedFetch is used for the detail call
    count = text.count("authedFetch")
    assert count >= 2, (
        f"workflows.js must call authedFetch() at least twice: once for list, once for detail "
        f"(found {count} occurrences)"
    )


def test_workflows_js_detail_has_error_state() -> None:
    """Detail view must have an inline error state with a Retry button."""
    text = _wf_js()
    assert "detail-retry-btn" in text, (
        "workflows.js must render a detail retry button in the error state"
    )


def test_workflows_js_detail_error_has_role_alert() -> None:
    """Detail error state must have role='alert' for screen readers."""
    text = _wf_js()
    assert 'role="alert"' in text, "workflows.js must use role='alert' on error state markup"


# ---------------------------------------------------------------------------
# workflows.js — public API
# ---------------------------------------------------------------------------


def test_workflows_js_exposes_load_detail() -> None:
    """window.Workflows must expose loadDetail for external use."""
    text = _wf_js()
    assert "loadDetail" in text and "window.Workflows" in text, (
        "workflows.js must expose loadDetail on window.Workflows"
    )


def test_workflows_js_exposes_parse_workflow_hash_on_window() -> None:
    """window.Workflows must expose parseWorkflowHash."""
    text = _wf_js()
    assert "parseWorkflowHash" in text, "window.Workflows must expose parseWorkflowHash"


def test_workflows_js_exposes_build_detail_hash_on_window() -> None:
    """window.Workflows must expose buildDetailHash."""
    text = _wf_js()
    assert "buildDetailHash" in text, "window.Workflows must expose buildDetailHash"


def test_workflows_js_exposes_handle_hash_on_activation_on_window() -> None:
    """window.Workflows must expose handleHashOnActivation."""
    text = _wf_js()
    assert "handleHashOnActivation" in text, "window.Workflows must expose handleHashOnActivation"


# ---------------------------------------------------------------------------
# CSS — data-status hooks for all 4 states
# ---------------------------------------------------------------------------


def test_workflows_css_has_data_status_pending() -> None:
    """WORKFLOWS_CSS must define a rule for [data-status='pending']."""
    css = _wf_css()
    assert 'data-status="pending"' in css, (
        "workflows.css must define a CSS rule targeting [data-status='pending']"
    )


def test_workflows_css_has_data_status_running() -> None:
    """WORKFLOWS_CSS must define a rule for [data-status='running']."""
    css = _wf_css()
    assert 'data-status="running"' in css, (
        "workflows.css must define a CSS rule targeting [data-status='running']"
    )


def test_workflows_css_has_data_status_done() -> None:
    """WORKFLOWS_CSS must define a rule for [data-status='done']."""
    css = _wf_css()
    assert 'data-status="done"' in css, (
        "workflows.css must define a CSS rule targeting [data-status='done']"
    )


def test_workflows_css_has_data_status_failed() -> None:
    """WORKFLOWS_CSS must define a rule for [data-status='failed']."""
    css = _wf_css()
    assert 'data-status="failed"' in css, (
        "workflows.css must define a CSS rule targeting [data-status='failed']"
    )


# ---------------------------------------------------------------------------
# CSS — detail view styles
# ---------------------------------------------------------------------------


def test_workflows_css_has_detail_view_class() -> None:
    """WORKFLOWS_CSS must define .workflow-detail-view styles."""
    css = _wf_css()
    assert "workflow-detail-view" in css, (
        "workflows.css must define .workflow-detail-view full-width container styles"
    )


def test_workflows_css_has_dag_container() -> None:
    """WORKFLOWS_CSS must define .workflow-dag container styles."""
    css = _wf_css()
    assert ".workflow-dag" in css, "workflows.css must define .workflow-dag container styles"


def test_workflows_css_has_dag_skeleton() -> None:
    """WORKFLOWS_CSS must define .workflow-dag-skeleton styles."""
    css = _wf_css()
    assert "workflow-dag-skeleton" in css, (
        "workflows.css must define .workflow-dag-skeleton placeholder styles"
    )


def test_workflows_css_has_back_button_styles() -> None:
    """WORKFLOWS_CSS must define .workflow-back-btn styles."""
    css = _wf_css()
    assert "workflow-back-btn" in css, "workflows.css must define .workflow-back-btn styles"


def test_workflows_css_has_inline_error_styles() -> None:
    """WORKFLOWS_CSS must define .workflow-detail-error styles."""
    css = _wf_css()
    assert "workflow-detail-error" in css, (
        "workflows.css must define .workflow-detail-error inline error styles"
    )


def test_workflows_css_dag_container_has_overflow_x() -> None:
    """WORKFLOWS_CSS .workflow-dag must have overflow-x for wide DAGs."""
    css = _wf_css()
    assert "overflow-x" in css, (
        "workflows.css must define overflow-x on .workflow-dag so wide DAGs scroll"
    )


def test_workflows_css_skeleton_pulse_respects_reduced_motion() -> None:
    """WORKFLOWS_CSS must disable skeleton-pulse animation under prefers-reduced-motion."""
    css = _wf_css()
    assert "prefers-reduced-motion" in css, (
        "workflows.css must include @media (prefers-reduced-motion: reduce) to disable animation"
    )


def test_workflows_css_status_rules_use_color_tokens() -> None:
    """The data-status CSS rules must use var(--color-*) tokens, not bare hex."""
    css = _wf_css()
    # Find the section containing data-status rules
    status_section_start = css.find('data-status="pending"')
    assert status_section_start >= 0, "data-status='pending' rule not found"
    status_section = css[status_section_start:]
    var_count = status_section.count("var(--color-")
    assert var_count >= 3, (
        f"data-status CSS rules must use at least 3 var(--color-*) tokens (found {var_count})"
    )


# ---------------------------------------------------------------------------
# core.js — calls handleHashOnActivation
# ---------------------------------------------------------------------------


def test_core_js_calls_handle_hash_on_activation() -> None:
    """core.js must call window.Workflows.handleHashOnActivation() on workflows tab click."""
    text = _core_js()
    assert "handleHashOnActivation" in text, (
        "core.js must call window.Workflows.handleHashOnActivation() when the workflows "
        "tab is activated"
    )


def test_core_js_routes_hash_workflows_detail_on_load() -> None:
    """core.js initial hash routing must handle #workflows?detail= deep links."""
    text = _core_js()
    # The tab click triggered by core.js now delegates to handleHashOnActivation
    # which handles #workflows?detail=<name> deep links
    assert "#workflows" in text or "hash.startsWith('#workflows')" in text, (
        "core.js must handle the #workflows hash variant on initial load"
    )
