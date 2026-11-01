"""The source-root guard: ``public install`` never projects into the library checkout."""

from __future__ import annotations

import tomllib
from pathlib import Path

from dadaia_workspace.core import platform


def _is_source_repo_root(path: Path) -> bool:
    """True only for the library checkout, never a version-matching consumer workspace."""
    if not (path / "dadaia_workspace" / "public").is_dir():
        return False
    try:
        data = tomllib.loads(platform.read_text(path / "pyproject.toml"))
    except (tomllib.TOMLDecodeError, OSError, platform.Undecodable):
        return False
    names = (
        data.get("project", {}).get("name"),
        data.get("tool", {}).get("poetry", {}).get("name"),
    )
    return "dadaia-workspace" in names
