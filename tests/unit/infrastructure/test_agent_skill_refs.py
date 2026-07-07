"""Agent skill-ref integrity — core + plugin-aware sweep (T-63-40, v0.1.63 FR6, AC-7).

``check_agent_skill_refs`` is the D-CX-SKILLS surface: every ``skills:`` frontmatter ref
in a public agent must resolve to a real skill dir. Read fact 6 (SPEC v0.1.63): pre-fix
the check swept ONLY ``public/agents/*.md`` — a bogus ref in a pack agent under
``public/plugins/<pack>/agents/`` produced ZERO report lines. This module locks:

* the core-agent behavior (unchanged, additive sweep — fate ledger);
* AC-7 RED-first: a bogus pack-agent ref yields a ``[drift]`` line; resolution is
  against ``public/skills/`` UNION that pack's own ``plugins/<pack>/skills/``;
* pack isolation: a ref to ANOTHER pack's skill does NOT resolve.

The ``[drift]`` prefix flows through the existing ``public doctor`` / ``public stage``
ref-drift handling (``cli/commands/public.py`` — non-zero on drift), per ADR-C3.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.codex_doctor import check_agent_skill_refs

_AGENT_TEMPLATE = """---
name: {name}
description: test agent
skills:
{skills}
---

body
"""


def _mk_skill(base: Path, slug: str) -> None:
    d = base / slug
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {slug}\n---\n", encoding="utf-8")


def _mk_agent(path: Path, name: str, skills: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(f"  - {s}" for s in skills)
    path.write_text(_AGENT_TEMPLATE.format(name=name, skills=lines), encoding="utf-8")


def _public_tree(tmp_path: Path) -> Path:
    """Synthetic public dir: 1 core skill, 2 packs with 1 skill each."""
    public = tmp_path / "public"
    _mk_skill(public / "skills", "core-skill")
    _mk_skill(public / "plugins" / "pack-a" / "skills", "pack-a-skill")
    _mk_skill(public / "plugins" / "pack-b" / "skills", "pack-b-skill")
    return public


class TestCoreAgentSweepUnchanged:
    """Fate ledger: the pre-existing core-agent behavior survives the additive sweep."""

    def test_core_agent_bogus_ref_still_reported(self, tmp_path: Path) -> None:
        public = _public_tree(tmp_path)
        _mk_agent(public / "agents" / "core-agent.md", "core-agent", ["core-skill", "ghost"])
        out = check_agent_skill_refs(public)
        assert out == [
            "[drift] agent:core-agent: frontmatter references "
            "non-existent skill 'ghost' (D-CX-SKILLS)"
        ]

    def test_core_agent_does_not_resolve_against_pack_skills(self, tmp_path: Path) -> None:
        """Core agents resolve against public/skills/ ONLY — pack skills are not global."""
        public = _public_tree(tmp_path)
        _mk_agent(public / "agents" / "core-agent.md", "core-agent", ["pack-a-skill"])
        out = check_agent_skill_refs(public)
        assert len(out) == 1 and out[0].startswith("[drift] agent:core-agent:")


class TestPluginAwareSweep:
    """AC-7: pack-agent refs resolve against public/skills/ ∪ the pack's own skills/."""

    def test_bogus_pack_agent_ref_yields_drift_line(self, tmp_path: Path) -> None:
        """RED-first (read fact 6): pre-fix this produced ZERO report lines."""
        public = _public_tree(tmp_path)
        _mk_agent(
            public / "plugins" / "pack-a" / "agents" / "pack-agent.md",
            "pack-agent",
            ["pack-a-skill", "no-such-skill"],
        )
        out = check_agent_skill_refs(public)
        drift = [r for r in out if r.startswith("[drift]")]
        assert drift == [
            "[drift] plugin-agent:pack-a/pack-agent: frontmatter references "
            "non-existent skill 'no-such-skill' (D-CX-SKILLS)"
        ]

    def test_pack_agent_resolves_union_of_core_and_own_pack(self, tmp_path: Path) -> None:
        public = _public_tree(tmp_path)
        _mk_agent(
            public / "plugins" / "pack-a" / "agents" / "pack-agent.md",
            "pack-agent",
            ["core-skill", "pack-a-skill"],
        )
        assert check_agent_skill_refs(public) == []

    def test_pack_agent_does_not_resolve_foreign_pack_skill(self, tmp_path: Path) -> None:
        public = _public_tree(tmp_path)
        _mk_agent(
            public / "plugins" / "pack-a" / "agents" / "pack-agent.md",
            "pack-agent",
            ["pack-b-skill"],
        )
        out = check_agent_skill_refs(public)
        assert len(out) == 1
        assert out[0].startswith("[drift] plugin-agent:pack-a/pack-agent:")
        assert "'pack-b-skill'" in out[0]

    def test_no_plugins_dir_is_a_noop(self, tmp_path: Path) -> None:
        public = tmp_path / "public"
        _mk_skill(public / "skills", "core-skill")
        _mk_agent(public / "agents" / "core-agent.md", "core-agent", ["core-skill"])
        assert check_agent_skill_refs(public) == []
