"""T-70-01/02 (FR1): agent_tier doc<->schema consistency.

The memory-frontmatter-v1 schema (``additionalProperties: false``) has
correctly rejected ``agent_tier`` since v0.1.61 (deprecated v0.1.53). Four
authoring-contract surfaces must state that truth accurately, not the
opposite ("the schema tolerates it" / "the schema retains a deprecated
optional agent_tier property"). This is an executed-path test over the real
on-disk files (not a schema test — see
``test_lint_memory_atoms.py::test_agent_tier_property_absent_from_schema``
for the schema-side pin).
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

# The three AGENTS.md copies carry the byte-identical false claim string.
_AGENTS_MD_LIE = "the schema tolerates it"
_AGENTS_MD_COPIES = [
    _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold" / "memory" / "AGENTS.md",
    _REPO_ROOT / "dadaia_workspace" / "public" / "data" / "memory-AGENTS.md",
    _REPO_ROOT / "specs" / "memory" / "AGENTS.md",
]

# architecture.md carries a differently-worded false claim.
_ARCHITECTURE_MD = _REPO_ROOT / "specs" / "memory" / "architecture.md"
_ARCHITECTURE_MD_LIE = "retains a deprecated optional `agent_tier`"

# Truth markers: each corrected surface must say agent_tier is
# rejected/removed by the schema.
_TRUTH_MARKERS = ("rejects", "reject", "removed", "dropped")


def test_agents_md_copies_do_not_claim_schema_tolerates_agent_tier() -> None:
    """None of the three AGENTS.md copies may claim the schema tolerates agent_tier."""
    offenders = []
    for path in _AGENTS_MD_COPIES:
        text = path.read_text(encoding="utf-8")
        if _AGENTS_MD_LIE in text:
            offenders.append(str(path.relative_to(_REPO_ROOT)))
    assert offenders == [], f"These files still falsely claim '{_AGENTS_MD_LIE}': {offenders}"


def test_architecture_md_does_not_claim_schema_retains_agent_tier() -> None:
    """architecture.md may not claim the schema 'retains' agent_tier as optional."""
    text = _ARCHITECTURE_MD.read_text(encoding="utf-8")
    assert _ARCHITECTURE_MD_LIE not in text, (
        f"architecture.md still falsely claims '{_ARCHITECTURE_MD_LIE}'"
    )


def test_agents_md_copies_state_agent_tier_is_rejected_or_removed() -> None:
    """Each AGENTS.md copy must state agent_tier is rejected/removed, near the field."""
    missing = []
    for path in _AGENTS_MD_COPIES:
        text = path.read_text(encoding="utf-8")
        idx = text.find("agent_tier")
        assert idx != -1, f"{path} no longer mentions agent_tier at all"
        # Look at the surrounding window (a couple sentences) for a truth marker.
        window = text[idx : idx + 400].lower()
        if not any(marker in window for marker in _TRUTH_MARKERS):
            missing.append(str(path.relative_to(_REPO_ROOT)))
    assert missing == [], (
        f"These files mention agent_tier but do not state it is rejected/removed: {missing}"
    )


def test_architecture_md_states_agent_tier_is_rejected_or_removed() -> None:
    """architecture.md must state agent_tier is rejected/removed, near the field."""
    text = _ARCHITECTURE_MD.read_text(encoding="utf-8")
    idx = text.find("agent_tier")
    assert idx != -1, "architecture.md no longer mentions agent_tier at all"
    window = text[idx : idx + 400].lower()
    assert any(marker in window for marker in _TRUTH_MARKERS), (
        "architecture.md mentions agent_tier but does not state it is rejected/removed"
    )
