"""MANDATORY tier-taxonomy contract (v0.1.60 FR6 / Ruling 17 — reworked v0.1.65 FR9).

The word "tier" names two distinct axes and this contract machine-enforces the split:

  * the numeric frontmatter ``dispatch_band: 1/2/3`` = the agent dispatch/priority band
    (renamed from the legacy ``tier:`` spelling in v0.1.64 FR5);
  * the registry ``Tier`` (``deep``/``dispatch``/``fast``/``plugin``) = the model-cost
    class resolved from a Claude model id via ``core/model_registry``.

v0.1.65 rework (FR9): the staged core agent bodies are now MODEL-AGNOSTIC templates
(FR1 — render-at-install injects the resolved ``model:``/``effort:``), so this contract
stops pinning per-file frontmatter rosters and instead pins the **built-in template
registry** in ``core/agent_model_templates.py``:

  (a) the full contents of the 3 built-in templates (the FR2 table, verbatim);
  (b) ``balanced`` is the default;
  (c) no template assigns ``claude-fable-5`` to security-reviewer (operator ruling G-1);
  (d) every template model resolves in REGISTRY with the expected tier;
  (e) staged core bodies carry NO ``model:``/``effort:`` frontmatter (AC-1);
  (f) plugin pack bodies carry ``dispatch_band: 3`` + ``model: claude-sonnet-5``
      (registry tier ``plugin``);
  (g) roster counts unchanged: 9 core / 3 plugin.

This is NON-OPTIONAL: it must fail loudly if a template roster drifts from the FR2
table, if a staged core body re-grows a hardcoded model, or if the roster count drifts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import dadaia_workspace
from dadaia_workspace.core.agent_model_templates import (
    CORE_AGENTS,
    default_template,
    list_templates,
)
from dadaia_workspace.core.model_registry import registry_by_claude_id

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
    """Non-plugin core agents in public/agents/ (excludes the plugin stubs)."""
    return [
        p
        for p in sorted((_PUBLIC / "agents").glob("*.md"))
        if _frontmatter(p).get("plugin") is not True
    ]


def _plugin_body_agents() -> list[Path]:
    """The real plugin agent bodies distributed in the packs (W3 content)."""
    return sorted((_PUBLIC / "plugins").glob("*/agents/*.md"))


# ---------------------------------------------------------------------------
# (g) roster counts unchanged
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# (a) the 3 built-in templates, verbatim (the SPEC FR2 table)
# ---------------------------------------------------------------------------

#: The FR2 table, pinned verbatim: template id -> agent -> (model, effort).
_EXPECTED_TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "balanced": {
        "project-manager": ("claude-fable-5", "high"),
        "software-architect": ("claude-fable-5", "high"),
        "product-engineer": ("claude-opus-5", "high"),
        "project-auditor": ("claude-opus-5", "xhigh"),
        "security-reviewer": ("claude-opus-5", "xhigh"),
        "code-reviewer": ("claude-opus-5", "high"),
        "ai-engineer": ("claude-sonnet-5", "high"),
        "software-engineer": ("claude-sonnet-5", "xhigh"),
        "qa-engineer": ("claude-sonnet-5", "high"),
    },
    "subscription-saver": {
        "project-manager": ("claude-opus-5", "high"),
        "software-architect": ("claude-opus-5", "high"),
        "product-engineer": ("claude-sonnet-5", "xhigh"),
        "project-auditor": ("claude-sonnet-5", "xhigh"),
        "security-reviewer": ("claude-opus-5", "high"),
        "code-reviewer": ("claude-sonnet-5", "xhigh"),
        "ai-engineer": ("claude-sonnet-5", "high"),
        "software-engineer": ("claude-sonnet-5", "xhigh"),
        "qa-engineer": ("claude-sonnet-5", "high"),
    },
    "max-quality": {
        "project-manager": ("claude-fable-5", "high"),
        "software-architect": ("claude-fable-5", "high"),
        "product-engineer": ("claude-fable-5", "high"),
        "project-auditor": ("claude-fable-5", "high"),
        "security-reviewer": ("claude-opus-5", "xhigh"),
        "code-reviewer": ("claude-opus-5", "xhigh"),
        "ai-engineer": ("claude-opus-5", "medium"),
        "software-engineer": ("claude-sonnet-5", "xhigh"),
        "qa-engineer": ("claude-opus-5", "high"),
    },
}

#: (d) the registry tier each template model must resolve to.
_MODEL_TIER: dict[str, str] = {
    "claude-fable-5": "deep",
    "claude-opus-5": "dispatch",
    "claude-sonnet-5": "plugin",
}


def test_builtin_templates_pin_fr2_table_default_and_registry_tiers() -> None:
    """(a)+(b)+(d): the FR2 table verbatim, ``balanced`` is the single default, and every
    template cell's model resolves in REGISTRY with the pinned tier."""
    templates = {t.id: t for t in list_templates()}
    assert set(templates) == set(_EXPECTED_TEMPLATES), sorted(templates)
    registry = registry_by_claude_id()
    for template_id, expected_roster in _EXPECTED_TEMPLATES.items():
        template = templates[template_id]
        actual = {agent: (a.model, a.effort) for agent, a in template.assignments.items()}
        assert actual == expected_roster, (
            f"template {template_id!r} drifted from the FR2 table: {actual}"
        )
        for agent, assignment in template.assignments.items():
            assert assignment.model in registry, (
                f"{template.id}/{agent}: model {assignment.model!r} not registry-known"
            )
            assert assignment.model in _MODEL_TIER, (
                f"{template.id}/{agent}: model {assignment.model!r} not in the pinned "
                "tier map — extend _MODEL_TIER deliberately"
            )
            assert registry[assignment.model].tier == _MODEL_TIER[assignment.model], (
                f"{template.id}/{agent}: {assignment.model!r} must resolve to the "
                f"{_MODEL_TIER[assignment.model]!r} registry tier"
            )

    assert default_template().id == "balanced"
    defaults = [t.id for t in list_templates() if t.default]
    assert defaults == ["balanced"]


def test_no_template_assigns_fable_to_security_reviewer() -> None:
    """(c): G-1 — Fable is NEVER assigned to security-reviewer, in any template."""
    for template in list_templates():
        assert template.assignments["security-reviewer"].model != "claude-fable-5", (
            f"template {template.id!r} assigns Fable to security-reviewer (G-1 violation)"
        )


# ---------------------------------------------------------------------------
# (e) staged core bodies are model-agnostic; dispatch_band stays numeric+mandatory
# ---------------------------------------------------------------------------


def test_core_and_plugin_agent_frontmatter_tiers() -> None:
    """(g): roster counts unchanged (9 core, 3 plugin). (e): staged core bodies carry
    ``dispatch_band`` but NO ``model:``/``effort:`` (v0.1.65 FR1: the model/effort
    pinning moved from per-file frontmatter to the template registry, asserted above;
    the projected files carry them, the staged sources must not). (f): plugin pack
    bodies carry ``dispatch_band: 3`` + ``model: claude-sonnet-5`` (registry tier
    ``plugin``)."""
    assert len(_core_agents()) == 9, [p.name for p in _core_agents()]
    assert {p.stem for p in _core_agents()} == set(CORE_AGENTS)
    bodies = _plugin_body_agents()
    assert {p.stem for p in bodies} == {
        "frontend-engineer",
        "design-specialist",
        "devops-engineer",
    }, [p.name for p in bodies]

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

    registry = registry_by_claude_id()
    for md in _plugin_body_agents():
        fm = _frontmatter(md)
        assert fm.get("dispatch_band") == 3, (
            f"{md.name}: plugin agent must carry 'dispatch_band: 3', "
            f"got {fm.get('dispatch_band')!r}"
        )
        model = fm.get("model")
        assert model == "claude-sonnet-5", (
            f"{md.name}: plugin agent must carry the pack default "
            f"'claude-sonnet-5' (G-4/D-5), got {model!r}"
        )
        assert registry[str(model)].tier == "plugin", (
            f"{md.name}: {model!r} must resolve to the 'plugin' registry tier"
        )
