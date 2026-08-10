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

import pytest

from dadaia_workspace.infrastructure.codex_doctor import check_agent_skill_refs


def _rendered(result: object) -> list[str]:
    """Legacy string view of a typed doctor result (DoctorReport | list[DoctorLine])."""
    if hasattr(result, "rendered"):
        return result.rendered()  # type: ignore[attr-defined, no-any-return]
    return [
        line.render() if hasattr(line, "render") else str(line)
        for line in result  # type: ignore[union-attr]
    ]


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


@pytest.mark.parametrize(
    ("skills", "expect_drift"),
    [
        pytest.param(["core-skill", "ghost"], True, id="bogus-ref-reported"),
        pytest.param(["pack-a-skill"], True, id="does-not-resolve-against-pack-skills-global"),
    ],
)
def test_core_agent_sweep(tmp_path: Path, skills: list[str], expect_drift: bool) -> None:
    public = _public_tree(tmp_path)
    _mk_agent(public / "agents" / "core-agent.md", "core-agent", skills)
    out = _rendered(check_agent_skill_refs(public))
    if expect_drift:
        assert len(out) == 1
        assert out[0].startswith("[drift] agent:core-agent:")
    else:
        assert out == []

    if skills == ["core-skill", "ghost"]:
        # RED-first message shape (D-CX-SKILLS) — verbatim string kept once.
        assert out == [
            "[drift] agent:core-agent: frontmatter references "
            "non-existent skill 'ghost' (D-CX-SKILLS)"
        ]


@pytest.mark.parametrize(
    ("skills", "expected"),
    [
        pytest.param(
            ["pack-a-skill", "no-such-skill"],
            [
                "[drift] plugin-agent:pack-a/pack-agent: frontmatter references "
                "non-existent skill 'no-such-skill' (D-CX-SKILLS)"
            ],
            id="bogus-pack-agent-ref-yields-drift-line",
        ),
        pytest.param(["core-skill", "pack-a-skill"], [], id="resolves-union-core-and-own-pack"),
        pytest.param(
            ["pack-b-skill"], "foreign-pack-not-resolved", id="foreign-pack-skill-not-resolved"
        ),
    ],
)
def test_pack_agent_sweep(tmp_path: Path, skills: list[str], expected: list[str] | str) -> None:
    public = _public_tree(tmp_path)
    _mk_agent(public / "plugins" / "pack-a" / "agents" / "pack-agent.md", "pack-agent", skills)
    out = _rendered(check_agent_skill_refs(public))
    drift = [r for r in out if r.startswith("[drift]")]
    if expected == "foreign-pack-not-resolved":
        assert len(drift) == 1
        assert drift[0].startswith("[drift] plugin-agent:pack-a/pack-agent:")
        assert "'pack-b-skill'" in drift[0]
    else:
        assert drift == expected


def test_no_plugins_dir_is_a_noop(tmp_path: Path) -> None:
    public = tmp_path / "public"
    _mk_skill(public / "skills", "core-skill")
    _mk_agent(public / "agents" / "core-agent.md", "core-agent", ["core-skill"])
    assert check_agent_skill_refs(public) == []
