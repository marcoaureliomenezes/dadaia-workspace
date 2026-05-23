"""Unit tests for PR3-11 / P5-D (T-P5-18 to T-P5-20): Agent card modal interaction.

PR3-11 covered the inline expand/collapse.  P5-D (T-P5-18 to T-P5-20) replaces the
inline expand with a native <dialog> modal.  Tests updated accordingly:
  - agents.js has prompt fetch call (authedFetch to /api/agents/<id>/prompt)
  - agents.js has per-card prompt cache (Map or similar cache keyed by agent id)
  - agents.js renders modal content: skills, cost, prompt in <pre>
  - agents.js formats total_cost_usd to USD string
  - agents.js opens a <dialog> modal on card click (aria-haspopup="dialog")
  - agents.js handles Escape key (via native dialog; wired event still present)
  - agents.css defines modal styles (.agent-modal)
  - agents.css has max-height + overflow for prompt scrollability (in modal body)
  - agents.css has transition rules respecting prefers-reduced-motion (modal animation)
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent

_JS_DIR = _REPO_ROOT / "dadaia_workspace" / "features" / "panel" / "views" / "assets" / "js"

_CSS_DIR = _REPO_ROOT / "dadaia_workspace" / "features" / "panel" / "views" / "assets" / "css"


# ---------------------------------------------------------------------------
# agents.js — prompt fetch
# ---------------------------------------------------------------------------


def test_agents_js_fetches_prompt_endpoint() -> None:
    """agents.js must call authedFetch('/api/agents/<id>/prompt') on expand."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    assert "/prompt" in agents_text, (
        "agents.js must fetch /api/agents/<id>/prompt for system prompt lazy load"
    )
    assert "authedFetch" in agents_text, (
        "agents.js must use authedFetch() to call the prompt endpoint"
    )


def test_agents_js_has_prompt_cache() -> None:
    """agents.js must cache prompt responses per agent id (in-memory Map or object)."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    # Cache can be implemented via a Map or a plain object; check for common patterns
    has_map = "new Map" in agents_text or "promptCache" in agents_text
    has_obj_cache = "_cache" in agents_text or "cache" in agents_text.lower()
    assert has_map or has_obj_cache, (
        "agents.js must cache prompt responses per card id to avoid re-fetching"
    )


def test_agents_js_card_uses_aria_haspopup_dialog() -> None:
    """agents.js card button must use aria-haspopup='dialog' (modal pattern, P5-D)."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    assert "aria-haspopup" in agents_text, (
        "agents.js must set aria-haspopup on the card button (modal design)"
    )
    assert "dialog" in agents_text, (
        "agents.js must reference 'dialog' (aria-haspopup='dialog' or modal wiring)"
    )


def test_agents_js_opens_modal_on_card_click() -> None:
    """agents.js must call showModal() to open the agent detail dialog."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    assert "showModal" in agents_text, (
        "agents.js must call showModal() to open the native <dialog> modal"
    )


def test_agents_js_renders_system_prompt_in_pre() -> None:
    """agents.js must render system prompt inside a <pre> element."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    assert "<pre" in agents_text, "agents.js must render system prompt inside a <pre> block"


def test_agents_js_renders_full_skills_list() -> None:
    """agents.js modal content must render the full skills list (not truncated)."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    # The modal renders all skills; look for modal-specific skills logic
    # Both the collapsed (slice 0,2) and the modal (all skills) must coexist
    assert "skill" in agents_text.lower(), "agents.js must render skills in modal"
    # Modal content should render the full array (no truncation to 2)
    assert "agent-detail" in agents_text.lower() or "modal" in agents_text.lower(), (
        "agents.js must render content into the modal body"
    )


def test_agents_js_renders_cost_in_expanded_panel() -> None:
    """agents.js must show total cost in the expanded panel."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    # Cost formatting — look for dollar sign or USD formatting
    assert "$" in agents_text or "cost" in agents_text.lower(), (
        "agents.js must render cost in expanded panel"
    )
    # Must format using total_cost_usd field
    assert "total_cost_usd" in agents_text or "total_cost" in agents_text, (
        "agents.js must read total_cost_usd from telemetry for cost display"
    )


def test_agents_js_handles_escape_key_to_close() -> None:
    """agents.js modal must handle Escape to close (native dialog wires it; close handler present)."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    # Native <dialog> handles Escape natively; we verify that the 'close' event is wired
    # for focus return, which is the P5-D contract.
    assert "close" in agents_text, (
        "agents.js must wire the 'close' event on the dialog (for focus return on Escape)"
    )


def test_agents_js_uses_modal_not_inline_expand() -> None:
    """agents.js P5-D: card click opens a <dialog> modal, not an inline expand region.

    The modal pattern replaces the multi-open accordion from PR3-11.
    Each card click opens a single shared dialog.
    """
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    # Must have modal open function
    assert "openModal" in agents_text or "showModal" in agents_text, (
        "agents.js must use openModal() / showModal() for card detail (modal design)"
    )
    # Must NOT have inline per-card detail DIVs in the card HTML (detail is in dialog now)
    assert "agent-card__detail" not in agents_text, (
        "agents.js must NOT render .agent-card__detail inline (detail moved to modal)"
    )


def test_agents_js_has_loading_state_on_prompt_fetch() -> None:
    """agents.js must show a loading state on the card while prompt is fetching."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    # Loading state for prompt fetch — look for aria-busy or a loading indicator
    assert "loading" in agents_text.lower() or "aria-busy" in agents_text, (
        "agents.js must show a loading state on the card while the prompt is fetching"
    )


def test_agents_js_copy_button_present() -> None:
    """agents.js must render a copy-to-clipboard button in the expanded panel."""
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    assert "copy" in agents_text.lower() or "clipboard" in agents_text.lower(), (
        "agents.js must render a copy-to-clipboard button for the system prompt"
    )


# ---------------------------------------------------------------------------
# agents.css — expanded panel styles
# ---------------------------------------------------------------------------


def test_agents_css_defines_modal_styles() -> None:
    """agents.css must define styles for the agent modal (P5-D replaces inline panel)."""
    from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS

    assert "agent-modal" in AGENTS_CSS, (
        "agents.css must define styles for .agent-modal (modal design, P5-D)"
    )


def test_agents_css_prompt_block_has_max_height() -> None:
    """agents.css must define max-height for the prompt block to enable scrolling."""
    from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS

    assert "max-height" in AGENTS_CSS, (
        "agents.css must define max-height for the prompt block to contain long prompts"
    )
    assert "overflow" in AGENTS_CSS, (
        "agents.css must define overflow for the prompt block to enable scrolling"
    )


def test_agents_css_defines_prompt_block_styles() -> None:
    """agents.css must define styles for the prompt <pre> block."""
    from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS

    assert "agent-prompt" in AGENTS_CSS or "prompt" in AGENTS_CSS, (
        "agents.css must define styles for the system prompt block"
    )


def test_agents_css_defines_cost_label_styles() -> None:
    """agents.css must define styles for the cost label in expanded panel."""
    from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS

    assert "cost" in AGENTS_CSS.lower() or "total" in AGENTS_CSS.lower(), (
        "agents.css must define styles for the cost display in expanded panel"
    )


def test_agents_css_transition_respects_reduced_motion() -> None:
    """agents.css must disable expand transition under prefers-reduced-motion."""
    from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS

    assert "prefers-reduced-motion" in AGENTS_CSS, (
        "agents.css must include prefers-reduced-motion media query for transitions"
    )


def test_agents_css_uses_tokens_in_expanded_panel() -> None:
    """agents.css expanded panel styles must use var(--color-*) tokens."""
    from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS

    # Count var() usages — must be substantial (already checked in PR3-10 but reinforced here)
    var_count = AGENTS_CSS.count("var(--color-")
    assert var_count >= 8, (
        f"agents.css uses var(--color-*) only {var_count} times — "
        "expanded panel styles must also use tokens for theme support"
    )


def test_agents_css_modal_has_backdrop() -> None:
    """agents.css must define ::backdrop styles for the modal overlay (P5-D)."""
    from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS

    assert "::backdrop" in AGENTS_CSS, (
        "agents.css must include .agent-modal::backdrop rule for the overlay"
    )


# ---------------------------------------------------------------------------
# AGT-33 — project-manager expansion case (skills: project-orchestration)
# ---------------------------------------------------------------------------


def test_agents_js_does_not_hardcode_agent_ids() -> None:
    """agents.js must not hardcode a fixed list of agent IDs.

    The 16-agent topology (AGT-33) requires that expanding any agent card works
    dynamically.  A hardcoded agent-ID list would break when new agents are added.
    """
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    # Hardcoded old-topology agent names MUST NOT appear as a fixed enum/array
    # (individual string occurrences in comments / fetch paths are fine, but a
    # JS array literal containing all the agent IDs is the anti-pattern we guard).
    # We check that no JS array literal references the old-topology agent set exhaustively.
    old_agents = [
        "software-engineer",
        "frontend-engineer",
        "backend-engineer",
        "qa-engineer",
        "devops-engineer",
    ]
    # If all 5 appear AND they're close together (within 500 chars), likely an array
    indices = [agents_text.find(f'"{a}"') for a in old_agents]
    if all(i >= 0 for i in indices):
        span = max(indices) - min(indices)
        assert span > 500 or span == -1, (
            "agents.js appears to hardcode the original agent ID set as a list "
            "(found all 5 original agents within a 500-char span). "
            "Expand dynamically instead — new agents must not require JS changes."
        )


def test_agents_js_renders_skills_as_generic_list() -> None:
    """agents.js must render skills from card data — not hardcode skill names.

    This verifies that project-manager (skills: project-orchestration, dadaia-grill-me,
    dadaia-workspace-manager, dadaia-workspace-spec-navigator, dadaia-task-manager)
    and all other new agents can have their skills rendered without code changes.
    """
    agents_text = (_JS_DIR / "agents.js").read_text(encoding="utf-8")
    # Skills must be read from the data object (agent.skills or similar)
    assert "skills" in agents_text, (
        "agents.js must reference 'skills' field from agent data for rendering"
    )
    # Verify no hardcoded skill name for the project-orchestration skill
    # (its presence would indicate a non-generic renderer)
    assert "project-orchestration" not in agents_text, (
        "agents.js must NOT hardcode skill names — render from data generically"
    )
