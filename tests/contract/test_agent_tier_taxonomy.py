"""MANDATORY tier-taxonomy contract (v0.1.60 FR6 / Ruling 17 / AC-9).

The word "tier" names two distinct axes and this contract machine-enforces the split NOW
(not merely documents it):

  * the numeric frontmatter ``tier: 1/2/3`` = the agent dispatch/priority band;
  * the registry ``Tier`` (``deep``/``dispatch``/``fast``/``plugin``) = the model-cost class
    resolved from the frontmatter ``model:`` via ``core/model_registry``.

Assertions (AC-9, amended by the 2026-07-06 operator retier):
  * every NON-plugin core agent (``public/agents/*.md`` without ``plugin: true``) carries a
    numeric ``tier`` AND a registry-known ``model``. The core roster is split by operator
    decision (2026-07-06): FIVE agents run ``claude-fable-5`` (registry tier ``deep``) with a
    pinned per-agent Claude ``effort`` — product-engineer/high, project-auditor/high,
    ai-engineer/medium, software-engineer/low, qa-engineer/low — and the remaining FOUR
    (project-manager, software-architect, security-reviewer, code-reviewer) keep
    ``claude-opus-4-8`` (registry tier ``dispatch``) with no ``effort`` override;
  * the 3 plugin agents (the real bodies at ``public/plugins/*/agents/*.md``) carry
    ``tier: 3`` + ``model: claude-sonnet-4-6`` (registry tier ``plugin``).

This is NON-OPTIONAL: it must fail loudly if a core agent's model/effort drifts from the
pinned map, or if the roster count drifts. The eventual source-level
``tier:`` → ``dispatch_band:`` rename is tracked as backlog return ``tier-taxonomy-rename``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import dadaia_workspace
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


def test_core_roster_is_exactly_nine() -> None:
    assert len(_core_agents()) == 9, [p.name for p in _core_agents()]


def test_plugin_bodies_are_exactly_three() -> None:
    bodies = _plugin_body_agents()
    assert {p.stem for p in bodies} == {
        "frontend-engineer",
        "design-specialist",
        "devops-engineer",
    }, [p.name for p in bodies]


#: The operator-pinned Claude-axis assignment (2026-07-06): agent -> (model, effort).
#: ``effort`` is the per-agent Claude Code frontmatter override; ``None`` = no override
#: (the agent inherits the session effort).
_CORE_MODEL_EFFORT: dict[str, tuple[str, str | None]] = {
    "product-engineer": ("claude-fable-5", "high"),
    "project-auditor": ("claude-fable-5", "high"),
    "ai-engineer": ("claude-fable-5", "medium"),
    "software-engineer": ("claude-fable-5", "low"),
    "qa-engineer": ("claude-fable-5", "low"),
    "project-manager": ("claude-opus-4-8", None),
    "software-architect": ("claude-opus-4-8", None),
    "security-reviewer": ("claude-opus-4-8", None),
    "code-reviewer": ("claude-opus-4-8", None),
}

#: The registry tier each pinned model must resolve to.
_MODEL_TIER: dict[str, str] = {
    "claude-fable-5": "deep",
    "claude-opus-4-8": "dispatch",
}


def test_core_agents_carry_numeric_tier_and_pinned_model_effort() -> None:
    registry = registry_by_claude_id()
    seen: set[str] = set()
    for md in _core_agents():
        fm = _frontmatter(md)
        tier = fm.get("tier")
        assert isinstance(tier, int) and not isinstance(tier, bool), (
            f"{md.name}: 'tier' must be a numeric band, got {tier!r}"
        )
        assert md.stem in _CORE_MODEL_EFFORT, f"{md.name}: not in the pinned roster map"
        expected_model, expected_effort = _CORE_MODEL_EFFORT[md.stem]
        model = fm.get("model")
        assert model in registry, f"{md.name}: model {model!r} is not registry-known"
        assert model == expected_model, (
            f"{md.name}: pinned model is {expected_model!r}, got {model!r}"
        )
        assert registry[str(model)].tier == _MODEL_TIER[expected_model], (
            f"{md.name}: {model!r} must resolve to the {_MODEL_TIER[expected_model]!r} "
            "registry tier"
        )
        effort = fm.get("effort")
        assert effort == expected_effort, (
            f"{md.name}: pinned effort is {expected_effort!r}, got {effort!r}"
        )
        seen.add(md.stem)
    assert seen == set(_CORE_MODEL_EFFORT), (
        f"roster/map mismatch: missing {set(_CORE_MODEL_EFFORT) - seen}"
    )


def test_plugin_agents_carry_tier3_sonnet_plugin_model() -> None:
    registry = registry_by_claude_id()
    for md in _plugin_body_agents():
        fm = _frontmatter(md)
        assert fm.get("tier") == 3, (
            f"{md.name}: plugin agent must carry 'tier: 3', got {fm.get('tier')!r}"
        )
        model = fm.get("model")
        assert model == "claude-sonnet-4-6", (
            f"{md.name}: plugin agent must run on the sonnet/plugin tier, got {model!r}"
        )
        assert registry[str(model)].tier == "plugin", (
            f"{md.name}: {model!r} must resolve to the 'plugin' registry tier"
        )
