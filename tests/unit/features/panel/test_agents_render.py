"""PR4-19 — JS rendering smoke test: agents.js must wire data-tier on each card.

These tests are intentionally lightweight source-grep assertions.  They verify
that the JS renderer sets the `data-tier` attribute on card elements and exposes
a `tierLabel` helper — the full runtime behaviour is covered by E2E (qa-engineer).
"""

from __future__ import annotations

from pathlib import Path

_JS_PATH = (
    Path(__file__).parents[4]
    / "dadaia_workspace/features/panel/views/assets/js/agents.js"
)


def test_agents_js_sets_data_tier_attribute() -> None:
    """agents.js DOM renderer must set the data-tier attribute on each card element."""
    src = _JS_PATH.read_text()
    assert "data-tier" in src, (
        "agents.js must wire data-tier attribute per agent tier"
    )
    assert "tier" in src.lower(), (
        "agents.js must reference agent.tier"
    )


def test_agents_js_has_tier_label_helper() -> None:
    """agents.js must include a tierLabel helper mapping tier numbers to text."""
    src = _JS_PATH.read_text()
    assert "tierLabel" in src, (
        "agents.js must define a tierLabel() helper function"
    )


def test_agents_js_tier_label_all_three_values() -> None:
    """tierLabel must map 1 → 'T1 Orchestrator', 2 → 'T2 Curator', 3 → 'T3 Leaf'."""
    src = _JS_PATH.read_text()
    assert "T1 Orchestrator" in src, "agents.js must produce 'T1 Orchestrator' label"
    assert "T2 Curator" in src, "agents.js must produce 'T2 Curator' label"
    assert "T3 Leaf" in src, "agents.js must produce 'T3 Leaf' label"


def test_agents_js_tier_label_element_rendered() -> None:
    """agents.js must render the .agent-card__tier-label span in the card HTML."""
    src = _JS_PATH.read_text()
    assert "agent-card__tier-label" in src, (
        "agents.js must render the .agent-card__tier-label element per design spec"
    )
