"""AC-6 positive 16/16 handoff-v1.2 + self_pull instruction adoption (v0.1.62 FR4 / QA62-3).

Enumerates the **16 emission-instruction surfaces** and asserts each carries BOTH the
``handoff-v1.2`` and the ``self_pull`` instruction tokens — a surface missing either
token FAILS, naming the surface. The 16 surfaces (file-enumerated, never glob-only):

* the 12 agent bodies — 9 core ``public/agents/*.md`` + 3 plugin
  ``public/plugins/*/agents/*.md``;
* the ``dadaia-handoff-emitter`` skill's TWO JSON examples (each counted as its own
  surface — both must model the v1.2 + ``self_pull`` shape);
* ``public/data/handoff-AGENTS.md``;
* ``public/lifecycle_fragments/shared/output-handoff.md``.

A roster-completeness assert backs the enumeration: a renamed/removed agent body or a
new plugin agent body not added here fails loudly instead of silently shrinking the
contract. Sequencing per Ruling 62-A: these body-prose edits land BEFORE v0.1.63's
plugin-agent frontmatter and v0.1.64's ``tier:`` rename on the same files; v0.1.64
re-verifies this contract post-rename.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"

_TOKEN_V12 = "handoff-v1.2"
_TOKEN_SELF_PULL = "self_pull"

#: The 9 core agent bodies carrying the emission instruction. The 3 remaining files in
#: ``public/agents/`` (design-specialist, devops-engineer, frontend-engineer) are the
#: plugin STUBS — no behavior, no emission instruction; their real bodies live in the
#: plugin packs and are enumerated in _PLUGIN_AGENT_BODIES.
_CORE_AGENT_BODIES: tuple[str, ...] = (
    "agents/ai-engineer.md",
    "agents/code-reviewer.md",
    "agents/product-engineer.md",
    "agents/project-auditor.md",
    "agents/project-manager.md",
    "agents/qa-engineer.md",
    "agents/security-reviewer.md",
    "agents/software-architect.md",
    "agents/software-engineer.md",
)

_PLUGIN_STUBS: frozenset[str] = frozenset(
    {
        "agents/design-specialist.md",
        "agents/devops-engineer.md",
        "agents/frontend-engineer.md",
    }
)

_PLUGIN_AGENT_BODIES: tuple[str, ...] = (
    "plugins/devops/agents/devops-engineer.md",
    "plugins/frontend-design/agents/design-specialist.md",
    "plugins/frontend-design/agents/frontend-engineer.md",
)

_DOC_SURFACES: tuple[str, ...] = (
    "data/handoff-AGENTS.md",
    "lifecycle_fragments/shared/output-handoff.md",
)

_EMITTER_SKILL = "skills/dadaia-handoff-emitter/SKILL.md"

#: The 14 whole-file surfaces (the emitter skill's two examples add the other 2 = 16).
_FILE_SURFACES: tuple[str, ...] = (
    *_CORE_AGENT_BODIES,
    *_PLUGIN_AGENT_BODIES,
    *_DOC_SURFACES,
)


def _read(rel: str) -> str:
    path = _PUBLIC / rel
    assert path.is_file(), f"enumerated surface missing on disk: {rel}"
    return path.read_text(encoding="utf-8")


def _skill_json_examples() -> list[str]:
    text = _read(_EMITTER_SKILL)
    return re.findall(r"```json\n(.*?)```", text, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Roster completeness — a missing/renamed/unenumerated file fails loudly.
# ---------------------------------------------------------------------------


def test_roster_completeness_core_agents() -> None:
    on_disk = {f"agents/{p.name}" for p in (_PUBLIC / "agents").glob("*.md")}
    assert on_disk == set(_CORE_AGENT_BODIES) | _PLUGIN_STUBS, (
        "public/agents/*.md roster drifted — update the 16-surface enumeration: "
        f"{sorted(on_disk.symmetric_difference(set(_CORE_AGENT_BODIES) | _PLUGIN_STUBS))}"
    )


def test_roster_completeness_plugin_agents() -> None:
    on_disk = {
        p.relative_to(_PUBLIC).as_posix() for p in (_PUBLIC / "plugins").glob("*/agents/*.md")
    }
    assert on_disk == set(_PLUGIN_AGENT_BODIES), (
        "public/plugins/*/agents/*.md roster drifted — update the 16-surface "
        f"enumeration: {sorted(on_disk.symmetric_difference(set(_PLUGIN_AGENT_BODIES)))}"
    )


def test_roster_is_sixteen_surfaces() -> None:
    examples = _skill_json_examples()
    assert len(examples) == 2, (
        f"the emitter skill must carry exactly TWO JSON examples, found {len(examples)}"
    )
    assert len(_FILE_SURFACES) + len(examples) == 16


# ---------------------------------------------------------------------------
# The 16/16 adoption contract.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("surface", _FILE_SURFACES)
def test_surface_carries_v12_and_self_pull_instruction(surface: str) -> None:
    text = _read(surface)
    missing = [t for t in (_TOKEN_V12, _TOKEN_SELF_PULL) if t not in text]
    assert not missing, (
        f"surface {surface} lacks the emission-instruction token(s) {missing} — "
        "every FR4 surface must instruct handoff-v1.2 emission with self_pull.refs "
        "(the atoms actually self-pulled/read; never an unread atom)"
    )


@pytest.mark.parametrize("index", [0, 1], ids=["example-handoff-only", "example-with-report"])
def test_emitter_skill_example_carries_v12_and_self_pull(index: int) -> None:
    examples = _skill_json_examples()
    assert len(examples) == 2, "emitter skill must carry exactly two JSON examples"
    example = examples[index]
    missing = [t for t in (_TOKEN_V12, _TOKEN_SELF_PULL) if t not in example]
    assert not missing, (
        f"dadaia-handoff-emitter SKILL.md example #{index + 1} lacks token(s) "
        f"{missing} — both examples must model schema_version handoff-v1.2 with a "
        "self_pull.refs block"
    )
