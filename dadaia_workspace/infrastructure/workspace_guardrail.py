"""The source-root guard: ``public install`` never projects into the library checkout."""

from __future__ import annotations

import tomllib
from pathlib import Path


def _is_source_repo_root(path: Path) -> bool:
    """Return True only for the dadaia-workspace source tree root.

    This intentionally ignores staged manifest versions: a normal temporary
    consumer workspace becomes version-matching after ``stage()`` and must still
    be installable. The source-root guard is only for the library checkout that
    contains the package source itself.
    """
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.exists():
        return False
    if not (path / "dadaia_workspace" / "public").is_dir():
        return False
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return False
    tool = data.get("tool")
    poetry_name = ""
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            name = poetry.get("name")
            if isinstance(name, str):
                poetry_name = name

    project_name = ""
    project = data.get("project")
    if isinstance(project, dict):
        name = project.get("name")
        if isinstance(name, str):
            project_name = name
    return poetry_name == "dadaia-workspace" or project_name == "dadaia-workspace"
