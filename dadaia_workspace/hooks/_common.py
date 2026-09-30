"""Shared primitives of the Python governance hooks: stdin JSON, payload normalization,
write-target extraction, session id and the block/allow envelopes. Every file read or
write passes ``encoding="utf-8"`` (Windows defaults to the locale code page)."""

from __future__ import annotations

import contextlib
import json
import os
import sys
from typing import Any

from dadaia_workspace.core import invocation

WRITE_TOOLS = frozenset({"Write", "write_file", "Edit", "edit_file", "MultiEdit", "NotebookEdit"})
WRITE_TOOLS |= {"apply_patch"}
_PATCH_PREFIXES = ("*** Update File: ", "*** Add File: ", "*** Delete File: ")


def read_stdin_json() -> dict[str, Any]:
    """The hook JSON envelope from stdin; ``{}`` on any failure (fail-open)."""
    try:
        data = json.loads(sys.stdin.read())
    except Exception:  # noqa: BLE001 — fail-open: a stdin read error must never crash a hook
        return {}
    return data if isinstance(data, dict) else {}


#: Native tool names (lower-cased) -> the Claude name every policy reads.
_TOOL_ALIASES = {"bash": "Bash", "exec": "Bash", "shell": "Bash", "edit": "Edit"}
_TOOL_ALIASES |= {"write": "Write", "create": "Write"}


def claude_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Every harness's pre-tool payload in Claude form, before any policy runs."""
    name = payload.get("tool_name") or payload.get("toolName") or payload.get("tool")
    args: Any = payload.get("toolArgs")
    with contextlib.suppress(ValueError, TypeError):
        args = json.loads(args)  # Copilot sends toolArgs as a JSON string
    name = str(name or ("Bash" if "command" in payload else ""))
    tool_input = payload.get("tool_input") or args
    tool_input = tool_input if isinstance(tool_input, dict) else payload
    return {**payload, "tool_name": _TOOL_ALIASES.get(name.lower(), name), "tool_input": tool_input}


def is_write_tool(name: str) -> bool:
    return name in WRITE_TOOLS


def target_paths(payload: dict[str, Any]) -> list[str]:
    """Every write target: the direct path key, else EVERY ``apply_patch`` file header in
    order (the gate judges each); ``[]`` when none parses."""
    inp = payload.get("tool_input")
    src: dict[str, Any] = inp if isinstance(inp, dict) else payload
    direct = src.get("file_path") or src.get("path") or src.get("notebook_path") or ""
    if direct:
        return [str(direct)]
    command = src.get("command") or ""
    lines = command.splitlines() if isinstance(command, str) else []
    return [line.split(": ", 1)[1].strip() for line in lines if line.startswith(_PATCH_PREFIXES)]


def target_path(payload: dict[str, Any]) -> str:
    """The first of :func:`target_paths`, or ``""``."""
    return next(iter(target_paths(payload)), "")


def resolve_session_id() -> str:
    """The sanitized session id by the one rule (:func:`invocation.resolve_session_id`)."""
    return invocation.resolve_session_id(os.environ)


def emit_block(reason: str) -> None:
    """The block envelope: Claude Code's ``permissionDecision: "deny"`` plus the top-level
    ``decision``/``reason`` the codex hooks and kimi shim grep — ``reason`` stays the LAST
    key, the shim's sed extraction depends on it."""
    deny = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
    print(json.dumps({"decision": "block", "hookSpecificOutput": deny, "reason": reason}))


def emit_allow() -> None:
    """The explicit, non-empty allow envelope with NO permission verdict: Claude Code's schema
    rejects ``decision: "allow"``, and ``approve``/``allow`` verdicts bypass the user's prompts."""
    print(json.dumps({"continue": True, "hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
