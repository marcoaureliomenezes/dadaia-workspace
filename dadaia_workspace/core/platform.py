"""The package's door to the OS boundary: the kernel's ``_platform`` decides every host fact; this
module hands it the current ``PLATFORM`` and re-exports the functions that read none. Tests swap
it: ``monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))``.
"""

from __future__ import annotations

from pathlib import Path, PurePath
from typing import TYPE_CHECKING, NamedTuple

from dadaia_workspace.core.skill_owner import load_owner

if TYPE_CHECKING:
    import _platform as _owner
else:
    _owner = load_owner("dd-bug-resolution", "_platform")


class Capabilities(NamedTuple):
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


def _caps(caps: Capabilities | None = None) -> _owner.Caps:
    caps = caps or PLATFORM
    return _owner.Caps(caps.venv_scripts_dir, caps.venv_exe_suffix, caps.windows)


def venv_dir[P: PurePath](root: P) -> P:
    """The workspace venv under *root*, by the kernel's rule."""
    return _owner.venv_dir(root)


def venv_tool[P: PurePath](venv: P, tool: str) -> P:
    """Where *venv* keeps the executable *tool*, by the kernel's rule fed the current ``PLATFORM``."""
    return _owner.venv_tool(venv, tool, _caps())


def cli_argv(venv: PurePath) -> list[str]:
    """The words that run *venv*'s CLI in a shell line, by the kernel's rule fed the current ``PLATFORM``."""
    return _owner.cli_argv(venv, _caps())


def workspace_cli_path[P: PurePath](root: P) -> P:
    """Where the workspace CLI lives under *root*, by the kernel's rule fed the current ``PLATFORM``."""
    return _owner.cli_path(root, _caps())


def quote(word: str) -> str:
    """One argument inside a sentence for the host shell, by the kernel's rule fed the current ``PLATFORM``."""
    return _owner.quote(word, _caps())


def head(word: str) -> str:
    """A command's first word for the host shell, by the kernel's rule fed the current ``PLATFORM``."""
    return _owner.head(word, _caps())


def command(*argv: str) -> str:
    """The finished command line of *argv* for the host shell, by the kernel's rule fed the current ``PLATFORM``."""
    return _owner.command(*argv, caps=_caps())


def inline(*argv: str) -> str:
    """*argv* as text inside a sentence for the host shell, by the kernel's rule fed the current ``PLATFORM``."""
    return _owner.inline(*argv, caps=_caps())


def git_inline(repo: Path | str, *argv: str) -> str:
    """``git -C <repo> argv…`` as text inside a sentence, by the kernel's rule fed the current ``PLATFORM``."""
    return _owner.git_inline(repo, *argv, caps=_caps())


def python_in[P: PurePath](venv: P, caps: Capabilities | None = None) -> P:
    """Where *venv* keeps its interpreter on *caps* (default: the current ``PLATFORM``)."""
    return _owner.python_in(venv, _caps(caps))


def is_fully_qualified(candidate: str) -> bool:
    """Whether *candidate* is rooted on the current ``PLATFORM``."""
    return _owner.is_fully_qualified(candidate, _caps())


def cli_words(root: PurePath | None, *argv: str) -> tuple[str, ...]:
    """The words that run the workspace CLI of *root* with *argv*, on the current ``PLATFORM``."""
    return _owner.cli_words(root, *argv, caps=_caps())


def reinstall_fix(start: Path, *, projected: bool = False) -> str:
    """The command that repairs a missing file under *start*, on the current ``PLATFORM``."""
    return str(
        load_owner("dd-bug-resolution", "_jsonl").reinstall_fix(start, _caps(), projected=projected)
    )


def mkdir_line(directory: PurePath) -> str:
    """The cross-shell mkdir line for *directory*, on the current ``PLATFORM``."""
    return _owner.mkdir_line(directory, _caps())


def canonical_cli(text: str) -> str:
    """*text* with the current ``PLATFORM``'s venv CLI spelling replaced by the source form."""
    return _owner.canonical_cli(text, _caps())


def home_env(home: Path) -> dict[str, str]:
    """The variables a child reads its home from on the current ``PLATFORM``."""
    return _owner.home_env(home, _caps())


def is_executable(path: Path) -> bool:
    """Whether *path* is runnable on the current ``PLATFORM``."""
    return _owner.is_executable(path, _caps())


def make_executable(path: Path) -> None:
    """Add the exec bits to *path* on the current ``PLATFORM``."""
    _owner.make_executable(path, _caps())


# The kernel's functions that read no capability: the door hands them out unchanged.
Undecodable = _owner.Undecodable
act = _owner.act
act_kind = _owner.act_kind
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
