#!/usr/bin/env python3
"""The one OS boundary: every host fact the skill scripts and the package need, as a function over
`Caps`. Stdlib only. Text is UTF-8 with LF, a child's text is decoded UTF-8, a runnable line is
spelled here and nowhere else; no other module reads `sys.platform` or spells a shell word."""

from __future__ import annotations

import contextlib
import ntpath
import os
import posixpath
import re
import shlex
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePath, PurePosixPath
from typing import IO, Any, Literal, NamedTuple

from _refusal import Refusal


class Caps(NamedTuple):
    scripts_dir: str
    exe_suffix: str
    windows: bool


def detect(platform: str | None = None) -> Caps:
    """Capabilities of *platform* (default ``sys.platform``)."""
    windows = (platform if platform is not None else sys.platform) == "win32"
    return Caps("Scripts" if windows else "bin", ".exe" if windows else "", windows)


_LOCAL = re.compile(r"^(?P<bind>.+):(?P<port>\d+)$")
_PID = re.compile(r'\("(?P<exe>[^"]+)",pid=(?P<pid>\d+)')


# --- venv layout and paths -------------------------------------------------------------


def venv_dir[P: PurePath](root: P) -> P:
    """The workspace venv under *root*."""
    return root / ".dadaia" / ".venv"


def venv_tool[P: PurePath](venv: P, tool: str, caps: Caps | None = None) -> P:
    """Where *venv* keeps the executable *tool* on this host."""
    caps = caps or detect()
    return venv / caps.scripts_dir / f"{tool}{caps.exe_suffix}"


def python_in[P: PurePath](venv: P, caps: Caps | None = None) -> P:
    """Where *venv* keeps its interpreter."""
    return venv_tool(venv, "python", caps)


def cli_path[P: PurePath](root: P, caps: Caps | None = None) -> P:
    """Where the workspace CLI lives under *root*; whether it exists is not asked."""
    return venv_tool(venv_dir(root), "dadaia", caps)


def cli_argv(venv: PurePath, caps: Caps | None = None) -> list[str]:
    """The words that run the CLI of *venv* in a shell line: its console script."""
    return [str(venv_tool(venv, "dadaia", caps))]


def cli_words(root: PurePath | None, *argv: str, caps: Caps | None = None) -> tuple[str, ...]:
    """The words that run the workspace CLI of *root* (the venv running now when ``None``) with
    *argv*: rendered once, by :func:`command` for a fix or :func:`inline` inside a sentence."""
    venv = venv_dir(root) if root is not None else Path(sys.prefix)
    return (*cli_argv(venv, caps), *argv)


def norm_sep(path: str) -> str:
    """*path* spelled with forward slashes, whatever host wrote it."""
    return path.replace("\\", "/")


def is_fully_qualified(candidate: str, caps: Caps | None = None) -> bool:
    """Whether *candidate* names one location whatever the cwd or current drive is: on Windows a
    drive or UNC root (a drive-relative ``\\tools`` is not), elsewhere a leading slash."""
    if (caps or detect()).windows:
        return ntpath.isabs(candidate) and ntpath.splitdrive(candidate)[0] != ""
    return posixpath.isabs(candidate)


def canonical_cli(text: str, caps: Caps | None = None) -> str:
    """*text* with this host's spelling of the venv CLI replaced by the source form, so a digest of
    it is one value on every host."""
    host = venv_tool(PurePosixPath(".venv"), "dadaia", caps).as_posix()
    return text.replace(host, ".venv/bin/dadaia")


def home_env(home: Path, caps: Caps | None = None) -> dict[str, str]:
    """The variables a child reads its home from: ``HOME``, and ``USERPROFILE`` on Windows."""
    names = ("HOME", "USERPROFILE") if (caps or detect()).windows else ("HOME",)
    return {name: str(home) for name in names}


# --- text ------------------------------------------------------------------------------


class Undecodable(Refusal):
    """The file *path* is not UTF-8 at *line*: a verb refuses with the act that re-encodes that
    line in place, a check reports a finding there."""

    def __init__(self, path: Path, fix: str = "", line: int = 1) -> None:
        super().__init__(
            f"{path} is not valid UTF-8",
            fix
            or act(
                "agent",
                f"re-encode line {line} of {path.resolve()} as UTF-8 in place; every other line stays",
            ),
        )
        self.path, self.line = path, line


def read_text(path: Path, fix: str = "") -> str:
    """The text of *path*, newlines as ``\\n``; bytes that are not UTF-8 raise :class:`Undecodable`
    naming it, with *fix* in place of the default act."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise Undecodable(path, fix, exc.object.count(b"\n", 0, exc.start) + 1) from exc


def write_text(path: Path, text: str, *, newline: str | None = "\n") -> None:
    """Write *text* to *path* as UTF-8; *newline* is ``Path.write_text``'s (LF on every host)."""
    path.write_text(text, encoding="utf-8", newline=newline)


def decode(raw: bytes) -> str:
    """*raw* as text: UTF-8, a BOM dropped, CRLF as LF, bad bytes replaced."""
    return raw.decode("utf-8-sig", errors="replace").replace("\r\n", "\n")


def use_utf8_stdio() -> None:
    """Make stdout and stderr UTF-8 whatever the host pipe defaults to (cp1252 on Windows)."""
    for stream in (sys.stdout, sys.stderr):
        if reconfigure := getattr(stream, "reconfigure", None):
            reconfigure(encoding="utf-8", errors=stream.errors)


# --- child processes -------------------------------------------------------------------


def run(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    input: str | None = None,
    stdin: int | None = None,
    timeout: float | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run *argv* (no shell) and capture its output as UTF-8 text, bad bytes replaced. A missing
    program raises ``OSError``; a non-zero exit raises only with *check*."""
    return subprocess.run(  # noqa: S603 — an argv list, no shell
        list(argv), cwd=cwd, env=env, input=input, stdin=stdin, timeout=timeout, check=check,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )  # fmt: skip


def passthrough(
    argv: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None
) -> int:
    """Run *argv* (no shell) with this process's own stdin, stdout and stderr; its exit code."""
    return subprocess.run(argv, cwd=cwd, env=env, check=False).returncode  # noqa: S603


def run_bytes(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    input: bytes | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run *argv* (no shell) and capture its output as raw bytes."""
    return subprocess.run(  # noqa: S603 — an argv list, no shell
        list(argv), cwd=cwd, env=env, input=input, timeout=timeout, capture_output=True
    )


def popen(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    stdout: int | IO[Any] | None = subprocess.PIPE,
    stderr: int | IO[Any] | None = subprocess.PIPE,
) -> subprocess.Popen[str]:
    """Start *argv* (no shell) with UTF-8 text pipes, bad bytes replaced."""
    return subprocess.Popen(  # noqa: S603 — an argv list, no shell
        list(argv), cwd=cwd, env=env, stdout=stdout, stderr=stderr,
        text=True, encoding="utf-8", errors="replace",
    )  # fmt: skip


def popen_bytes(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    stdout: int | IO[Any] | None = subprocess.PIPE,
    stderr: int | IO[Any] | None = subprocess.DEVNULL,
) -> subprocess.Popen[bytes]:
    """Start *argv* (no shell) with raw byte pipes."""
    return subprocess.Popen(list(argv), cwd=cwd, stdout=stdout, stderr=stderr)  # noqa: S603


# --- exec bit and filesystem -----------------------------------------------------------


def is_executable(path: Path, caps: Caps | None = None) -> bool:
    """Whether *path* is a file the host can run: the exec bit on POSIX, existence on Windows
    (the extension decides there)."""
    return path.is_file() and ((caps or detect()).windows or os.access(path, os.X_OK))


def make_executable(path: Path, caps: Caps | None = None) -> None:
    """Add the exec bits to *path*; Windows has none."""
    if not (caps or detect()).windows:
        os.chmod(path, stat.S_IMODE(path.stat().st_mode) | 0o111)


def make_writable(path: Path) -> None:
    """Give the owner read, write and search on *path* (clears the read-only attribute on Windows)."""
    os.chmod(path, path.stat().st_mode | stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)


def can_write(path: Path) -> bool:
    """Whether this process may write *path*."""
    return os.access(path, os.W_OK)


def replace(src: Path, dst: Path) -> None:
    """Move *src* onto *dst* atomically. A held-open destination (``PermissionError``, Windows) is
    retried 49 times 0.01 s apart before the final raising swap; POSIX never raises it there."""
    for _ in range(49):
        with contextlib.suppress(PermissionError):
            return os.replace(src, dst)
        time.sleep(0.01)
    os.replace(src, dst)


def is_link(path: Path) -> bool:
    """Whether *path* is a symlink (dangling included) or a Windows junction."""
    return path.is_symlink() or path.is_junction()


def link(target: str, dst: Path, *, is_dir: bool) -> bool:
    """Make *dst* a symlink to *target*; False when the host refuses (Windows without the
    privilege), so the caller copies. An existing *dst* raises ``FileExistsError``."""
    try:
        os.symlink(target.replace("/", os.sep), dst, target_is_directory=is_dir)
    except FileExistsError:
        raise
    except (OSError, NotImplementedError):
        return False
    return True


# --- process control -------------------------------------------------------------------


def _win_alive(pid: int) -> bool:
    """Whether Windows process *pid* is still running (exit code ``STILL_ACTIVE``)."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return bool(ctypes.get_last_error() == 5)  # type: ignore[attr-defined]  # access denied: it exists
    try:
        code = wintypes.DWORD()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value == 259)
    finally:
        kernel.CloseHandle(handle)


def pid_alive(pid: int, caps: Caps | None = None) -> bool:
    """Whether process *pid* exists."""
    if pid <= 0:
        return False
    if (caps or detect()).windows:
        return _win_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


class Listener(NamedTuple):
    port: int
    bind: str
    pid: int | None
    cmdline: str
    cwd: str


def parse_ss_line(line: str) -> tuple[int, str, int | None] | None:
    """``(port, bind, pid)`` of one ``ss -tlnp`` row; None for the header or a short row."""
    parts = line.split()
    if len(parts) < 4 or line.startswith("State") or not (m := _LOCAL.match(parts[3])):
        return None
    bind = m.group("bind").lstrip("[").rstrip("]")
    bind = "0.0.0.0" if bind == "*" else bind  # noqa: S104 — parsing, not binding
    pid = None
    if len(parts) >= 6 and (pm := _PID.search(" ".join(parts[5:]))):
        pid = int(pm.group("pid"))
    return int(m.group("port")), bind, pid


def _ss() -> str | None:
    try:
        done = run(["ss", "-tlnp"], timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def listeners(
    *, proc: Path = Path("/proc"), ss: Callable[[], str | None] = _ss
) -> list[Listener] | None:
    """The TCP listeners of this host with their owner's command line and cwd, by port; None where
    there is no process tree or no ``ss`` to ask (today only Linux has both)."""
    raw = ss() if proc.is_dir() else None
    if raw is None:
        return None
    found = []
    for line in raw.splitlines():
        if (parsed := parse_ss_line(line)) is None:
            continue
        port, bind, pid = parsed
        cmdline = cwd = ""
        if pid is not None:
            with contextlib.suppress(OSError):
                cmdline = decode((proc / str(pid) / "cmdline").read_bytes().replace(b"\0", b" "))
                cmdline = cmdline.strip()[:200]
                cwd = os.readlink(proc / str(pid) / "cwd")
        found.append(Listener(port, bind, pid, cmdline, cwd))
    return sorted(found, key=lambda f: f.port)


def file_owner(path: Path) -> tuple[int, str] | None:
    """``(uid, name)`` owning *path*; None where the host has no account database."""
    try:
        import pwd

        uid = path.stat().st_uid
    except (ImportError, OSError):
        return None
    try:
        return uid, pwd.getpwuid(uid).pw_name
    except KeyError:
        return uid, str(uid)


def effective_uid() -> int | None:
    """The uid this process runs as; None where there is none."""
    geteuid = getattr(os, "geteuid", None)
    return int(geteuid()) if geteuid else None


# --- shell spelling --------------------------------------------------------------------

#: Windows shells (and an interactive Git Bash, for "!") read these as syntax even inside double
#: quotes: a word holding one has no spelling.
_NO_SPELLING = frozenset('"$`%!\r\n\0')
#: PowerShell reads these in argument mode as numbers and hands a native command the value, not the
#: text: 0x10, 1e3, 1kb, 10d, 007, 0b1, 1n, 1ukb. A short plain integer is the same either way.
_NUMBER_LIKE = re.compile(
    r"[+-]?(0x[0-9a-f]+|0b[01]+|\d+\.?\d*(e[+-]?\d+)?|\.\d+(e[+-]?\d+)?)(u[lsy]?|[lsyn]|d)?([kmgtp]b)?",
    re.IGNORECASE,
)
_PLAIN_INT = re.compile(r"0|[1-9]\d{0,8}")


def spell(word: str, caps: Caps | None = None, *, head: bool = False) -> str | None:
    """The grammar's one decider: *word* as one shell word, or None when no quoting makes it safe.

    POSIX: ``shlex``. Windows (PowerShell, cmd and Git Bash read the result alike): backslashes
    become ``/``; letters and digits of any alphabet and ``._-/:+`` stay bare (``=`` too, except in
    a command head, where cmd splits on it); a number-like word, anything else and the empty word go
    in double quotes, except a head: none of its quoted forms runs alike in the three shells (a
    leading quote is an expression to PowerShell, ``C"…"`` garbles a pip launcher in cmd), so a head
    needing a quote has no spelling; a word holding ``" $ ` % !``, a line break, U+2018-U+201E or a Unicode space
    other than blank and tab has no spelling. :func:`quote`, :func:`head` and :func:`command` are
    its forms."""
    if not (caps or detect()).windows:
        return shlex.quote(word)
    word = norm_sep(word)
    if any(
        c in _NO_SPELLING or "\u2018" <= c <= "\u201e" or (c.isspace() and c not in " \t")
        for c in word
    ):
        return None
    bare = word and all(c.isalnum() or c in "._-/:+" or (c == "=" and not head) for c in word)
    if bare and (_NUMBER_LIKE.fullmatch(word) and not _PLAIN_INT.fullmatch(word)):
        bare = False
    if head and not bare:  # no quoted head runs alike in cmd, PowerShell and Git Bash
        return None
    return word if bare else f'"{word}"'


def quote(word: str, caps: Caps | None = None) -> str:
    """One argument inside a sentence; a word with no safe spelling stands as itself. A runnable
    line is :func:`command`'s."""
    return spell(word, caps) or word


def head(word: str, caps: Caps | None = None) -> str:
    """A command's first word; one with no spelling stands as itself."""
    return spell(word, caps, head=True) or word


def _shown(word: str) -> str:
    return "".join(c if c.isprintable() else c.encode("unicode_escape").decode() for c in word)


def _spelled(argv: Sequence[str], caps: Caps) -> list[str | None]:
    return [spell(argv[0], caps, head=True), *(spell(w, caps) for w in argv[1:])]


def _inline(argv: Sequence[str], caps: Caps) -> tuple[str, bool]:
    words = _spelled(argv, caps)
    text = " ".join(_shown(w) if s is None else s for w, s in zip(argv, words, strict=True))
    bad = [_shown(w) for w, s in zip(argv, words, strict=True) if s is None]
    return (f"{text}, quoting {', '.join(bad)} for your shell", False) if bad else (text, True)


def inline(*argv: str, caps: Caps | None = None) -> str:
    """*argv* as text inside a sentence that is itself an ``Agent action:``: the line when every
    word has a safe spelling, else the words as they are and ``, quoting <word> for your shell``,
    so it never reads as a runnable line and no Agent action nests in another."""
    return _inline(argv, caps or detect())[0]


def command(*argv: str, caps: Caps | None = None) -> str:
    """The finished command line of *argv*, real values included; with a word that has no safe
    spelling on the host, ``Agent action: run `` and :func:`inline`'s text instead."""
    text, safe = _inline(argv, caps or detect())
    return text if safe else act("agent", f"run {text}")


def mkdir_line(directory: PurePath, caps: Caps | None = None) -> str:
    """Create *directory* and its parents, idempotent: one interpreter line that runs unchanged
    under sh, bash, cmd and PowerShell, the path its own argv word."""
    code = "import pathlib, sys; pathlib.Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)"
    return command(sys.executable, "-c", code, str(directory), caps=caps)


_LABELS = {"agent": "Agent action", "operator": "Operator action"}


def act(kind: Literal["agent", "operator"], text: str) -> str:
    """*text* behind the label of *kind* (``agent`` or ``operator``); any other *kind* raises ``ValueError``."""
    if kind not in _LABELS:
        raise ValueError(f"unknown action kind {kind!r}")
    return f"{_LABELS[kind]}: {text}"


def git_line(repo: Path | str, *argv: str, caps: Caps | None = None) -> str:
    """``git -C <repo> argv…`` as a finished command line (:func:`command`)."""
    return command("git", "-C", str(repo), *argv, caps=caps)


def git_inline(repo: Path | str, *argv: str, caps: Caps | None = None) -> str:
    """``git -C <repo> argv…`` as text inside an ``Agent action:`` sentence (:func:`inline`)."""
    return inline("git", "-C", str(repo), *argv, caps=caps)
