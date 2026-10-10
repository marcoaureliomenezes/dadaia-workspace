"""Persona frontmatter contract: numeric ``dispatch_band``, model-agnostic staged bodies.

The template table, tier map and G-1 pin live in ``test_model_registry.py``.
"""

from __future__ import annotations

from pathlib import Path

import yaml

import dadaia_workspace
from dadaia_workspace.core.model_registry import CORE_AGENTS

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
