"""The ONE authority for every harness's hook wiring, as data (``HOOK_DIALECTS``).

A row per :class:`~dadaia_workspace.core.harness_registry.HookFormat` names the behaviour
lanes (gate, post-gate, context injection, reaper), the files that register them and how
the harness reads a deny. Each lane is a generated, self-locating wrapper: it resolves the
venv interpreter from its own path (a user-level shim: from the hook cwd), never ``PATH``;
a missing venv warns and exits 0.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from dadaia_workspace.core.harness_registry import HarnessRecord, HookFormat

#: The SessionStart lane: the one reaper, run as a CLI process at every
#: session start — never a hook module (P-12). ``--quiet`` prints only what it deleted, so
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
    ``env`` exports; ``decides`` marks the lane whose stdout a :class:`HookAnswer` remaps."""

    name: str
    argv: str
    env: tuple[tuple[str, str], ...] = ()
    decides: bool = False
    timeout: int = SESSION_TIMEOUT_S

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


#: Resolve the workspace from the wrapper's OWN location — never a ``PATH`` lookup.
_SELF_ROOT = 'ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)\n'
#: A user-level shim serves every workspace: walk up from the hook cwd to the nearest
#: sentinel; none -> not a workspace, exit 0.
_CWD_ROOT = (
    "ROOT=$PWD\n"
    'while [ ! -f "$ROOT/.dadaia/states/spec_contexts.json" ]; do\n'
    '  [ "$ROOT" = / ] && exit 0\n'
    '  ROOT=$(dirname "$ROOT")\n'
    "done\n"
)


@dataclass(frozen=True)
class HookDialect:
    """Everything one :class:`HookFormat` serializes differently.

    ``files`` are rendered by :func:`hook_documents`; ``nested`` groups each entry as
    ``{matcher, hooks: [entry]}``; ``bare`` drops the top-level ``hooks`` key; ``prefix``
    precedes every command; ``ungated`` states the actions with no pre-action event.
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
    root: str = _SELF_ROOT
    ungated: tuple[str, ...] = ()

    def timeout(self, lane: str) -> int:
        return next(each.timeout for each in self.lanes if each.name == lane)


_GATE = HookLane("pre-gate", 'dadaia_workspace.hooks.pre_gate "$@"', (), True, TOOL_TIMEOUT_S)
_REAPER = HookLane("doctor-expired", f"dadaia_workspace {REAPER_ARGS}")
_POST = HookLane("post-gate", 'dadaia_workspace.hooks.sdd_post_gate "$@"', timeout=TOOL_TIMEOUT_S)
_CTX = HookLane("ctx-inject", 'dadaia_workspace.hooks.ctx_inject "$@"')
_CODEX_OUT = ("DADAIA_HOOK_OUTPUT", "codex-json")
_KIMI = ("DADAIA_RUNTIME", "kimi-code")
_START = ("DADAIA_HOOK_EVENT", "SessionStart")
_REAP = ("SessionStart", "doctor-expired", "startup|resume")

#: One row per :class:`HookFormat`, total by construction (ADR 0054: every pre-tool event
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
    ),
    HookFormat.KIMI_HOOKS: HookDialect(
        lanes=(
            replace(_GATE, env=(_KIMI,)),
            replace(_POST, env=(_KIMI,)),
            replace(_CTX, env=(_KIMI,)),
            HookLane("post-compact", _CTX.argv, (("DADAIA_HOOK_EVENT", "PostCompact"), _KIMI)),
            _REAPER,
        ),
        files=(
            HookFileSpec(
                "config.toml",
                (
                    ("PreToolUse", "pre-gate", "^(Edit|Write|Bash)$"),
                    ("PostToolUse", "post-gate", None),
                    ("UserPromptSubmit", "ctx-inject", None),
                    ("PostCompact", "post-compact", "manual|auto"),
                    ("SessionStart", "doctor-expired", None),
                ),
            ),
        ),
        answer=HookAnswer(exit_code=2),
        wrapper="dadaia-kimi-{lane}.sh",
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
            ),
            _REAPER,
        ),
        files=(
            HookFileSpec(
                "hooks.json",
                (
                    ("PreToolUse", "pre-gate", "^(apply_patch|Edit|Write|Bash)$"),
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


def hook_wrapper_command(name: str) -> str:
    """Return a direct-exec-safe hook command path for a generated wrapper."""
    return f".dadaia/hooks/{name}"


def wrapper_name(record: HarnessRecord, lane: str) -> str:
    """The wrapper filename of *record*'s *lane*."""
    return HOOK_DIALECTS[record.hooks].wrapper.format(harness=record.name, lane=lane)


#: The ONE missing-venv posture (DEC-10): warn on stderr naming the venv, exit 0.
#: ``$ROOT`` is the workspace; POSIX ``bin/python`` or Windows ``Scripts/python.exe``.
VENV_PYTHON = (
    'for PYTHON_BIN in "$ROOT/.dadaia/.venv/bin/python" "$ROOT/.dadaia/.venv/Scripts/python.exe"; do\n'
    '  [ -x "$PYTHON_BIN" ] && break\n'
    "done\n"
    'if [ ! -x "$PYTHON_BIN" ]; then\n'
    '  echo "dadaia hook: no workspace venv at $ROOT/.dadaia/.venv — hook skipped" >&2\n'
    "  exit 0\n"
    "fi\n"
)


def _translator(answer: HookAnswer) -> str:
    """Remap the gate's native envelope into *answer*'s shape, as parsed JSON (never a
    key-order text match). Only a deny is answered — no wrapper emits an explicit allow
    (ADR 0054). No single quote: it is embedded in a single-quoted ``sh`` word."""
    say = (
        f'sys.stderr.write(reason + "\\n")\n    raise SystemExit({answer.exit_code})\n'
        if answer.exit_code
        else f'print(json.dumps({{"{answer.decision_key}": "deny", "{answer.reason_key}": reason}}))\n'
    )
    return (
        "import json,sys\n"
        "try:\n"
        '    out = json.load(sys.stdin).get("hookSpecificOutput", {})\n'
        "except Exception:\n"
        "    raise SystemExit(0)\n"
        'if out.get("permissionDecision") == "deny":\n'
        '    reason = out.get("permissionDecisionReason", "")\n'
        f"    {say}"
    )


def hook_wrapper_contents(record: HarnessRecord) -> dict[str, str]:
    """Return ``{wrapper filename: script}``: one argument-free executable per lane, so
    every harness registers a plain path whether it shell-parses or direct-execs it."""
    dialect = HOOK_DIALECTS[record.hooks]
    answer = dialect.answer
    prologue = f"#!/usr/bin/env sh\nset -eu\n{dialect.root}{VENV_PYTHON}"
    wrappers: dict[str, str] = {}
    for lane in dialect.lanes:
        exports = "".join(f'{key}="{value}"\nexport {key}\n' for key, value in lane.env)
        run = f'"$PYTHON_BIN" -B -m {lane.argv}'
        if answer is not None and lane.decides:
            body = (
                f"_envelope=$({run}) || exit 0\n"
                f"printf '%s' \"$_envelope\" | \"$PYTHON_BIN\" -B -c '{_translator(answer)}'\n"
            )
        elif answer is not None and not answer.exit_code and not lane.speaks:
            body = f"exec {run} >&2\n"  # stdout is this harness's decision channel
        else:
            body = f"exec {run}\n"
        wrappers[wrapper_name(record, lane.name)] = f"{prologue}{exports}{body}"
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
