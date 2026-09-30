"""The source-root guard: ``public install`` never projects into the library checkout."""

from __future__ import annotations

import tomllib
from pathlib import Path


def _is_source_repo_root(path: Path) -> bool:
    """True only for the library checkout, never a version-matching consumer workspace."""
    if not (path / "dadaia_workspace" / "public").is_dir():
        return False
    try:
        data = tomllib.loads((path / "pyproject.toml").read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return False
    names = (
        data.get("project", {}).get("name"),
        data.get("tool", {}).get("poetry", {}).get("name"),
    )
    return "dadaia-workspace" in names
