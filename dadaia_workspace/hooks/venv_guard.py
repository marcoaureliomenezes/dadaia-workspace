"""Venv-determinism + cache guard — narrow Bash PreToolUse policy.

(FR-W3-01, ADR-G4, T-014-12 — venv-rooting; FR28, T-043-43 — the cache guard.)

Two independent, orthogonal rules live in this one module (one Bash PreToolUse slot,
one policy function — ``pre_gate`` wires exactly one call site):

**Rule 1 — venv-rooting (ADR-G4, unchanged).** The workspace law (root ``AGENTS.md``)
requires ``dadaia`` / ``pip`` / ``python -m dadaia_workspace`` to run from the workspace
venv (``.dadaia/.venv/bin/``), never from a system interpreter.

ADR-G4 narrowness is deliberate and load-bearing:

- **First command token only.** We inspect the leading whitespace-delimited token of the
  command string. There is NO general shell parsing: we do not split on ``&&``, strip
  ``cd … &&`` prefixes, expand env vars, or descend into quoted sub-commands. A token
  buried inside a quoted string (``echo "pip install"``) is therefore never the leading
  token and never blocks (ADR-G1 zero-false-block).
- **Fixed pattern set.** Only three families match: a bare ``dadaia`` entrypoint, a bare
  ``pip``/``pip3``, and ``python``/``python3 -m dadaia_workspace``. Everything else flows.
- **Explicit exclusions.** ``pytest``, ``ruff``, and ``mypy`` are NOT matched by THIS
  rule (ADR-G4): they are run directly by agents and reviewers and venv-rooting is out
  of scope for this rule — see Rule 2 below for what IS in scope for them.

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

**Rule 2 — the cache guard (FR28, T-043-43 — "the cache must not be born").** A repo
working tree must never carry ``.pytest_cache/``, ``.ruff_cache/``, or ``.mypy_cache/``
(``DADAIA.md`` §4 — "Repos stay clean"). Evidence that drove this rule: 6 duplicate mypy
caches (~68 MB) cleaned 2026-08-17; a concurrent session recreated 5 new cache dirs
(~35 MB) within 40 minutes. This rule blocks a ``pytest``/``ruff``/``mypy`` Bash
invocation that is missing the flag that stops it from writing that cache in-repo:

- ``pytest`` without the adjacent pair ``-p no:cacheprovider``.
- ``ruff check`` / ``ruff format`` without ``--no-cache`` (both subcommands write
  ``.ruff_cache/``; every OTHER ruff subcommand — ``--version``, ``rule``, ``config``,
  ``linter`` … — never writes a cache and is out of scope, never blocked).
- ``mypy`` without ``--cache-dir`` (or its ``--cache-dir=PATH`` form) present anywhere
  in the args. ``incremental = false`` in ``pyproject.toml`` does NOT stop mypy from
  creating ``.mypy_cache/`` — only redirecting the cache dir does (see the
  ``[tool.mypy]`` comment in ``pyproject.toml``); presence of the flag is all this
  fixed-token guard can verify (no shell parsing — it does not resolve or judge the
  destination path), matching A28.3's letter.

Recognition uses the SAME fixed-leading-token discipline as Rule 1 (see
``_cache_tool_name``): the leading token must be the BARE name (``pytest``/``ruff``/
``mypy``) or a token rooted in OUR OWN ``.dadaia/.venv/bin/`` whose basename is exactly
one of the three names. A foreign venv's pytest/ruff/mypy, a quoted string, an in-repo
path merely ending in the name, or a similarly-named tool (``pytest-watch``, ``mypyc``)
is never recognized and never blocked (A28.2). Deliberately OUT of scope, for the same
narrowness reason Rule 1 stays narrow: ``python -m pytest`` / ``python -m ruff`` /
``python -m mypy`` forms (only ``python -m dadaia_workspace`` is special-cased, by Rule
1) — extending module-invocation matching to three more modules is a bigger surface for
a false block with no evidence any agent in this workspace invokes them that way; a gap
here fails OPEN (ALLOW), never closed. Rule 2 is evaluated BEFORE Rule 1's "already
venv-rooted → ALLOW" shortcut, so it fires even for an otherwise-"already correct"
venv-rooted pytest/ruff/mypy token — the two rules are independent and both apply.

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

#: FR28 (T-043-43) — bare names the cache guard recognizes, in addition to a token
#: rooted in OUR OWN ``.dadaia/.venv/bin/`` whose basename matches one of these.
_CACHE_TOOL_NAMES: frozenset[str] = frozenset({"pytest", "ruff", "mypy"})

#: ruff subcommands that write ``.ruff_cache/`` — every other subcommand (``--version``,
#: ``rule``, ``config``, ``linter`` …) is out of scope for the cache guard.
_RUFF_CACHE_SUBCOMMANDS: frozenset[str] = frozenset({"check", "format"})

#: Suggested out-of-repo mypy cache dir carried in a corrected command (mirrors the
#: convention ``features/ci_preflight/service.py:resolve_mypy_cache_dir`` redirects to —
#: this guard suggests the parent ``.dadaia/tmp/`` form since it cannot resolve a live
#: workspace root from a bare command string).
_MYPY_CACHE_DIR_HINT = ".dadaia/tmp/mypy-cache"


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


def _cache_tool_name(token: str) -> str | None:
    """Return the recognized cache-guard tool name for *token*, else ``None``.

    Matches the BARE command name (``pytest``/``ruff``/``mypy``), or an explicit path
    provably rooted in OUR OWN venv bin (``_is_venv_rooted``) whose basename is exactly
    one of the three names. A foreign venv/path (``repos/other/.venv/bin/pytest``) is
    NOT recognized — same false-block discipline as the rest of this module (ADR-G1):
    only a bare name or our own venv-rooted path is ever matched.
    """
    if token in _CACHE_TOOL_NAMES:
        return token
    if _is_venv_rooted(token):
        base = _basename(token)
        if base in _CACHE_TOOL_NAMES:
            return base
    return None


def _has_adjacent_pair(args: list[str], first: str, second: str) -> bool:
    """True when *first* is immediately followed by *second* anywhere in *args*."""
    return any(a == first and b == second for a, b in zip(args, args[1:], strict=False))


def _has_flag(args: list[str], flag: str) -> bool:
    """True when *flag* (bare or its ``flag=VALUE`` long-option form) is in *args*."""
    prefix = f"{flag}="
    return any(a == flag or a.startswith(prefix) for a in args)


def _insert_tokens(args: list[str], index: int, insertion: list[str]) -> list[str]:
    """Return *args* with *insertion* spliced in at *index* (a new list)."""
    return [*args[:index], *insertion, *args[index:]]


def _cache_guard_reason(command: str, token: str) -> str | None:
    """FR28 (T-043-43) — block a cache-enabling mypy/pytest/ruff invocation.

    Independent of, and evaluated BEFORE, the venv-rooting rule: pytest/ruff/mypy are
    permanently exempt from venv-rooting (ADR-G4) but never exempt from THIS rule,
    whether invoked bare or through our own venv-rooted path. Returns ``None`` (ALLOW)
    for anything not recognized by :func:`_cache_tool_name`, an unparseable command, or
    an already-compliant invocation.
    """
    name = _cache_tool_name(token)
    if name is None:
        return None
    try:
        args = shlex.split(command, comments=False, posix=True)
    except ValueError:
        return None
    if not args:
        return None

    if name == "pytest":
        if _has_adjacent_pair(args, "-p", "no:cacheprovider"):
            return None
        corrected = shlex.join(_insert_tokens(args, 1, ["-p", "no:cacheprovider"]))
        return _cache_block_message(
            command.strip(),
            corrected,
            "pytest must run with `-p no:cacheprovider` — an in-repo `.pytest_cache/` "
            "must never be created.",
        )

    if name == "ruff":
        # Only `check`/`format` write a cache; every other subcommand (`--version`,
        # `rule`, `config`, `linter` …) is out of scope — no false block (A28.2).
        if len(args) < 2 or args[1] not in _RUFF_CACHE_SUBCOMMANDS:
            return None
        if _has_flag(args, "--no-cache"):
            return None
        corrected = shlex.join(_insert_tokens(args, 2, ["--no-cache"]))
        return _cache_block_message(
            command.strip(),
            corrected,
            "`ruff check`/`ruff format` must run with `--no-cache` — an in-repo "
            "`.ruff_cache/` must never be created.",
        )

    if name == "mypy":
        if _has_flag(args, "--cache-dir"):
            return None
        corrected = shlex.join(
            _insert_tokens(args, len(args), ["--cache-dir", _MYPY_CACHE_DIR_HINT])
        )
        return _cache_block_message(
            command.strip(),
            corrected,
            "mypy must run with an out-of-repo `--cache-dir` — it creates "
            "`.mypy_cache/` even with `incremental = false`.",
        )

    return None  # pragma: no cover — every _CACHE_TOOL_NAMES member is handled above.


def _cache_block_message(original: str, corrected: str, note: str) -> str:
    return (
        "[CACHE GUARD] This command must not create an in-repo cache directory "
        "(DADAIA.md, Repos stay clean; FR28). Blocked:\n"
        f"  {original}\n"
        "Use the compliant form instead:\n"
        f"  {corrected}\n"
        f"({note})"
    )


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

    # FR28 (T-043-43) — the cache guard runs FIRST and independently of the
    # venv-rooting rule below: pytest/ruff/mypy are exempt from venv-rooting but never
    # from this rule, whether invoked bare or through our own venv-rooted path.
    cache_reason = _cache_guard_reason(command, token)
    if cache_reason is not None:
        return cache_reason

    # Already correct or explicitly overridden → ALLOW (venv-rooting rule, ADR-G4).
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
        "(pytest/ruff/mypy are exempt from venv-rooting — see the separate cache "
        "guard; set $DADAIA_BIN to override.)"
    )
