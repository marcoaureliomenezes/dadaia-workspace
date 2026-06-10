"""Unit tests for views/agents.py.

Covers the static HTML skeleton contract (T-016-P09): agents are a sub-section
inside the Ops tab (no longer a top-level tabpanel). Agent cards are populated
client-side via JS fetch, so the server must NOT serialise agent data into the HTML.

The skeleton is exercised by asserting on its rendered structure (distinct ids,
roles, hidden-by-default states) rather than smoke-asserting it is a non-empty
string — each assertion below fails on a real regression that drops a DOM hook the
client JS depends on.
"""

from dadaia_workspace.features.panel.views.agents import render_agents_section


def test_agents_subsection_structure() -> None:
    """The Ops agents sub-section exposes every DOM hook the client JS targets.

    After T-016-P09 the container is a sub-section (``ops-subsection-agents``), NOT a
    ``role="tabpanel"`` target. The grid, empty-state, and staleness banner ids must
    all be present so the fetch-driven UI can populate and toggle them.
    """
    html = render_agents_section()

    # Sub-section container (replaces the former top-level tabpanel).
    assert 'id="ops-subsection-agents"' in html
    # Grid the client JS injects cards into.
    assert 'id="agents-grid"' in html
    # Empty-state + staleness banner, both present.
    assert 'id="agents-empty"' in html
    assert 'id="agents-staleness-banner"' in html
    assert 'role="status"' in html


def test_agents_empty_state_and_staleness_banner_hidden_by_default() -> None:
    """Both the empty-state and the staleness banner ship hidden; JS reveals them."""
    html = render_agents_section()

    empty_idx = html.find('id="agents-empty"')
    assert "hidden" in html[max(0, empty_idx - 20) : empty_idx + 100]

    banner_idx = html.find('id="agents-staleness-banner"')
    assert "hidden" in html[max(0, banner_idx - 20) : banner_idx + 120]


def test_no_inline_agent_data_serialized() -> None:
    """Server must NOT serialise agent records into HTML; JS fetches them dynamically.

    A regression that starts server-side-rendering agent data would re-introduce one
    of these JSON keys into the skeleton.
    """
    html = render_agents_section()
    assert '"agent_id"' not in html
    assert '"total_cost_usd"' not in html
    assert '"dominant_model"' not in html
    assert '"session_count"' not in html
