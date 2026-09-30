"""Venv-determinism PreToolUse policy: a Bash command whose FIRST token is a bare ``dadaia``,
``pip``/``pip3`` or ``python[3] -m dadaia_workspace`` is BLOCKED with one ``fix:`` — the
absolute venv command. A venv-rooted token, ``$DADAIA_BIN``, any other shape or an
unparseable payload is ALLOWED (fail-open)."""

from __future__ import annotations

import shlex

from dadaia_workspace.core.cli_line import fix_line, venv_line

_PIP_NAMES: frozenset[str] = frozenset({"pip", "pip3"})
_PYTHON_NAMES: frozenset[str] = frozenset({"python", "python3"})
_VENV_BIN = ".dadaia/.venv/bin/"
_ALLOWED_PREFIXES: tuple[str, ...] = ("$DADAIA_BIN", "${DADAIA_BIN}")


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """The block reason for a non-venv workspace invocation, else ``None`` (ALLOW)."""
    if str(payload.get("tool_name") or "") != "Bash":
        return None
    inp = payload.get("tool_input")
    command = (inp if isinstance(inp, dict) else payload).get("command")
    if not isinstance(command, str):
        return None
    try:
        args = shlex.split(command, comments=False, posix=True)
    except ValueError:
        return None
    if not args or args[0].startswith(_ALLOWED_PREFIXES) or _VENV_BIN in args[0]:
        return None
    token = args[0]
    rest = command.strip()[len(token) :].lstrip()
    tail = f" {rest}" if rest else ""
    if token == "dadaia":
        corrected = fix_line(None) + tail
    elif token in _PIP_NAMES:
        corrected = venv_line(None, token) + tail
    elif (
        token in _PYTHON_NAMES
        and args[1:2] == ["-m"]
        and len(args) >= 3
        and _is_dadaia_module(args[2])
    ):
        corrected = venv_line(None, "python", *args[1:])
    else:
        return None
    return (
        "[VENV GUARD] This command must run from the workspace venv "
        f"({_VENV_BIN}). Blocked:\n"
        f"  {command.strip()}\n"
        "(pytest/ruff/mypy are never matched by this rule; set $DADAIA_BIN to override.)\n"
        f"fix: {corrected}"
    )


def _is_dadaia_module(module: str) -> bool:
    return module == "dadaia_workspace" or module.startswith("dadaia_workspace.")
