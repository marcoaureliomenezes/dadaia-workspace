"""MANDATORY tier-taxonomy contract (v0.1.60 FR6 / Ruling 17 / AC-9).

The word "tier" names two distinct axes and this contract machine-enforces the split NOW
(not merely documents it):

  * the numeric frontmatter ``tier: 1/2/3`` = the agent dispatch/priority band;
  * the registry ``Tier`` (``deep``/``dispatch``/``fast``/``plugin``) = the model-cost class
    resolved from the frontmatter ``model:`` via ``core/model_registry``.

Assertions (AC-9):
  * every NON-plugin core agent (``public/agents/*.md`` without ``plugin: true``) carries a
    numeric ``tier`` AND a registry-known ``model`` — the 9 core keep ``claude-opus-4-8``
    (registry tier ``dispatch``);
  * the 3 plugin agents (the real bodies at ``public/plugins/*/agents/*.md``) carry
    ``tier: 3`` + ``model: claude-sonnet-4-6`` (registry tier ``plugin``).

This is NON-OPTIONAL: it must fail loudly if a core agent loses its tier/model, if a plugin
agent is put back on opus, or if the roster count drifts. The eventual source-level
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


def test_core_agents_carry_numeric_tier_and_opus_dispatch_model() -> None:
    registry = registry_by_claude_id()
    for md in _core_agents():
        fm = _frontmatter(md)
        tier = fm.get("tier")
        assert isinstance(tier, int) and not isinstance(tier, bool), (
            f"{md.name}: 'tier' must be a numeric band, got {tier!r}"
        )
        model = fm.get("model")
        assert model in registry, f"{md.name}: model {model!r} is not registry-known"
        assert model == "claude-opus-4-8", f"{md.name}: core agent must keep opus, got {model!r}"
        assert registry[str(model)].tier == "dispatch", (
            f"{md.name}: {model!r} must resolve to the 'dispatch' registry tier"
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
