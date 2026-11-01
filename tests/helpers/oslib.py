"""The one door through which tests reach the OS: the skill kernel's `_platform`, re-exported.

Tests read, write, spawn, spell and probe with these names; none calls `Path.read_text`,
`subprocess.run` or a host check itself, so a Windows rule is the kernel's and nowhere else.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from dadaia_workspace.core.skill_owner import load_owner

_K = load_owner("dd-bug-resolution", "_platform")

Caps = _K.Caps
Undecodable = _K.Undecodable
canonical_cli = _K.canonical_cli
cli_argv = _K.cli_argv
cli_path = _K.cli_path
command = _K.command
decode = _K.decode
detect = _K.detect
effective_uid = _K.effective_uid
git_line = _K.git_line
head = _K.head
home_env = _K.home_env
inline = _K.inline
is_executable = _K.is_executable
is_fully_qualified = _K.is_fully_qualified
is_link = _K.is_link
link = _K.link
make_executable = _K.make_executable
make_writable = _K.make_writable
norm_sep = _K.norm_sep
pid_alive = _K.pid_alive
popen = _K.popen
popen_bytes = _K.popen_bytes
python_in = _K.python_in
quote = _K.quote
read_text = _K.read_text
replace = _K.replace
run = _K.run
run_bytes = _K.run_bytes
spell = _K.spell
venv_dir = _K.venv_dir
venv_tool = _K.venv_tool
write_text = _K.write_text

#: The line ending a console prints on this host.
EOL = os.linesep


#: Whether file permissions bind this process: a host with owners, and not root.
PERMISSIONS_ENFORCED = _K.effective_uid() not in (None, 0)


def make_readonly(path: Path, *, locked: bool = False) -> None:
    """Take write permission from *path*, every permission with *locked*; `make_writable` gives
    the owner's back."""
    os.chmod(path, 0 if locked else stat.S_IMODE(path.stat().st_mode) & ~0o222)


def shells_for(caps: Caps) -> list[str]:
    """The shells a line spelled for *caps* is judged in: ``sh`` and ``bash`` for POSIX; ``cmd``,
    ``powershell``, ``pwsh`` and Git Bash for Windows. A PowerShell is never given a POSIX line."""
    return ["cmd", "powershell", "pwsh", "bash"] if caps.windows else ["sh", "bash"]


def run_line(line: str, **kw: object) -> subprocess.CompletedProcess[str]:
    """Run a finished command line in the host shell: ``sh -c``, PowerShell on Windows."""
    shell = ["powershell", "-NoProfile", "-Command"] if detect().windows else ["sh", "-c"]
    return run([*shell, line], **kw)  # type: ignore[arg-type]


def run_cmdline(command_line: str, **kw: object) -> subprocess.CompletedProcess[str]:
    """Run *command_line* as the child's own Windows command line, not re-quoted from an argv
    (``cmd /s`` reads its raw tail); output decoded by the kernel's `decode`."""
    done = subprocess.run(command_line, capture_output=True, **kw)  # type: ignore[call-overload]  # noqa: S603 — one finished command line, no shell
    return subprocess.CompletedProcess(
        done.args, done.returncode, decode(done.stdout), decode(done.stderr)
    )


def make_venv(path: Path) -> Path:
    """A real ``python -m venv --copies`` at *path* (on Windows its ``python.exe`` is CPython's
    redirector, as in production); returns its interpreter."""
    run([sys._base_executable, "-m", "venv", "--copies", "--without-pip", str(path)], check=True)
    return python_in(path)


def stub_cli(directory: Path, name: str, source: str, python: Path | None = None) -> Path:
    """A runnable fake CLI *name* in *directory*: *source*, a python script whose first line is
    ``#!python``, bound to *python* (default the base interpreter) as pip binds a console script.
    pip's launcher ``.exe`` on Windows, an executable shebang script elsewhere, started by its
    path without a shell. Returns that path."""
    from pip._vendor.distlib.scripts import (
        ScriptMaker,
        enquote_executable,
    )  # pip is not a declared dependency: only a stub needs it

    with tempfile.TemporaryDirectory() as src:
        script = Path(src) / name
        write_text(script, source)
        maker = ScriptMaker(src, str(directory), add_launchers=True)
        maker.clobber = True  # a re-placed stub replaces the older one
        maker.executable = enquote_executable(str(python or Path(sys._base_executable).resolve()))
        maker.make(str(script))
    return directory / f"{name}{detect().exe_suffix}"
