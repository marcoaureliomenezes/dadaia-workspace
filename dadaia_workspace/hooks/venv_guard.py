"""Venv-determinism guard — narrow Bash PreToolUse policy (FR-W3-01, ADR-G4, T-014-12).

The workspace law (root ``AGENTS.md``) requires ``dadaia`` / ``pip`` / ``python -m
dadaia_workspace`` to run from the workspace venv (``.dadaia/.venv/bin/``), never from a
system interpreter. This policy enforces that for Bash tool calls — and **only** that.

ADR-G4 narrowness is deliberate and load-bearing:

- **First command token only.** We inspect the leading whitespace-delimited token of the
  command string. There is NO general shell parsing: we do not split on ``&&``, strip
  ``cd … &&`` prefixes, expand env vars, or descend into quoted sub-commands. A token
  buried inside a quoted string (``echo "pip install"``) is therefore never the leading
  token and never blocks (ADR-G1 zero-false-block).
- **Fixed pattern set.** Only three families match: a bare ``dadaia`` entrypoint, a bare
  ``pip``/``pip3``, and ``python``/``python3 -m dadaia_workspace``. Everything else flows.
- **Explicit exclusions.** ``pytest``, ``ruff``, and ``mypy`` are NOT matched (ADR-G4):
  they are run directly by agents and reviewers and are out of scope for this guard.

A matched-but-not-venv-rooted invocation is BLOCKED with a message that contains the
corrected, venv-rooted command so the agent can copy-paste the fix.

False-block guards (ADR-G1):

- An already-venv-rooted leading token (``.dadaia/.venv/bin/dadaia`` or a
  workspace-absolute ``…/.dadaia/.venv/bin/…``) → ALLOW.
- A ``$DADAIA_BIN`` / ``${DADAIA_BIN}`` override leading token → ALLOW.
- A *foreign* explicit bin path that happens to end in ``pip``/``dadaia`` (another venv,
  an in-repo ``repos/x/pip.py``, a ``./pip-helper.sh``) → ALLOW. We only match the bare
  command names and the ``python -m dadaia_workspace`` form, never an arbitrary path that
  merely contains the substring.

The policy is pure and fail-open: any unexpected payload shape returns ``None`` (ALLOW),
so a malformed envelope can never deadlock the harness.
"""

from __future__ import annotations

import shlex

#: Bare entrypoint names that must run from the workspace venv.
_DADAIA_ENTRYPOINT = "dadaia"
_PIP_NAMES: frozenset[str] = frozenset({"pip", "pip3"})
_PYTHON_NAMES: frozenset[str] = frozenset({"python", "python3"})

#: The canonical venv bin prefix (relative form printed in the corrected command).
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


def _basename(token: str) -> str:
    """Return the trailing path component of *token* (POSIX ``/`` separator)."""
    return token.rsplit("/", 1)[-1]


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """Return a block reason for a non-venv workspace invocation, else ``None`` (ALLOW).

    Only Bash-family tool calls carrying a ``command`` are inspected (Claude ``Bash`` and
    the Codex shell event share the ``tool_input.command`` shape). Any other tool, an
    empty/absent command, or an unparseable command fails open.
    """
    name = str(payload.get("tool_name") or payload.get("tool") or "")
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

    # Already correct or explicitly overridden → ALLOW.
    if token.startswith(_ALLOWED_PREFIXES) or _is_venv_rooted(token):
        return None

    # We only match the BARE command name as the leading token. A path with a
    # foreign directory (``repos/x/pip.py``, ``./pip-helper.sh``, another venv's bin)
    # has a basename that differs and/or is not a bare name → ALLOW.
    rest = command.strip()[len(token) :].lstrip()

    if token == _DADAIA_ENTRYPOINT:
        corrected = f"{_VENV_BIN}{_DADAIA_ENTRYPOINT}" + (f" {rest}" if rest else "")
        return _block_message(command.strip(), corrected)

    if token in _PIP_NAMES:
        corrected = f"{_VENV_BIN}{token}" + (f" {rest}" if rest else "")
        return _block_message(command.strip(), corrected)

    if token in _PYTHON_NAMES:
        # Only the ``python -m dadaia_workspace`` form is in scope (ADR-G4).
        try:
            args = shlex.split(command, comments=False, posix=True)
        except ValueError:
            return None
        if len(args) >= 3 and args[1] == "-m" and _is_dadaia_module(args[2]):
            corrected = f"{_VENV_BIN}python " + " ".join(args[1:])
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
        "Use the venv-rooted form instead:\n"
        f"  {corrected}\n"
        "(pytest/ruff/mypy are exempt; set $DADAIA_BIN to override.)"
    )
