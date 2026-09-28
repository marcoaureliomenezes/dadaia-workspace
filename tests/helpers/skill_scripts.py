"""Stage one skill's scripts folder the way `public stage` does: its modules, the schema
copies (`_SKILL_SCRIPT_SCHEMAS`) and the shared ledger modules (`_SKILL_SCRIPT_SHARED`)."""

from __future__ import annotations

import shutil
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import (
    _SKILL_SCRIPT_SCHEMAS,  # allow-private-import: the one staging table
    _SKILL_SCRIPT_SHARED,  # allow-private-import: the one staging table
)

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"


def stage_skill_scripts(skill: str, staged: Path) -> Path:
    """Copy *skill*'s staged scripts folder into *staged*; returns *staged*."""
    shutil.copytree(_PKG / "public" / "skills" / skill / "scripts", staged, dirs_exist_ok=True)
    copies = [(f"public/{s}", f"{d}/{Path(s).name}") for s, d in _SKILL_SCRIPT_SCHEMAS]
    for src, dst in [*copies, *_SKILL_SCRIPT_SHARED]:
        if dst.startswith(f"skills/{skill}/scripts/"):
            target = staged / dst.removeprefix(f"skills/{skill}/scripts/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_PKG / src, target)
    return staged
