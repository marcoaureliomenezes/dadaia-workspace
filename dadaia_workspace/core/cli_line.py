"""The ONE spelling of the workspace CLI and its venv tools: absolute paths, so every
``fix:`` runs from any cwd. The quoting rule belongs to the kernel's `_platform.py`."""

from __future__ import annotations

import sys
from pathlib import Path, PurePath

from dadaia_workspace.core import platform
from dadaia_workspace.core.skill_owner import load_owner


def fix_of(text: str, default: str = "") -> str:
    """The first `fix:` line of a child script's *text*: the kernel's one parser."""
    return str(load_owner("dd-bug-resolution", "_refusal").fix_of(text, default))


def without_fix(text: str) -> str:
    """*text* with its `fix:` lines removed: the kernel's one stripper."""
    return str(load_owner("dd-bug-resolution", "_refusal").without_fix(text))


def spell_fix(fix: str) -> str:
    """The `fix:` line of *fix*: the kernel's one spelling."""
    return str(load_owner("dd-bug-resolution", "_refusal").spell_fix(fix))


reinstall_fix = platform.reinstall_fix


def cli_words(root: PurePath | None, *argv: str) -> tuple[str, ...]:
    """The words that run the workspace CLI of *root*: the kernel's."""
    return platform.cli_words(root, *argv)


def fix_line(root: PurePath | None, *argv: str) -> str:
    """``<absolute CLI> argv…`` quoted for the host shell (:func:`venv_line` for the CLI)."""
    return platform.command(*cli_words(root, *argv))


#: The skills this package ships — present wherever the running CLI is installed.
_SHIPPED_SKILLS = Path(__file__).resolve().parents[1] / "public" / "skills"


def script_line(script: str, *argv: str) -> str:
    """A skill script (its ``.agents/skills/…`` path) run from the copy the running CLI
    ships, by the running interpreter — both absolute, true in any venv (pipx, poetry)."""
    shipped = _SHIPPED_SKILLS / PurePath(script).relative_to(".agents/skills")
    return venv_line(None, "python", str(shipped), *argv)


def venv_line(root: PurePath | None, tool: str, *argv: str) -> str:
    """``<absolute venv tool> argv…`` for *tool* (``dadaia``, ``pip``, ``python``) of the
    workspace venv; no workspace (*root* ``None``: CI) names the venv running now."""
    venv = platform.venv_dir(root) if root is not None else Path(sys.prefix)
    return platform.command(str(platform.venv_tool(venv, tool)), *argv)


def git_line(repo: str | PurePath, *argv: str) -> str:
    """``git -C <repo> argv…`` — every git fix names its repo, so it runs from any cwd."""
    return platform.command("git", "-C", str(repo), *argv)


def shell_line(*parts: str) -> str:
    """*parts* as one finished command line for the host shell: the kernel's ``command``."""
    return platform.command(*parts)


def mkdir_line(directory: PurePath) -> str:
    """Create *directory* and its parents: the kernel's cross-shell act."""
    return platform.mkdir_line(directory)


def materialize_line(link: PurePath, target: PurePath) -> str:
    """Replace the symlink *link* by a regular copy of *target* (``os.remove`` drops the
    link, never its target) — the same interpreter line on every OS."""
    code = (
        "import os, shutil, sys; os.remove(sys.argv[1]); shutil.copyfile(sys.argv[2], sys.argv[1])"
    )
    return platform.command(sys.executable, "-c", code, str(link), str(target))
