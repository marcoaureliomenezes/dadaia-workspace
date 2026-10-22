"""The ONE authority for every harness's hook wiring, as data (``HOOK_DIALECTS``).

A row per :class:`~dadaia_workspace.core.harness_registry.HookFormat` names the behaviour
lanes (gate, post-gate, context injection, reaper), the files that register them and how
the harness reads a deny. Each lane is a generated, self-locating wrapper: it resolves the
venv interpreter from its own path (a user-level shim: from the hook cwd), never ``PATH``;
a missing venv warns, tells the agent on every ctx-inject lane and exits 0.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import PurePath, PurePosixPath, PureWindowsPath

from dadaia_workspace.core import platform
from dadaia_workspace.core.cli_line import spell_fix
from dadaia_workspace.core.harness_registry import HarnessRecord, HookFormat
from dadaia_workspace.core.skill_owner import load_owner

#: The SessionStart lane: the one reaper, run as a CLI process at every
#: session start — never a hook module. ``--quiet`` prints only what it deleted, so
#: a compliant workspace adds nothing to the model context.
REAPER_ARGS = "doctor --fix --expired-only --quiet"
#: Every row's ``timeout``, in seconds — all six harnesses read that key (Copilot as the
#: documented alias of ``timeoutSec``) and let the action through when it fires.
TOOL_TIMEOUT_S, SESSION_TIMEOUT_S = 10, 30


@dataclass(frozen=True)
class HookAnswer:
    """How a harness reads a deny: a flat object on stdout, or (``exit_code``) the reason
    on stderr and that exit code. ``None`` on a dialect: it reads the native envelope."""

    decision_key: str = ""
    reason_key: str = ""
    exit_code: int = 0


@dataclass(frozen=True)
class HookLane:
    """One behaviour lane rendered as one executable: ``python -B -m <argv>`` after the
    ``env`` exports, with the harness's own arguments when it ``forwards`` them; ``decides``
    marks the lane whose stdout a :class:`HookAnswer` remaps."""

    name: str
    argv: str
    env: tuple[tuple[str, str], ...] = ()
    decides: bool = False
    timeout: int = SESSION_TIMEOUT_S
    forwards: bool = False

    @property
    def speaks(self) -> bool:
        """A lane with a ``DADAIA_HOOK_OUTPUT`` answers in its vendor's own envelope: its
        stdout is that vendor's context channel, never redirected."""
        return any(key == "DADAIA_HOOK_OUTPUT" for key, _ in self.env)


@dataclass(frozen=True)
class HookFileSpec:
    """One hook registration file and its ``(event, lane name, matcher)`` rows; a ``None``
    matcher omits the key."""

    relpath: str
    events: tuple[tuple[str, str, str | None], ...]


_SENTINEL = load_owner("dd-bug-resolution", "_root").SENTINEL
#: Resolve the workspace from the wrapper's OWN location — never a ``PATH`` lookup.
_SELF_ROOT = 'ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)\n'
#: A user-level shim serves every workspace: walk up from the hook cwd to the nearest
#: sentinel; none -> not a workspace, exit 0.
_CWD_ROOT = (
    "ROOT=$PWD\n"
    f'while [ ! -f "$ROOT/{_SENTINEL.as_posix()}" ]; do\n'
    '  [ "$ROOT" = / ] && exit 0\n'
    '  ROOT=$(dirname "$ROOT")\n'
    "done\n"
)


@dataclass(frozen=True)
class HookDialect:
    """Everything one :class:`HookFormat` serializes differently.

    ``files`` are rendered by :func:`hook_documents`; ``nested`` groups each entry as
    ``{matcher, hooks: [entry]}``; ``bare`` drops the top-level ``hooks`` key; ``prefix``
    precedes every command; ``ungated`` states the actions with no pre-action event;
    ``overrides`` name the harness's own files that outrank the registration (PROTECTED too).
    """

    lanes: tuple[HookLane, ...] = ()
    files: tuple[HookFileSpec, ...] = ()
    entry_key: str = "command"
    typed: bool = True
    version: int | None = None
    answer: HookAnswer | None = None
    nested: bool = False
    bare: bool = False
    prefix: str = ""
    wrapper: str = "{harness}-{lane}"
    windows_wrapper: str = ""
    root: str = _SELF_ROOT
    ungated: tuple[str, ...] = ()
    overrides: tuple[str, ...] = ()

    def timeout(self, lane: str) -> int:
        return next(each.timeout for each in self.lanes if each.name == lane)


_GATE = HookLane("pre-gate", "dadaia_workspace.hooks.pre_gate", (), True, TOOL_TIMEOUT_S, True)
_REAPER = HookLane("doctor-expired", f"dadaia_workspace {REAPER_ARGS}")
_POST = HookLane(
    "post-gate", "dadaia_workspace.hooks.sdd_post_gate", timeout=TOOL_TIMEOUT_S, forwards=True
)
_CTX = HookLane("ctx-inject", "dadaia_workspace.hooks.ctx_inject", forwards=True)
_CODEX_OUT = ("DADAIA_HOOK_OUTPUT", "codex-json")
_KIMI = ("DADAIA_RUNTIME", "kimi-code")
_START = ("DADAIA_HOOK_EVENT", "SessionStart")
_REAP = ("SessionStart", "doctor-expired", "startup|resume")

#: One row per :class:`HookFormat`, total by construction: every pre-tool event
#: is gated; a format with no blocking contract declares ``ungated``).
HOOK_DIALECTS: dict[HookFormat, HookDialect] = {
    HookFormat.NONE: HookDialect(),
    HookFormat.CLAUDE_SETTINGS: HookDialect(
        lanes=(_GATE, _POST, _CTX, _REAPER),
        files=(
            HookFileSpec(
                "settings.json",
                (
                    ("PreToolUse", "pre-gate", "Edit|Write|MultiEdit|NotebookEdit|Bash"),
                    ("PostToolUse", "post-gate", "*"),
                    ("UserPromptSubmit", "ctx-inject", ""),
                    *(
                        ("SessionStart", "ctx-inject", m)
                        for m in ("compact", "clear", "startup", "resume")
                    ),
                    _REAP,
                ),
            ),
        ),
        nested=True,
        prefix='"$CLAUDE_PROJECT_DIR"/',
        overrides=("settings.local.json",),
    ),
    HookFormat.KIMI_HOOKS: HookDialect(
        lanes=(
            _GATE,
            replace(_POST, env=(_KIMI,)),
            replace(_CTX, env=(_KIMI,)),
            HookLane(
                "post-compact",
                _CTX.argv,
                (("DADAIA_HOOK_EVENT", "PostCompact"), _KIMI),
                forwards=True,
            ),
            _REAPER,
        ),
        files=(
            HookFileSpec(
                "config.toml",
                (
                    ("PreToolUse", "pre-gate", "^(Edit|Write)$"),
                    ("PostToolUse", "post-gate", None),
                    ("UserPromptSubmit", "ctx-inject", None),
                    ("PostCompact", "post-compact", "manual|auto"),
                    ("SessionStart", "doctor-expired", None),
                ),
            ),
        ),
        answer=HookAnswer(exit_code=2),
        wrapper="dadaia-kimi-{lane}.sh",
        windows_wrapper="dadaia-kimi-{lane}.cmd",
        root=_CWD_ROOT,
    ),
    HookFormat.CODEX_HOOKS: HookDialect(
        lanes=(
            _GATE,
            _POST,
            replace(_CTX, env=(_CODEX_OUT,)),
            HookLane(
                "ctx-inject-session-start",
                _CTX.argv,
                (_CODEX_OUT, _START),
                forwards=True,
            ),
            _REAPER,
        ),
        files=(
            HookFileSpec(
                "hooks.json",
                (
                    ("PreToolUse", "pre-gate", "^(apply_patch|Edit|Write)$"),
                    ("PostToolUse", "post-gate", None),
                    ("SessionStart", "ctx-inject-session-start", "startup|resume"),
                    _REAP,
                    ("UserPromptSubmit", "ctx-inject", None),
                ),
            ),
        ),
        nested=True,
    ),
    HookFormat.CURSOR_HOOKS: HookDialect(
        lanes=(_GATE, replace(_CTX, env=(("DADAIA_HOOK_OUTPUT", "cursor-json"), _START)), _REAPER),
        files=(
            HookFileSpec(
                "hooks.json",
                (
                    ("preToolUse", "pre-gate", None),
                    ("sessionStart", "ctx-inject", None),
                    ("sessionStart", "doctor-expired", None),
                ),
            ),
        ),
        typed=False,
        version=1,
        answer=HookAnswer("permission", "agent_message"),
    ),
    HookFormat.DEVIN_HOOKS: HookDialect(
        lanes=(_GATE, _CTX, _REAPER),
        files=(
            HookFileSpec(
                "hooks.v1.json",
                (
                    ("PreToolUse", "pre-gate", ""),
                    ("UserPromptSubmit", "ctx-inject", ""),
                    ("SessionStart", "ctx-inject", ""),
                    ("SessionStart", "doctor-expired", ""),
                ),
            ),
        ),
        nested=True,
        bare=True,
    ),
    HookFormat.COPILOT_HOOKS: HookDialect(
        lanes=(_GATE, replace(_CTX, env=(("DADAIA_HOOK_OUTPUT", "copilot-json"), _START)), _REAPER),
        files=(
            HookFileSpec("hooks/pre-tool-use.json", (("preToolUse", "pre-gate", None),)),
            HookFileSpec(
                "hooks/session-start.json",
                (("sessionStart", "ctx-inject", None), ("sessionStart", "doctor-expired", None)),
            ),
        ),
        entry_key="bash",
        version=1,
        answer=HookAnswer("permissionDecision", "permissionDecisionReason"),
    ),
}


def envelope(env: Mapping[str, str], text: str) -> str:
    """*text* in the context envelope *env*'s ``DADAIA_HOOK_OUTPUT`` names — each vendor's
    documented key, Codex's naming ``DADAIA_HOOK_EVENT`` — else plain text."""
    event = env.get("DADAIA_HOOK_EVENT", "UserPromptSubmit")
    native = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
    shaped = {"codex-json": native, "cursor-json": {"additional_context": text}}
    shaped["copilot-json"] = {"additionalContext": text}
    out = shaped.get(env.get("DADAIA_HOOK_OUTPUT", ""))
    return text if out is None else json.dumps(out) + "\n"


def hook_wrapper_command(name: str) -> str:
    """Return a direct-exec-safe hook command path for a generated wrapper."""
    return f".dadaia/hooks/{name}"


def _runs_cmd(dialect: HookDialect, caps: platform.Capabilities | None) -> bool:
    """Whether *dialect*'s shell on *caps* (default: this host) is ``cmd.exe``."""
    return bool(dialect.windows_wrapper) and (caps or platform.PLATFORM).windows


def wrapper_name(
    record: HarnessRecord, lane: str, caps: platform.Capabilities | None = None
) -> str:
    """The wrapper filename of *record*'s *lane* on *caps* (default: this host)."""
    dialect = HOOK_DIALECTS[record.hooks]
    name = dialect.windows_wrapper if _runs_cmd(dialect, caps) else dialect.wrapper
    return name.format(harness=record.name, lane=lane)


_POSIX, _WINDOWS = platform.Capabilities.detect("linux"), platform.Capabilities.detect("win32")
#: The workspace venv as each shell spells it, the root left open (``$ROOT``, ``%ROOT%``).
_SH_VENV = platform.venv_dir(PurePosixPath("$ROOT"))
_CMD_VENV = platform.venv_dir(PureWindowsPath("%ROOT%"))
#: The one missing-venv posture: warn on stderr naming the venv, ``{tell}`` the
#: agent (a ctx-inject lane), exit 0. ``$ROOT`` is the workspace (``$ESC`` JSON-escaped);
#: POSIX ``bin/python`` or Windows ``Scripts/python.exe``.
VENV_PYTHON = (
    f'for PYTHON_BIN in "{platform.python_in(_SH_VENV, _POSIX)}" "{platform.python_in(_SH_VENV, _WINDOWS)}"; do\n'
    '  [ -x "$PYTHON_BIN" ] && break\n'
    "done\n"
    'if [ ! -x "$PYTHON_BIN" ]; then\n'
    '  echo "{warning}" >&2\n'
    """  ESC=$(printf '%s' "$ROOT" | sed 's/[\\\\"]/\\\\&/g')\n"""
    "{tell}  exit 0\n"
    "fi\n"
)
#: What every venv-less firing says on stderr, and ctx-inject tells the agent; ``{venv}`` is open.
VENV_WARNING = "dadaia hook: no workspace venv at {venv} \u2014 hook skipped"
VENV_MISSING = (
    "dadaia: no workspace venv at {venv} \u2014 the gate is off.\n"
    + spell_fix(load_owner("dd-bug-resolution", "_jsonl").REINSTALL_ACT)
    + "\n"
)


def _told(lane: HookLane, venv: PurePath) -> str:
    """What a ctx-inject *lane* tells the agent about *venv*, in its envelope; empty elsewhere."""
    if lane.argv != _CTX.argv:
        return ""
    return envelope(dict(lane.env), VENV_MISSING.replace("{venv}", str(venv)))


def _tell(lane: HookLane) -> str:
    """A ctx-inject *lane*'s ``printf`` of :func:`_told`, root slot open."""
    if not (text := _told(lane, _SH_VENV)):
        return ""
    slot = "'\"$ESC\"'" if lane.speaks else "'\"$ROOT\"'"
    text = text.replace("'", "'\\''")  # for a single-quoted sh word
    return f"  printf '%s' '{slot.join(text.split('$ROOT'))}'\n"


def _oem(text: str) -> str:
    """*text* for a batch file, which cmd reads in the OEM code page: the dash folds to ASCII."""
    return text.replace("\u2014", "-")


def _cmd_script(lane: HookLane, dialect: HookDialect) -> str:
    """The ``cmd.exe`` batch of *lane*, the same contract as the sh wrapper: the workspace is the
    nearest sentinel from the cwd, a missing venv warns and exits 0, a deciding lane's deny
    becomes the dialect's exit code. CRLF, as batch labels require."""
    python = '"%PYTHON_BIN%" -B -m'
    run = f"{python} {lane.argv}{' %*' if lane.forwards else ''}"
    if dialect.answer is not None and lane.decides:
        run += f" | {python} dadaia_workspace.hooks.translate {dialect.answer.exit_code}"
    # ponytail: echo breaks on a workspace path holding & or ^ (the exit stays 0); quote it if one appears
    tell = _oem(_told(lane, _CMD_VENV))  # a cmd dialect speaks plain text; JSON would need escaping
    lines = [
        "@echo off",
        "setlocal EnableExtensions DisableDelayedExpansion",
        'set "ROOT=%CD%"',
        ":up",
        f'if exist "%ROOT%\\{PureWindowsPath(_SENTINEL)}" goto found',
        'for %%I in ("%ROOT%\\..") do set "UP=%%~fI"',
        'if "%UP%"=="%ROOT%" exit /b 0',
        'set "ROOT=%UP%"',
        "goto up",
        ":found",
        f'set "PYTHON_BIN={platform.python_in(_CMD_VENV, _WINDOWS)}"',
        'if exist "%PYTHON_BIN%" goto run',
        f"echo {_oem(VENV_WARNING.replace('{venv}', str(_CMD_VENV)))}>&2",
        *(f"echo {line}" for line in tell.splitlines()),
        "exit /b 0",
        ":run",
        *(f'set "{key}={value}"' for key, value in lane.env),
        run,
        "exit /b %ERRORLEVEL%",
        "",
    ]
    return "\r\n".join(lines)


def hook_wrapper_contents(
    record: HarnessRecord, caps: platform.Capabilities | None = None
) -> dict[str, str]:
    """Return ``{wrapper filename: script}`` on *caps* (default: this host): one argument-free
    executable per lane, so every harness registers a plain path whether it shell-parses or
    direct-execs it."""
    dialect = HOOK_DIALECTS[record.hooks]
    answer = dialect.answer
    wrappers: dict[str, str] = {}
    for lane in dialect.lanes:
        if lane.decides:  # the gate finds its harness record by this label
            lane = replace(lane, env=(*lane.env, ("DADAIA_RUNTIME", record.name)))
        name = wrapper_name(record, lane.name, caps)
        if _runs_cmd(dialect, caps):
            wrappers[name] = _cmd_script(lane, dialect)
            continue
        warning = VENV_WARNING.replace("{venv}", str(_SH_VENV))
        venv = VENV_PYTHON.format(warning=warning, tell=_tell(lane))
        prologue = f"#!/usr/bin/env sh\nset -eu\n{dialect.root}{venv}"
        exports = "".join(f'{key}="{value}"\nexport {key}\n' for key, value in lane.env)
        run = f'"$PYTHON_BIN" -B -m {lane.argv}{' "$@"' if lane.forwards else ""}'
        if answer is not None and lane.decides:
            words = (
                str(answer.exit_code)
                if answer.exit_code
                else f"{answer.decision_key} {answer.reason_key}"
            )
            body = (
                f"_envelope=$({run}) || exit 0\n"
                f'printf \'%s\' "$_envelope" | "$PYTHON_BIN" -B -m dadaia_workspace.hooks.translate {words}\n'
            )
        elif answer is not None and not answer.exit_code and not lane.speaks:
            body = f"exec {run} >&2\n"  # stdout is this harness's decision channel
        else:
            body = f"exec {run}\n"
        wrappers[name] = f"{prologue}{exports}{body}"
    return wrappers


def hook_documents(record: HarnessRecord) -> dict[str, dict[str, object]]:
    """Return ``{path relative to the record's directory: hook registration document}``;
    every event cites its lane's wrapper — a registration, never a copy of the behaviour."""
    dialect = HOOK_DIALECTS[record.hooks]
    documents: dict[str, dict[str, object]] = {}
    for spec in dialect.files:
        hooks: dict[str, list[object]] = {}
        for event, lane, matcher in spec.events:
            entry: dict[str, object] = {"type": "command"} if dialect.typed else {}
            entry[dialect.entry_key] = dialect.prefix + hook_wrapper_command(
                wrapper_name(record, lane)
            )
            entry["timeout"] = dialect.timeout(lane)
            group: dict[str, object] = {"hooks": [entry]}
            if matcher is not None:
                group["matcher"] = matcher
            hooks.setdefault(event, []).append(group if dialect.nested else entry)
        document: dict[str, object] = dict(hooks) if dialect.bare else {"hooks": hooks}
        if dialect.version is not None:
            document["version"] = dialect.version
        documents[spec.relpath] = document
    return documents
