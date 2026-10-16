"""Platform capability seam: every platform decision flows through the ``PLATFORM`` singleton,
whose facts are the kernel's ``_platform`` (the one host reader); tests swap it:
``monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

from dadaia_workspace.core.skill_owner import load_owner

_owner = load_owner("dd-bug-resolution", "_platform")


@dataclass(frozen=True)
class Capabilities:
    """``venv_scripts_dir`` (``bin``/``Scripts``), ``venv_exe_suffix`` (``""``/``.exe``)
    and ``windows`` (the host path flavor is ``ntpath``)."""

    venv_scripts_dir: str
    venv_exe_suffix: str
    windows: bool

    @classmethod
    def detect(cls, platform: str | None = None) -> Capabilities:
        """Capabilities for *platform* (default: this host)."""
        caps = _owner.detect(platform)
        return cls(caps.scripts_dir, caps.exe_suffix, caps.windows)


PLATFORM: Capabilities = Capabilities.detect()


def _caps() -> Any:
    return _owner.Caps(PLATFORM.venv_scripts_dir, PLATFORM.venv_exe_suffix, PLATFORM.windows)


def venv_dir[P: PurePath](root: P) -> P:
    """The workspace venv under *root*, by the kernel's rule."""
    path: P = _owner.venv_dir(root)
    return path


def venv_tool[P: PurePath](venv: P, tool: str) -> P:
    """Where *venv* keeps the executable *tool*, by the kernel's rule fed the current ``PLATFORM``."""
    path: P = _owner.venv_tool(venv, tool, _caps())
    return path


def cli_argv(venv: PurePath) -> list[str]:
    """The words that run *venv*'s CLI in a shell line, by the kernel's rule fed the current ``PLATFORM``."""
    return list(_owner.cli_argv(venv, _caps()))


def workspace_cli_path[P: PurePath](root: P) -> P:
    """Where the workspace CLI lives under *root*, by the kernel's rule fed the current ``PLATFORM``."""
    path: P = _owner.cli_path(root, _caps())
    return path


def quote(word: str) -> str:
    """One argument inside a sentence for the host shell, by the kernel's rule fed the current ``PLATFORM``."""
    return str(_owner.quote(word, _caps()))


def head(word: str) -> str:
    """A command's first word for the host shell, by the kernel's rule fed the current ``PLATFORM``."""
    return str(_owner.head(word, _caps()))


def command(*argv: str) -> str:
    """The finished command line of *argv* for the host shell, by the kernel's rule fed the current ``PLATFORM``."""
    return str(_owner.command(*argv, caps=_caps()))


def inline(*argv: str) -> str:
    """*argv* as text inside a sentence for the host shell, by the kernel's rule fed the current ``PLATFORM``."""
    return str(_owner.inline(*argv, caps=_caps()))


def git_inline(repo: PurePath | str, *argv: str) -> str:
    """``git -C <repo> argv…`` as text inside a sentence, by the kernel's rule fed the current ``PLATFORM``."""
    return str(_owner.git_inline(repo, *argv, caps=_caps()))


def python_in[P: PurePath](venv: P) -> P:
    """Where *venv* keeps its interpreter on the current ``PLATFORM``."""
    path: P = _owner.python_in(venv, _caps())
    return path


def is_fully_qualified(candidate: str) -> bool:
    """Whether *candidate* is rooted on the current ``PLATFORM``."""
    return bool(_owner.is_fully_qualified(candidate, _caps()))


def canonical_cli(text: str) -> str:
    """*text* with the current ``PLATFORM``'s venv CLI spelling replaced by the source form."""
    return str(_owner.canonical_cli(text, _caps()))


def home_env(home: PurePath) -> dict[str, str]:
    """The variables a child reads its home from on the current ``PLATFORM``."""
    return dict(_owner.home_env(home, _caps()))


def is_executable(path: PurePath) -> bool:
    """Whether *path* is runnable on the current ``PLATFORM``."""
    return bool(_owner.is_executable(path, _caps()))


def make_executable(path: PurePath) -> None:
    """Add the exec bits to *path* on the current ``PLATFORM``."""
    _owner.make_executable(path, _caps())


# The kernel's functions that read no capability: the door hands them out unchanged.
Undecodable = _owner.Undecodable
can_write = _owner.can_write
decode = _owner.decode
effective_uid = _owner.effective_uid
file_owner = _owner.file_owner
is_link = _owner.is_link
link = _owner.link
make_writable = _owner.make_writable
norm_sep = _owner.norm_sep
popen = _owner.popen
popen_bytes = _owner.popen_bytes
read_text = _owner.read_text
replace = _owner.replace
run = _owner.run
run_bytes = _owner.run_bytes
use_utf8_stdio = _owner.use_utf8_stdio
write_text = _owner.write_text
