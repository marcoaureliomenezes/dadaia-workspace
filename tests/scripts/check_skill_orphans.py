#!/usr/bin/env python3
"""Detect skill dirs unreferenced by any agent frontmatter. Exit 0=ok, 1=orphan."""

import os
import re
import sys
from pathlib import Path

_ROOT = Path(os.environ.get("DADAIA_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent.parent))
_SKILLS_DIR = _ROOT / "dadaia_workspace" / "public" / "skills"
_AGENTS_DIR = _ROOT / "dadaia_workspace" / "public" / "agents"


def _referenced_skills() -> set[str]:
    referenced: set[str] = set()
    for agent_file in _AGENTS_DIR.glob("*.md"):
        content = agent_file.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) < 2:
            continue
        fm = parts[1]
        in_skills = False
        for line in fm.splitlines():
            if re.match(r"^skills\s*:", line):
                in_skills = True
            elif in_skills:
                m = re.match(r"^\s+-\s+(\S+)", line)
                if m:
                    referenced.add(m.group(1))
                elif line.strip() and not line[0].isspace():
                    in_skills = False
    return referenced


def _disable_model_invocation_skills() -> set[str]:
    """Skills FR28 (A28.1) deliberately excludes from every persona's ``skills:`` list.

    A skill whose own ``SKILL.md`` frontmatter carries ``disable-model-invocation:
    true`` is, by design, never granted to a model through any agent's ``skills:``
    allowlist — it is driven directly (operator/dispatching-agent protocol), not
    invoked by the model. Flagging such a skill an "orphan" for that absence would
    demand a change that violates FR28 itself.
    """
    disabled: set[str] = set()
    for skill_dir in _SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        content = skill_file.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) < 2:
            continue
        fm = parts[1]
        if re.search(r"^disable-model-invocation\s*:\s*true\s*$", fm, re.MULTILINE):
            disabled.add(skill_dir.name)
    return disabled


def main() -> int:
    all_skills = {d.name for d in _SKILLS_DIR.iterdir() if d.is_dir()}
    orphans = sorted(all_skills - _referenced_skills() - _disable_model_invocation_skills())
    if orphans:
        for name in orphans:
            print(name, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
