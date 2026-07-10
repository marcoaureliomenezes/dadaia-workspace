"""T-12 — Skill-reference integrity test (AC C1).

Asserts that every skill name listed in the ``skills:`` frontmatter of each
agent Markdown file has a corresponding
``dadaia_workspace/public/skills/<name>/SKILL.md`` on disk.

If any reference is broken the test fails with a clear message that names the
offending agent and the missing skill path, so the author knows exactly what to
fix without reading a traceback.
"""

from __future__ import annotations

import pathlib
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Repository root — two levels up from this file's package root
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).parents[4]
_AGENTS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "agents"
_SKILLS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "skills"


# ---------------------------------------------------------------------------
# Helper: frontmatter parser
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: pathlib.Path) -> dict[str, Any]:
    """Return the YAML frontmatter dict from a ``---`` fenced Markdown file.

    Returns an empty dict if the file has no frontmatter or the fences are
    malformed — callers must handle missing keys gracefully.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    return yaml.safe_load(text[4:end]) or {}


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_agent_skill_references_exist() -> None:
    """Every skill listed in an agent's frontmatter must have a SKILL.md on disk.

    Parses all ``.md`` files under ``dadaia_workspace/public/agents/``, extracts
    the ``skills:`` list from each file's YAML frontmatter, and asserts that
    ``dadaia_workspace/public/skills/<name>/SKILL.md`` exists for each entry.

    Failure message lists every (agent, missing_skill_path) pair so the fix is
    unambiguous.
    """
    agent_files = sorted(_AGENTS_DIR.glob("*.md"))
    assert agent_files, f"No agent .md files found in {_AGENTS_DIR}"

    broken: list[str] = []

    for agent_path in agent_files:
        fm = _parse_frontmatter(agent_path)
        skills: list[str] = fm.get("skills") or []

        for skill_name in skills:
            skill_md = _SKILLS_DIR / skill_name / "SKILL.md"
            if not skill_md.exists():
                broken.append(
                    f"  agent={agent_path.name!r}  skill={skill_name!r}  expected={skill_md}"
                )

    assert not broken, (
        "The following agent skill references point to missing SKILL.md files:\n"
        + "\n".join(broken)
    )


# ---------------------------------------------------------------------------
# Relocated from tests/integration/test_public_assets.py (T-7, v0.1.75): a static
# frontmatter-shape lint over the runtime-adapter SKILL.md files that currently
# require it — no fs mutation, no install/stage, pure file-read + string check.
# ---------------------------------------------------------------------------


def test_problematic_skill_files_have_frontmatter() -> None:
    """Skill files that require YAML frontmatter must start with --- and define name+description.

    The set of checked skills is scoped to files that actually exist in the current
    public/ surface (agent-surface-reduction removed frontend/design skills).
    """
    public_dir = _REPO_ROOT / "dadaia_workspace" / "public"
    # Only skills that survived the agent-surface-reduction (v0.2.0) are checked.
    # frontend/design skills (ux-ui-review, design-report-quality-gate, etc.) were
    # removed from the core install; codex runtime adapters (design-ctx, frontend-ctx)
    # remain and are checked here.
    candidate_paths = [
        public_dir / "runtime" / "codex" / "design-ctx" / "SKILL.md",
        public_dir / "runtime" / "codex" / "frontend-ctx" / "SKILL.md",
    ]
    skill_paths = [p for p in candidate_paths if p.exists()]

    for skill_path in skill_paths:
        text = skill_path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{skill_path} must start with YAML frontmatter"
        assert "\n---\n" in text[4:], f"{skill_path} must close YAML frontmatter"
        frontmatter = text.split("\n---\n", 1)[0]
        assert "\nname: " in frontmatter
        assert "\ndescription: " in frontmatter
