"""Venv-determinism PreToolUse policy: every command of a Bash line is judged. One whose first
word (past ``NAME=value`` and reserved words) is a ``dadaia`` or ``python[3] -m dadaia_workspace``
not ending in the workspace venv path is BLOCKED with one ``fix:``; any other shape (``pip``
included, ADR 0134) or an unparseable payload is ALLOWED. Caveats: bash syntax only (Git Bash on
Windows loses an unquoted ``C:\\x`` path's backslashes as bash does); not judged: PowerShell,
``$(...)``, backticks, ``bash -c``, ``env``/``xargs``/``sudo``/``exec``, heredocs, ``time -p``;
a quoted operator-only argument reads as a boundary (a false block)."""

from __future__ import annotations

import re
import shlex

from dadaia_workspace.core import platform
from dadaia_workspace.core.cli_line import venv_line

_OPERATORS = ";()<>|&\n"
_BOUNDARY = frozenset(";&|()\n")
_SKIP = frozenset({"{", "!", "if", "then", "do", "else", "elif", "while", "until", "time"})
_ASSIGN = re.compile(r"[A-Za-z_]\w*=")


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """The block reason for a non-venv workspace invocation, else ``None`` (ALLOW)."""
    if str(payload.get("tool_name") or "") != "Bash":
        return None
    inp = payload.get("tool_input")
    command = (inp if isinstance(inp, dict) else payload).get("command")
    if not isinstance(command, str):
        return None
    lex = shlex.shlex(command, posix=True, punctuation_chars=_OPERATORS)
    lex.whitespace, lex.whitespace_split, lex.commenters = " \t\r", True, ""
    try:
        tokens = list(lex)
    except ValueError:
        return None
    venv_bin = f".dadaia/.venv/{platform.PLATFORM.venv_scripts_dir}/"
    words: list[str] = []
    for token in [*tokens, ";"]:
        if not set(token) <= _BOUNDARY:
            words.append(token)
            continue
        tool = _unrooted_tool(words, venv_bin)
        if tool:
            tail = "".join(f" {w if set(w) <= _BOUNDARY else shlex.quote(w)}" for w in words[1:])
            return (
                "[VENV GUARD] This command must run from the workspace venv "
                f"({venv_bin}). Blocked:\n"
                f"  {command.strip()}\n"
                f"fix: {venv_line(None, tool)}{tail}"
            )
        words = []
    return None


def _unrooted_tool(words: list[str], venv_bin: str) -> str | None:
    """``dadaia`` or ``python`` when the command's first word is that tool outside the venv."""
    while words and (words[0] in _SKIP or _ASSIGN.match(words[0])):
        del words[0]
    if not words:
        return None
    word = words[0].replace("\\", "/")
    name = word.rsplit("/", 1)[-1]
    suffix = platform.PLATFORM.venv_exe_suffix
    stem = name.removesuffix(suffix)
    if stem == "dadaia":
        tool = "dadaia"
    elif (
        stem in {"python", "python3"}
        and words[1:2] == ["-m"]
        and words[2:3]
        and words[2].split(".")[0] == "dadaia_workspace"
    ):
        tool = "python"
    else:
        return None
    rooted = word.endswith(venv_bin + name) and name.endswith(suffix)
    return None if rooted else tool
