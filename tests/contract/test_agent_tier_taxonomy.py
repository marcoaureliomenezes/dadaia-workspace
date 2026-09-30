"""Intent: CONTRACT — core.model_registry FR2 table and ruling G-1 (Fable never on dd-code-reviewer)

MANDATORY tier-taxonomy contract (v0.1.60 FR6 / Ruling 17 — reworked v0.1.65 FR9).

The word "tier" names two distinct axes and this contract machine-enforces the split:

  * the numeric frontmatter ``dispatch_band: 1/2/3`` = the agent dispatch/priority band
    (renamed from the legacy ``tier:`` spelling in v0.1.64 FR5);
  * the registry ``Tier`` (``deep``/``dispatch``/``fast``/``standard``) = the model-cost
    class resolved from a Claude model id via ``core/model_registry``.

v0.1.65 rework (FR9): the staged core agent bodies are now MODEL-AGNOSTIC templates
(FR1 — render-at-install injects the resolved ``model:``/``effort:``), so this contract
stops pinning per-file frontmatter rosters and instead pins the **built-in template
registry** in ``core/model_registry.py`` (sa-agent-model-resolved-by-two-modules: one module):

  (a) the full contents of the 3 built-in templates (the FR2 table, verbatim);
  (b) ``balanced`` is the default;
  (c) no template assigns ``claude-fable-5`` to dd-code-reviewer (operator ruling G-1);
  (d) every template model resolves in REGISTRY with the expected tier;
  (e) staged core bodies carry NO ``model:``/``effort:`` frontmatter (AC-1);
  (f) roster count: exactly the 9 core agents.

This is NON-OPTIONAL: it must fail loudly if a template roster drifts from the FR2
table, if a staged core body re-grows a hardcoded model, or if the roster count drifts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import dadaia_workspace
from dadaia_workspace.core.model_registry import (
    CORE_AGENTS,
    TEMPLATES,
    is_fable_model,
    registry_by_claude_id,
)

pytestmark = pytest.mark.contract

_PUBLIC = Path(dadaia_workspace.__file__).resolve().parent / "public"


def _frontmatter(md: Path) -> dict[str, object]:
    text = md.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{md} has no YAML frontmatter"
    end = text.find("\n---\n", 4)
    assert end != -1, f"{md} has an unterminated frontmatter block"
    parsed = yaml.safe_load(text[4 : end + 1])
    assert isinstance(parsed, dict), f"{md} frontmatter is not a mapping"
    return parsed


def _core_agents() -> list[Path]:
    """Core agents in public/agents/."""
    return sorted((_PUBLIC / "agents").glob("*.md"))


# ---------------------------------------------------------------------------
# (g) roster counts unchanged
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# (a) the 3 built-in templates, verbatim (the SPEC FR2 table)
# ---------------------------------------------------------------------------

#: The FR2 table, pinned verbatim: template id -> agent -> (model, effort).
_EXPECTED_TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "balanced": {
        "dd-product-engineer": ("claude-opus-5-5", "high"),
        "dd-code-reviewer": ("claude-opus-5-5", "high"),
        "dd-software-engineer": ("claude-opus-5-5", "low"),
    },
    "max-quality": {
        "dd-product-engineer": ("claude-fable-5-1", "high"),
        "dd-code-reviewer": ("claude-opus-5-5", "xhigh"),
        "dd-software-engineer": ("claude-opus-5-5", "medium"),
    },
    "economy": {
        "dd-product-engineer": ("claude-opus-5-5", "high"),
        "dd-code-reviewer": ("claude-sonnet-5", "high"),
        "dd-software-engineer": ("claude-sonnet-5", "medium"),
    },
}

#: (d) the registry tier each template model must resolve to.
_MODEL_TIER: dict[str, str] = {
    "claude-fable-5": "deep",
    "claude-fable-5-1": "deep",
    "claude-opus-5": "dispatch",
    "claude-opus-5-5": "dispatch",
    "claude-sonnet-5": "standard",
}


def test_builtin_templates_pin_fr2_table_default_and_registry_tiers() -> None:
    """(a)+(b)+(d): the FR2 table verbatim, ``balanced`` is the single default, and every
    template cell's model resolves in REGISTRY with the pinned tier."""
    assert list(TEMPLATES) == list(_EXPECTED_TEMPLATES)  # balanced first: the default
    registry = registry_by_claude_id()
    for template_id, expected_roster in _EXPECTED_TEMPLATES.items():
        cells = TEMPLATES[template_id]
        actual = {agent: (a.model, a.effort) for agent, a in cells.items()}
        assert actual == expected_roster, (
            f"template {template_id!r} drifted from the FR2 table: {actual}"
        )
        for agent, assignment in cells.items():
            assert assignment.model in registry, (
                f"{template_id}/{agent}: model {assignment.model!r} not registry-known"
            )
            assert assignment.model in _MODEL_TIER, (
                f"{template_id}/{agent}: model {assignment.model!r} not in the pinned "
                "tier map — extend _MODEL_TIER deliberately"
            )
            assert registry[assignment.model].tier == _MODEL_TIER[assignment.model], (
                f"{template_id}/{agent}: {assignment.model!r} must resolve to the "
                f"{_MODEL_TIER[assignment.model]!r} registry tier"
            )


def test_no_template_assigns_fable_to_security_reviewer() -> None:
    """(c): G-1 — Fable is NEVER assigned to dd-code-reviewer, in any template."""
    for template_id, cells in TEMPLATES.items():
        assert not is_fable_model(cells["dd-code-reviewer"].model), (
            f"template {template_id!r} assigns Fable to dd-code-reviewer (G-1 violation)"
        )


# ---------------------------------------------------------------------------
# (e) staged core bodies are model-agnostic; dispatch_band stays numeric+mandatory
# ---------------------------------------------------------------------------


def test_core_agent_frontmatter_tiers() -> None:
    """(f): roster count is exactly the 9 core agents. (e): staged core bodies carry
    ``dispatch_band`` but NO ``model:``/``effort:`` (v0.1.65 FR1: the model/effort
    pinning moved from per-file frontmatter to the template registry, asserted above;
    the projected files carry them, the staged sources must not)."""
    assert len(_core_agents()) == 3, [p.name for p in _core_agents()]
    assert {p.stem for p in _core_agents()} == set(CORE_AGENTS)

    seen: set[str] = set()
    for md in _core_agents():
        fm = _frontmatter(md)
        dispatch_band = fm.get("dispatch_band")
        assert isinstance(dispatch_band, int) and not isinstance(dispatch_band, bool), (
            f"{md.name}: 'dispatch_band' must be a numeric band, got {dispatch_band!r}"
        )
        assert "model" not in fm, (
            f"{md.name}: staged core body must be model-agnostic (FR1/AC-1); "
            f"found model: {fm.get('model')!r}"
        )
        assert "effort" not in fm, (
            f"{md.name}: staged core body must not pin 'effort' (FR1/AC-1); "
            f"found effort: {fm.get('effort')!r}"
        )
        seen.add(md.stem)
    assert seen == set(CORE_AGENTS), f"roster/template mismatch: missing {set(CORE_AGENTS) - seen}"
