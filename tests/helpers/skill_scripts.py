"""Stage the skills the way `public stage` does: every skill's `scripts/` folder under one
`skills/` tree (the parent of *staged*'s skill folder)."""

from __future__ import annotations

import shutil
from pathlib import Path

_SKILLS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "skills"


def stage_skill_scripts(skill: str, staged: Path) -> Path:
    """Stage every skill beside *staged*, and *skill*'s scripts at *staged* itself; returns *staged*."""
    skip = shutil.ignore_patterns("__pycache__")
    for scripts in _SKILLS.glob("*/scripts"):
        target = staged.parents[1] / scripts.parent.name / "scripts"
        shutil.copytree(scripts, target, dirs_exist_ok=True, ignore=skip)
    shutil.copytree(_SKILLS / skill / "scripts", staged, dirs_exist_ok=True, ignore=skip)
    return staged
