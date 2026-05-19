#!/usr/bin/env python3
"""Detect skill dirs unreferenced by any agent frontmatter. Exit 0=ok, 1=orphan."""
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
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


def main() -> int:
    all_skills = {d.name for d in _SKILLS_DIR.iterdir() if d.is_dir()}
    orphans = sorted(all_skills - _referenced_skills())
    if orphans:
        for name in orphans:
            print(name, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
