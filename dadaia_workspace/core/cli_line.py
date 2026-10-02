"""The ONE spelling of the workspace CLI and its venv tools (ADR 0045): absolute paths,
so every ``fix:`` runs from any cwd — ``shlex`` on POSIX; on Windows forward slashes, a
part holding a blank quoted whole — the executable's quote opened after its drive letter
(``C":/a b/x.exe"``), since a line opening with a quote is a PowerShell expression."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path, PurePath

from dadaia_workspace.core import platform


def cli_path[P: PurePath](root: P) -> P:
    """The workspace CLI's real executable (``Scripts\\dadaia.exe`` on Windows)."""
    return _venv_tool(root / ".dadaia" / ".venv", "dadaia")


def fix_line(root: PurePath | None, *argv: str) -> str:
    """``<absolute CLI> argv…`` quoted for the host shell (:func:`venv_line` for the CLI)."""
    return venv_line(root, "dadaia", *argv)


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
    venv = root / ".dadaia" / ".venv" if root is not None else Path(sys.prefix)
    return shell_line(str(_venv_tool(venv, tool)), *argv)


def _venv_tool[P: PurePath](venv: P, tool: str) -> P:
    caps = platform.PLATFORM
    return venv / caps.venv_scripts_dir / f"{tool}{caps.venv_exe_suffix}"


def git_line(repo: str | PurePath, *argv: str) -> str:
    """``git -C <repo> argv…`` — every git fix names its repo, so it runs from any cwd."""
    return shell_line("git", "-C", str(repo), *argv)


def shell_line(*parts: str) -> str:
    """*parts* joined into one command line quoted for the host shell."""
    if platform.PLATFORM.venv_exe_suffix:  # Windows
        head, *argv = (_win_quote(part.replace("\\", "/")) for part in parts)
        if head.startswith('"'):  # a drive path: open the quote after its first char
            head = f'{head[1]}"{head[2:]}'
        return " ".join((head, *argv))
    return shlex.join(parts)


def mkdir_line(directory: PurePath) -> str:
    """Create *directory* and its parents, idempotent — one interpreter line that runs
    unchanged under sh, bash, cmd and PowerShell (no shell builtin differs per OS)."""
    code = f"import pathlib; pathlib.Path(r'{directory}').mkdir(parents=True, exist_ok=True)"
    return shell_line(sys.executable, "-c", code)


def materialize_line(link: PurePath, target: PurePath) -> str:
    """Replace the symlink *link* by a regular copy of *target* (``os.remove`` drops the
    link, never its target) — the same interpreter line on every OS."""
    code = f"import os, shutil; os.remove(r'{link}'); shutil.copyfile(r'{target}', r'{link}')"
    return shell_line(sys.executable, "-c", code)


def _win_quote(arg: str) -> str:
    return arg if arg and not any(c in arg for c in ' \t"') else f'"{arg}"'
