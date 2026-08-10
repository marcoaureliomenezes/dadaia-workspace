"""Agent skill-ref integrity (D-CX-SKILLS).

``check_agent_skill_refs`` sweeps every ``skills:`` frontmatter ref in a public core
agent; a bogus ref yields a ``[drift]`` line that flows through ``public doctor`` /
``public stage`` ref-drift handling (non-zero on drift).
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
