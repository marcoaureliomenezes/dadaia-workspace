"""Venv-determinism — one narrow Bash PreToolUse policy, one rule (ADR-G4).

The workspace law requires ``dadaia`` / ``pip`` / ``python -m dadaia_workspace`` to run
from the workspace venv, never a system interpreter. Narrow on purpose:

- **First command token only** — no shell parsing; a token inside a quoted string or
  after ``&&`` is never the leading token and never blocks (ADR-G1 zero-false-block).
- **Three families**: a bare ``dadaia``, a bare ``pip``/``pip3``, ``python[3] -m
  dadaia_workspace``. ``pytest``/``ruff``/``mypy`` are never matched (their caches are
  configured away in ``pyproject.toml``).
- **ALLOW**: an already venv-rooted token, a ``$DADAIA_BIN`` override, a foreign path
  that merely ends in ``pip``/``dadaia``.

A match is BLOCKED with one ``fix:`` — the absolute venv command (``core.cli_line``) —
and any unexpected payload shape is ALLOW (fail-open).
"""

from __future__ import annotations

import shlex

from dadaia_workspace.core.cli_line import fix_line, venv_line

#: Bare entrypoint names that must run from the workspace venv.
_DADAIA_ENTRYPOINT = "dadaia"
_PIP_NAMES: frozenset[str] = frozenset({"pip", "pip3"})
_PYTHON_NAMES: frozenset[str] = frozenset({"python", "python3"})

#: The venv bin prefix the message names.
_VENV_BIN = ".dadaia/.venv/bin/"

#: Leading-token forms that are already venv-rooted or operator-overridden → ALLOW.
_ALLOWED_PREFIXES: tuple[str, ...] = ("$DADAIA_BIN", "${DADAIA_BIN}")


def _first_token(command: str) -> str | None:
    """Return the FIRST whitespace-delimited command token, honoring shell quoting.

    Uses ``shlex.split`` so a quoted leading argument is parsed as one token (and a token
    *inside* quotes is therefore never the leading bare word). Returns ``None`` when the
    command is empty or cannot be lexed (caller fails open → ALLOW). We never parse beyond
    the first token: ``shlex`` errors (unbalanced quotes) fail open.
    """
    if not command.strip():
        return None
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        return None
    return tokens[0] if tokens else None


def _is_venv_rooted(token: str) -> bool:
    """True when *token* is already rooted in a ``.dadaia/.venv/bin/`` path.

    Matches both the relative canonical form (``.dadaia/.venv/bin/dadaia``) and the
    workspace-absolute equivalent (``/…/.dadaia/.venv/bin/dadaia``). A foreign venv bin
    (``repos/other/.venv/bin/pip``) does NOT contain this exact segment and so is treated
    as out of scope — it is not one of the bare names below either, so it ALLOWS.
    """
    return _VENV_BIN in token


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """Return a block reason for a non-venv workspace invocation, else ``None`` (ALLOW).

    Only Bash-family tool calls carrying a ``command`` are inspected (Claude ``Bash`` and
    the Codex shell event share the ``tool_input.command`` shape). Any other tool, an
    empty/absent command, or an unparseable command fails open.
    """
    name = str(payload.get("tool_name") or "")
    if name != "Bash":
        return None
    inp = payload.get("tool_input")
    src = inp if isinstance(inp, dict) else payload
    command = src.get("command")
    if not isinstance(command, str):
        return None

    token = _first_token(command)
    if token is None:
        return None

    # Already correct or explicitly overridden → ALLOW (venv-rooting rule, ADR-G4).
    if token.startswith(_ALLOWED_PREFIXES) or _is_venv_rooted(token):
        return None

    # We only match the BARE command name as the leading token. A path with a
    # foreign directory (``repos/x/pip.py``, ``./pip-helper.sh``, another venv's bin)
    # has a basename that differs and/or is not a bare name → ALLOW.
    rest = command.strip()[len(token) :].lstrip()

    if token == _DADAIA_ENTRYPOINT:
        # The builder spells the CLI; the agent's own arguments follow verbatim.
        corrected = fix_line(None) + (f" {rest}" if rest else "")
        return _block_message(command.strip(), corrected)

    if token in _PIP_NAMES:
        corrected = venv_line(None, token) + (f" {rest}" if rest else "")
        return _block_message(command.strip(), corrected)

    if token in _PYTHON_NAMES:
        # Only the ``python -m dadaia_workspace`` form is in scope (ADR-G4).
        try:
            args = shlex.split(command, comments=False, posix=True)
        except ValueError:
            return None
        if len(args) >= 3 and args[1] == "-m" and _is_dadaia_module(args[2]):
            corrected = venv_line(None, "python", *args[1:])
            return _block_message(command.strip(), corrected)
        return None

    return None


def _is_dadaia_module(module: str) -> bool:
    """True when *module* is ``dadaia_workspace`` or a submodule of it."""
    return module == "dadaia_workspace" or module.startswith("dadaia_workspace.")


def _block_message(original: str, corrected: str) -> str:
    return (
        "[VENV GUARD] This command must run from the workspace venv "
        f"({_VENV_BIN}). Blocked:\n"
        f"  {original}\n"
        "(pytest/ruff/mypy are never matched by this rule; set $DADAIA_BIN to override.)\n"
        f"fix: {corrected}"
    )
