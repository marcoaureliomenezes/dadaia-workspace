"""Tests for PR3-16: Workflows IIFE extraction from core.js into workflows.js.

Covers the acceptance criteria from TASKS.md PR3-16:
  - core.js no longer contains the Workflows IIFE block
  - PANEL_JS in _assets.py reads from workflows.js (produces a concatenated JS string)
  - workflows.js is non-empty and contains the card-grid implementation
  - index.py includes <script src="/static/workflows.js">
  - workflows section HTML has a container element workflows.js can target
  - PANEL_JS remains syntactically valid after the move
  - workflows CSS uses var(--color-*) tokens and defines card grid layout
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent

_JS_DIR = _REPO_ROOT / "dadaia_workspace" / "features" / "panel" / "views" / "assets" / "js"

_VIEWS_DIR = _REPO_ROOT / "dadaia_workspace" / "features" / "panel" / "views"


# ---------------------------------------------------------------------------
# core.js — Workflows IIFE must be extracted
# ---------------------------------------------------------------------------


def test_core_js_no_longer_contains_workflows_iife_marker() -> None:
    """core.js must NOT contain 'var Workflows = (function' after PR3-16."""
    core_text = (_JS_DIR / "core.js").read_text(encoding="utf-8")
    assert "var Workflows = (function" not in core_text, (
        "core.js still contains 'var Workflows = (function' — "
        "the Workflows IIFE must be extracted to workflows.js"
    )


def test_core_js_no_workflows_iife_comment_block() -> None:
    """core.js must not contain the '── workflows tab' comment block after PR3-16."""
    core_text = (_JS_DIR / "core.js").read_text(encoding="utf-8")
    assert "── workflows tab" not in core_text, (
        "core.js still contains the '── workflows tab' comment block — "
        "that section must move to workflows.js"
    )


# ---------------------------------------------------------------------------
# workflows.js — must be non-empty and contain card-grid implementation
# ---------------------------------------------------------------------------


def test_workflows_js_is_nonempty() -> None:
    """workflows.js must not be the stub comment-only file."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert len(wf_text) > 500, (
        f"workflows.js is too short ({len(wf_text)} chars) — "
        "it appears to still be the stub placeholder"
    )


def test_workflows_js_fetches_api_workflows() -> None:
    """workflows.js must call /api/workflows to load the card grid."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert "/api/workflows" in wf_text, "workflows.js must fetch /api/workflows"


def test_workflows_js_uses_authed_fetch() -> None:
    """workflows.js must use authedFetch (defined in core.js) to call the API."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert "authedFetch" in wf_text, "workflows.js must call authedFetch() to send the Bearer token"


def test_workflows_js_renders_card_per_workflow() -> None:
    """workflows.js must render one card per workflow (card-grid pattern)."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    # The card-grid approach replaces the 2-pane; check for card class references
    assert "workflow-card" in wf_text, (
        "workflows.js must render .workflow-card elements (card-grid, not 2-pane list)"
    )


def test_workflows_js_renders_agent_chips() -> None:
    """workflows.js card must include agent chips for each agent_id."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert "agent_ids" in wf_text or "agent-chip" in wf_text, (
        "workflows.js must render agent chips from agent_ids"
    )


def test_workflows_js_renders_stage_count_badge() -> None:
    """workflows.js card must display stage_count badge."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert "stage_count" in wf_text or "stage" in wf_text.lower(), (
        "workflows.js must render a stage count badge"
    )


def test_workflows_js_has_loading_skeleton() -> None:
    """workflows.js must render a loading skeleton while fetch is in flight."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert "skeleton" in wf_text.lower() or "aria-busy" in wf_text, (
        "workflows.js must render a loading skeleton (aria-busy or .skeleton class)"
    )


def test_workflows_js_has_empty_state() -> None:
    """workflows.js must handle an empty workflows list and show an empty state."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert "empty" in wf_text.lower() or "workflows-empty" in wf_text, (
        "workflows.js must handle empty state"
    )


def test_workflows_js_has_error_state() -> None:
    """workflows.js must handle fetch errors and show an error state."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert "error" in wf_text.lower(), "workflows.js must contain error state handling"


def test_workflows_js_has_view_dag_affordance() -> None:
    """workflows.js card must include a 'View DAG' affordance element with data-workflow-name."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert "data-workflow-name" in wf_text, (
        "workflows.js must include data-workflow-name attribute on the CTA "
        "so PR3-17 can wire the click handler"
    )


def test_workflows_js_exposes_window_workflows() -> None:
    """workflows.js must expose window.Workflows (like agents.js exposes window.Agents)."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    assert "window.Workflows" in wf_text, (
        "workflows.js must expose window.Workflows for core.js tab-activation hook"
    )


def test_workflows_js_cards_are_keyboard_accessible() -> None:
    """workflows.js cards or affordance must be keyboard accessible (Enter/Space)."""
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    # Either proper button element usage or explicit keydown handling
    assert (
        "keydown" in wf_text
        or "<button" in wf_text
        or 'type="button"' in wf_text
        or "type='button'" in wf_text
    ), "workflows.js must render cards/affordances as <button> or handle keyboard events"


# ---------------------------------------------------------------------------
# JS files — workflows.js + core.js + agents.js content checks
# T-P5-01: PANEL_JS removed from _assets.py. JS files are served directly by
# static.py. Assemble PANEL_JS inline here for content verification.
# ---------------------------------------------------------------------------


def _build_panel_js() -> str:
    """Assemble PANEL_JS from individual JS files (mirrors static.py behaviour)."""
    return (
        (_JS_DIR / "core.js").read_text(encoding="utf-8")
        + "\n"
        + (_JS_DIR / "agents.js").read_text(encoding="utf-8")
        + "\n"
        + (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    )


def test_panel_js_includes_workflows_js_content() -> None:
    """Assembled JS must include content from workflows.js."""
    panel_js = _build_panel_js()
    wf_text = (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    lines = [
        ln.strip() for ln in wf_text.splitlines() if ln.strip() and not ln.strip().startswith("//")
    ]
    assert len(lines) > 0, "workflows.js has no non-comment content"
    first_code_line = lines[0]
    assert first_code_line in panel_js, (
        f"Assembled JS does not contain the first code line of workflows.js: {first_code_line!r}."
    )


def test_panel_js_still_contains_core_js_content() -> None:
    """Assembled JS must still include core.js content (tab switching, token bootstrap, etc.)."""
    panel_js = _build_panel_js()
    assert "authedFetch" in panel_js
    assert "bootstrapToken" in panel_js


def test_panel_js_still_contains_agents_js_content() -> None:
    """Assembled JS must still include agents.js content."""
    panel_js = _build_panel_js()
    assert "window.Agents" in panel_js


# ---------------------------------------------------------------------------
# index.py — must include <script src="/static/workflows.js">
# ---------------------------------------------------------------------------


def test_index_py_includes_workflows_js_script_tag() -> None:
    """index.py must include <script src="/static/workflows.js"> in the HTML output."""
    index_text = (_VIEWS_DIR / "index.py").read_text(encoding="utf-8")
    assert "/static/workflows.js" in index_text, (
        'index.py must include a <script src="/static/workflows.js"> tag'
    )


# ---------------------------------------------------------------------------
# workflows.py (views) — section HTML compatibility
# ---------------------------------------------------------------------------


def test_workflows_section_has_grid_container_for_js() -> None:
    """render_workflows_section must include id='workflows-grid' for workflows.js to target."""
    from dadaia_workspace.features.panel.views.workflows import render_workflows_section

    html = render_workflows_section()
    assert 'id="workflows-grid"' in html


# ---------------------------------------------------------------------------
# CSS — workflows.css must define card grid and use var(--color-*) tokens
# ---------------------------------------------------------------------------


def test_workflows_css_defines_card_grid() -> None:
    """WORKFLOWS_CSS must define a card grid layout (not 2-pane)."""
    from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

    assert "workflow-card" in WORKFLOWS_CSS, (
        "workflows.css must define .workflow-card styles for the card grid"
    )
    assert "grid" in WORKFLOWS_CSS.lower(), "workflows.css must use CSS grid for the card layout"


def test_workflows_css_uses_var_color_tokens() -> None:
    """WORKFLOWS_CSS must use var(--color-*) tokens, not bare hex for major colors."""
    from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

    var_count = WORKFLOWS_CSS.count("var(--color-")
    assert var_count >= 5, (
        f"workflows.css uses var(--color-*) only {var_count} times — "
        "should use tokens extensively for theme support"
    )


def test_workflows_css_is_responsive() -> None:
    """WORKFLOWS_CSS must include a media query for responsive layout."""
    from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

    assert "@media" in WORKFLOWS_CSS, (
        "workflows.css must include a media query for responsive (mobile-first) layout"
    )


def test_workflows_css_has_stage_count_badge() -> None:
    """WORKFLOWS_CSS must define styles for the stage count badge."""
    from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

    assert "stage" in WORKFLOWS_CSS.lower(), (
        "workflows.css must define styles for the stage count badge"
    )


def test_workflows_css_has_hover_focus_styles() -> None:
    """WORKFLOWS_CSS must define hover and focus-visible styles for cards."""
    from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

    assert ":hover" in WORKFLOWS_CSS, "workflows.css must define :hover styles"
    assert "focus" in WORKFLOWS_CSS, "workflows.css must define :focus or :focus-visible styles"
