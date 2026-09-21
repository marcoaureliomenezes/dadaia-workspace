"""The hook derivation as DATA: lanes, wrapper scripts and hook-file payloads.

0.4.7 FR3. The workspace defines four deterministic behaviours — root whitelist, venv
guard, SDD gate (the ONE merged ``dadaia_workspace.hooks.pre_gate`` entrypoint) and the
session-start reaper — and every harness gets the SAME four. What differs per harness is
only *serialization*, so everything that differs lives here as a row keyed by
:class:`~dadaia_workspace.core.harness_registry.HookFormat`:

- :class:`HookLane` — one behaviour lane: the argv a wrapper execs, the env it exports,
  and whether it answers a permission question.
- :class:`HookAnswer` — the harness's *answer shape*. Claude, Codex and Devin read the
  gate's own ``hookSpecificOutput`` envelope natively; Cursor and GitHub Copilot expect a
  flat object with their own key names. That translation is the WRAPPER's job, never a
  fifth behaviour: the same Python entrypoint runs everywhere and the adapter sits at the
  seam, where the foreign shape belongs.
- :class:`HookFileSpec` — which events of which file cite which lane's wrapper.

The wrapper is generated, not authored, and is **self-locating**: it resolves the venv
interpreter from its own path and never from ``PATH`` (the exit-127 bug family), so
moving or importing a workspace never leaves a stale absolute interpreter behind. The
translation runs through that same verified interpreter rather than through ``sed``
(the key-order-fragile shape the kimi shim documents), so an envelope key moving cannot
silently turn a block into an allow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from dadaia_workspace.core.harness_registry import HarnessRecord, HookFormat

#: The SessionStart lane (0.4.6 FR4/D13): the one reaper, run as a CLI process at every
#: session start — never a hook module (P-12). ``--quiet`` prints only what it deleted, so
#: a compliant workspace adds nothing to the model context.
REAPER_ARGS = "doctor --fix --expired-only --quiet"


@dataclass(frozen=True)
class HookAnswer:
    """The flat permission object a harness reads off the wrapper's stdout.

    ``None`` on a format means the harness reads the gate's native envelope and the
    wrapper needs no translation at all.
    """

    decision_key: str
    reason_key: str
    allow: str
    deny: str


@dataclass(frozen=True)
class HookLane:
    """One behaviour lane rendered as one on-disk executable.

    Args:
        name: the wrapper's suffix — its filename is ``<harness>-<name>``.
        argv: everything after ``python -B -m``; hook modules forward the harness payload
            (``"$@"``), the reaper is a fixed CLI invocation.
        env: exported before the exec, e.g. the harness's output dialect.
        decides: the lane answers a permission question, so a format with a
            :class:`HookAnswer` translates its stdout.
    """

    name: str
    argv: str
    env: tuple[tuple[str, str], ...] = ()
    decides: bool = False


@dataclass(frozen=True)
class HookFileSpec:
    """One hook registration file: its path under the record's own directory, and the
    ``(event, lane name)`` pairs it registers."""

    relpath: str
    events: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class HookDialect:
    """Everything one :class:`HookFormat` serializes differently.

    Args:
        lanes: the behaviour lanes this format wires.
        files: the hook registration files it renders (empty when the format renders its
            own richer file elsewhere, e.g. matcher-carrying Codex hooks).
        entry_key: the key holding the command path inside one hook entry.
        typed: the entry carries ``"type": "command"``.
        version: a top-level ``"version"`` field, when the format declares one.
        answer: the flat permission shape, or ``None`` for a native-envelope reader.
    """

    lanes: tuple[HookLane, ...] = ()
    files: tuple[HookFileSpec, ...] = ()
    entry_key: str = "command"
    typed: bool = True
    version: int | None = None
    answer: HookAnswer | None = None


#: The gate lane: one entrypoint, three behaviours (root whitelist, venv guard, SDD gate).
_GATE = HookLane("pre-gate", 'dadaia_workspace.hooks.pre_gate "$@"', decides=True)
#: The fourth behaviour: the session-start reaper.
_REAPER = HookLane("doctor-expired", f"dadaia_workspace {REAPER_ARGS}")
#: The four behaviours, in every format that has nothing richer to say.
_FOUR_BEHAVIOURS: tuple[HookLane, ...] = (_GATE, _REAPER)

_CODEX_LANES: tuple[HookLane, ...] = (
    _GATE,
    HookLane("post-gate", 'dadaia_workspace.hooks.sdd_post_gate "$@"'),
    HookLane(
        "ctx-inject",
        'dadaia_workspace.hooks.ctx_inject "$@"',
        env=(("DADAIA_HOOK_OUTPUT", "codex-json"),),
    ),
    HookLane(
        "ctx-inject-session-start",
        'dadaia_workspace.hooks.ctx_inject "$@"',
        env=(("DADAIA_HOOK_OUTPUT", "codex-json"), ("DADAIA_HOOK_EVENT", "SessionStart")),
    ),
    _REAPER,
)

_EMPTY = HookDialect()

#: One row per :class:`HookFormat`. Total by construction: a format with no wrappers of
#: its own (Claude's merged settings file, Kimi's user-level shims) states an empty
#: dialect rather than falling through a missing key.
#:
#: Cursor decides only on the events it exposes *before* an action — its file-edit event
#: fires after the write — so the gate rides ``beforeShellExecution``; Devin and Copilot
#: expose a real pre-tool event and get full coverage. Devin reads the gate's native
#: envelope (Claude-compatible), so it needs no answer translation.
HOOK_DIALECTS: dict[HookFormat, HookDialect] = {
    HookFormat.NONE: _EMPTY,
    HookFormat.CLAUDE_SETTINGS: _EMPTY,
    HookFormat.KIMI_HOOKS: _EMPTY,
    HookFormat.CODEX_HOOKS: HookDialect(lanes=_CODEX_LANES),
    HookFormat.CURSOR_HOOKS: HookDialect(
        lanes=_FOUR_BEHAVIOURS,
        files=(
            HookFileSpec(
                "hooks.json",
                (("beforeShellExecution", _GATE.name), ("sessionStart", _REAPER.name)),
            ),
        ),
        typed=False,
        version=1,
        answer=HookAnswer("permission", "user_message", "allow", "deny"),
    ),
    HookFormat.DEVIN_HOOKS: HookDialect(
        lanes=_FOUR_BEHAVIOURS,
        files=(
            HookFileSpec(
                "hooks.v1.json",
                (("PreToolUse", _GATE.name), ("SessionStart", _REAPER.name)),
            ),
        ),
    ),
    HookFormat.COPILOT_HOOKS: HookDialect(
        lanes=_FOUR_BEHAVIOURS,
        files=(
            HookFileSpec("hooks/pre-tool-use.json", (("preToolUse", _GATE.name),)),
            HookFileSpec("hooks/session-start.json", (("sessionStart", _REAPER.name),)),
        ),
        entry_key="bash",
        version=1,
        answer=HookAnswer("permissionDecision", "permissionDecisionReason", "allow", "deny"),
    ),
}


def hook_wrapper_command(name: str) -> str:
    """Return a direct-exec-safe hook command path for a generated wrapper."""
    return f".dadaia/hooks/{name}"


def _wrapper_name(record: HarnessRecord, lane: HookLane) -> str:
    return f"{record.name}-{lane.name}"


#: Resolve the venv interpreter from the wrapper's OWN location and refuse loudly when it
#: is missing — never a ``PATH`` lookup (the exit-127 bug family), never a silent success.
_PROLOGUE = (
    "#!/usr/bin/env sh\n"
    "set -eu\n"
    'SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
    'WORKSPACE_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)\n'
    'PYTHON_BIN="$WORKSPACE_ROOT/.dadaia/.venv/bin/python"\n'
    'if [ ! -x "$PYTHON_BIN" ]; then\n'
    '  echo "dadaia hook wrapper: missing executable $PYTHON_BIN" >&2\n'
    "  exit 127\n"
    "fi\n"
)


def _translator(answer: HookAnswer) -> str:
    """The stdin-to-stdout remap from the gate's native envelope into *answer*'s shape.

    Run through the wrapper's already-verified interpreter, so the decision travels as
    parsed JSON and never as a key-order-dependent text match. Fail-open by construction:
    an unreadable envelope prints nothing, which every harness reads as "no opinion".
    Carries no single quote — it is embedded in a single-quoted ``sh`` word.
    """
    return (
        "import json,sys\n"
        "try:\n"
        '    out = json.load(sys.stdin).get("hookSpecificOutput", {})\n'
        "except Exception:\n"
        "    raise SystemExit(0)\n"
        f'if out.get("permissionDecision") == "deny":\n'
        f'    print(json.dumps({{"{answer.decision_key}": "{answer.deny}", '
        f'"{answer.reason_key}": out.get("permissionDecisionReason", "")}}))\n'
        "else:\n"
        f'    print(json.dumps({{"{answer.decision_key}": "{answer.allow}"}}))\n'
    )


def hook_wrapper_contents(record: HarnessRecord) -> dict[str, str]:
    """Return ``{wrapper filename: script}`` for every lane *record*'s format wires.

    Harness command execution differs across surfaces: some paths shell-parse command
    strings, others direct-exec the string as an executable. The wrappers make the hook
    contract ONE executable path with no arguments or env-prefix syntax in the
    registration file, on every format that needs an on-disk executable.
    """
    dialect = HOOK_DIALECTS[record.hooks]
    wrappers: dict[str, str] = {}
    for lane in dialect.lanes:
        exports = "".join(f'{key}="{value}"\nexport {key}\n' for key, value in lane.env)
        answer = dialect.answer
        if answer is None:
            body = f'exec "$PYTHON_BIN" -B -m {lane.argv}\n'
        elif lane.decides:
            body = (
                f'_envelope=$("$PYTHON_BIN" -B -m {lane.argv}) || exit 0\n'
                'printf \'%s\' "$_envelope" | "$PYTHON_BIN" -B -c \''
                # The gate answers on stdout; the harness wants its own flat shape.
                f"{_translator(answer)}'\n"
            )
        else:
            # A non-deciding lane on a stdout-reading harness must not pollute the
            # decision channel: its output belongs on stderr.
            body = f'exec "$PYTHON_BIN" -B -m {lane.argv} >&2\n'
        wrappers[_wrapper_name(record, lane)] = f"{_PROLOGUE}{exports}{body}"
    return wrappers


def hook_file_payloads(record: HarnessRecord) -> dict[str, str]:
    """Return ``{path relative to the record's directory: serialized JSON}``.

    Every event cites the wrapper of the lane implementing its behaviour — the file is a
    registration, never a second copy of the behaviour.
    """
    dialect = HOOK_DIALECTS[record.hooks]
    lanes = {lane.name: lane for lane in dialect.lanes}
    payloads: dict[str, str] = {}
    for spec in dialect.files:
        hooks: dict[str, object] = {}
        for event, lane_name in spec.events:
            entry: dict[str, str] = {}
            if dialect.typed:
                entry["type"] = "command"
            entry[dialect.entry_key] = hook_wrapper_command(_wrapper_name(record, lanes[lane_name]))
            hooks[event] = [entry]
        document: dict[str, object] = {}
        if dialect.version is not None:
            document["version"] = dialect.version
        document["hooks"] = hooks
        payloads[spec.relpath] = json.dumps(document, indent=2, sort_keys=True) + "\n"
    return payloads
