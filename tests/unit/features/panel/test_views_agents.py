"""Unit tests for views/agents.py — T-AM-16.

Covers:
  - render_agents_section() returns a non-empty string
  - Section carries role="tabpanel" and aria-labelledby="tab-agents"
  - Grid container id="agents-grid" is present
  - Empty-state id="agents-empty" element is present and hidden by default
  - Staleness banner id="agents-staleness-banner" is present, hidden, role="status"
  - No inline agent data serialized into HTML (data is JS-fetched)
"""

from dadaia_workspace.features.panel.views.agents import render_agents_section


def test_render_agents_section_returns_string() -> None:
    """render_agents_section() must return a non-empty string."""
    result = render_agents_section()
    assert isinstance(result, str)
    assert len(result) > 0


def test_section_has_role_tabpanel() -> None:
    """Section must carry role="tabpanel" and aria-labelledby="tab-agents"."""
    html = render_agents_section()
    assert 'role="tabpanel"' in html
    assert 'aria-labelledby="tab-agents"' in html


def test_section_has_grid_container() -> None:
    """Section must include a grid container with id="agents-grid"."""
    html = render_agents_section()
    assert 'id="agents-grid"' in html


def test_section_has_empty_state() -> None:
    """Section must include empty-state element with id="agents-empty", hidden by default."""
    html = render_agents_section()
    assert 'id="agents-empty"' in html
    # The empty state must be hidden by default (hidden attribute present)
    assert "agents-empty" in html
    # Find the element and confirm hidden attribute
    idx = html.find('id="agents-empty"')
    # Get surrounding context (the element opening tag)
    chunk = html[max(0, idx - 20):idx + 100]
    assert "hidden" in chunk


def test_section_has_staleness_banner() -> None:
    """Section must include staleness banner with id="agents-staleness-banner",
    hidden by default, and role="status"."""
    html = render_agents_section()
    assert 'id="agents-staleness-banner"' in html
    assert 'role="status"' in html
    # Must be hidden by default
    idx = html.find('id="agents-staleness-banner"')
    chunk = html[max(0, idx - 20):idx + 120]
    assert "hidden" in chunk


def test_no_inline_data() -> None:
    """Server must NOT serialize agent data into HTML; JS fetches dynamically.

    Checks that no agent-specific data patterns appear that would suggest
    server-side rendering of agent records.
    """
    html = render_agents_section()
    # Should not contain JSON-like agent data patterns
    assert '"agent_id"' not in html
    assert '"total_cost_usd"' not in html
    assert '"dominant_model"' not in html
    assert '"session_count"' not in html
