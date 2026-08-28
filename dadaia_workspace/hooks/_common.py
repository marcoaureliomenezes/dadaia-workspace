"""Shared primitives for the Python governance hooks (Windows-safe).

Every concern that the shell hooks implemented with ad-hoc inline Python (stdin-JSON
parsing, the ``{"decision":"block",...}`` / allow envelope, python-bin resolution,
UTF-8 encoding, session-id sanitization, atomic file renewal) lives here once so the five
hook entrypoints stay thin and the behavior is identical across all of them.

Cross-platform notes:
- All file reads/writes use ``encoding="utf-8"`` explicitly (Windows defaults to the
  locale code page otherwise, corrupting non-ASCII payloads).
- Session ids are stripped to ``[A-Za-z0-9_-]`` before use as a filename component so a
  ``/`` or ``..`` can never escape the temp dir (CWE-22; mirrors the shell strip).
- Atomic renewal uses ``os.replace`` (atomic on POSIX *and* Windows), never ``os.rename``
  (which is not atomic-over-existing on Windows).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.session_env import HARNESS_SESSION_ID_ENV_VARS

#: Write-like tool names intercepted by the PreToolUse gates (Claude / Codex).
WRITE_TOOLS: frozenset[str] = frozenset(
    {
        "Write",
        "write_file",
        "Edit",
        "edit_file",
        "MultiEdit",
        "NotebookEdit",
        "apply_patch",
    }
)

#: Codex ``apply_patch`` file-header prefixes (the touched file follows the prefix).
_PATCH_PREFIXES: tuple[str, ...] = (
    "*** Update File: ",
    "*** Add File: ",
    "*** Delete File: ",
)

_SESSION_ID_STRIP = re.compile(r"[^A-Za-z0-9_-]")


def read_stdin_json() -> dict[str, Any]:
    """Parse the hook JSON envelope from stdin. Returns ``{}`` on any failure (fail-open)."""
    try:
        raw = sys.stdin.read()
    except Exception:  # noqa: BLE001 — fail-open: a stdin read error must never crash a hook
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def tool_name(payload: dict[str, Any]) -> str:
    """Extract the tool name from a hook payload (handles both Claude and Codex keys)."""
    return str(payload.get("tool_name") or payload.get("tool") or "")


def is_write_tool(name: str) -> bool:
    return name in WRITE_TOOLS


def target_paths(payload: dict[str, Any]) -> list[str]:
    """Extract ALL write-target paths from a hook payload.

    Handles direct keys (``file_path``/``path``/``notebook_path`` — always a single
    path) and Codex ``apply_patch`` commands (EVERY ``*** Add/Update/Delete File:``
    header, in source order). Returns ``[]`` when no path can be parsed (caller fails
    open).

    FR-W4-04 (T-014-02): a multi-file ``apply_patch`` must surface every file header so
    the gate can classify each path and let the most-restrictive verdict win (one FROZEN
    or PROTECTED header blocks the whole patch). Closes
    ``sdd-gate-apply-patch-multi-file-first-header-only``.
    """
    inp = payload.get("tool_input")
    src: dict[str, Any] = inp if isinstance(inp, dict) else payload
    direct = src.get("file_path") or src.get("path") or src.get("notebook_path") or ""
    if direct:
        return [str(direct)]
    command = src.get("command") or ""
    paths: list[str] = []
    if isinstance(command, str):
        for line in command.splitlines():
            for prefix in _PATCH_PREFIXES:
                if line.startswith(prefix):
                    paths.append(line[len(prefix) :].strip())
                    break
    return paths


def target_path(payload: dict[str, Any]) -> str:
    """Extract the FIRST write-target path from a hook payload (single-value back-compat).

    Direct keys (``file_path``/``path``/``notebook_path``) or the FIRST Codex
    ``apply_patch`` file header. Returns ``""`` when no path can be parsed (caller fails
    open). Retained for callers not yet migrated to :func:`target_paths`; the multi-file
    bug fix (FR-W4-04) lives in callers switching to :func:`target_paths`.
    """
    paths = target_paths(payload)
    return paths[0] if paths else ""


def sanitize_session_id(raw: str | None) -> str:
    """Strip a session id to ``[A-Za-z0-9_-]`` (CWE-22 path-traversal defense)."""
    return _SESSION_ID_STRIP.sub("", raw or "")


def resolve_session_id(payload: dict[str, Any], *, default: str = "") -> str:
    """Resolve the harness-native session id, sanitized.

    Order (v0.1.50 FR1): explicit ``DADAIA_SESSION_ID`` override (eval-flow contract,
    always first), then the stdin ``session_id`` payload field (the harness's live
    truth for THIS session), then the per-harness env vars (which may be INHERITED
    from a parent shell and stale — the audit F-1 rotated-sid self-block source),
    then ``default``. Shared seam: the gate, the PostToolUse heartbeat, and
    ctx-inject all resolve through here, staying sid-consistent by construction.

    The harness-native env-var list is the single source ``core.session_env.
    HARNESS_SESSION_ID_ENV_VARS`` (v0.1.55 FR4) — the same list the bind CLI and the
    ``core`` bound-context resolver read, so the harness id never drifts across layers.
    """
    candidate = os.environ.get("DADAIA_SESSION_ID") or str(payload.get("session_id") or "")
    if not candidate:
        for name in HARNESS_SESSION_ID_ENV_VARS:
            candidate = os.environ.get(name) or ""
            if candidate:
                break
    sanitized = sanitize_session_id(candidate)
    return sanitized or default


def emit_block(reason: str) -> None:
    """Print the merged block envelope: legacy + documented Claude Code contract.

    Bug claude-pre-gate-envelope-contract: the documented Claude Code PreToolUse verdict
    is ``hookSpecificOutput.permissionDecision: "deny"`` — the top-level
    ``"decision": "block"`` only rides an undocumented legacy fallback there. Both are
    carried in ONE envelope because each has its own consumer:

    - ``decision``/``reason`` — codex hooks and the kimi pre-gate shim. Key placement is
      part of the contract: the shim greps the literal ``"decision": "block"`` and its
      sed reason extraction (``.*"reason": "\\(.*\\)".*``) captures cleanly only while
      the top-level ``reason`` stays the LAST key.
    - ``hookSpecificOutput`` — Claude Code's documented PreToolUse decision control.
    """
    print(
        json.dumps(
            {
                "decision": "block",
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                },
                "reason": reason,
            }
        )
    )


def emit_allow(system_message: str | None = None) -> None:
    """Print the explicit allow envelope (observable AND Claude-Code schema-valid).

    ``system_message`` (bug pre-gate-drops-live-presence-advisory-042) carries the
    NO-LOCKS presence advisory of an allowed MUTATING write: it rides the envelope's
    ``systemMessage`` field (shown to the user, no permission verdict attached) and is
    additionally echoed to stderr so grep-based consumers (kimi shim, codex hooks,
    logs) see it without parsing JSON. Absent → the envelope is byte-identical to the
    pre-advisory shape.

    Bug projected-pre-gate-silent-allow: allow used to be silence + exit 0, so external
    automation could not distinguish an explicit allow from a hook that never ran — the
    envelope must stay non-empty. Bug pre-gate-allow-envelope-fails-claude-schema: it
    must also carry NO permission verdict, because Claude Code's PreToolUse output
    schema rejects everything else this gate could say:

    - top-level ``decision`` enum is ``["approve", "block"]`` — ``"allow"`` fails
      validation of the WHOLE envelope on every allowed call, and ``"approve"`` would
      BYPASS the user's permission prompts;
    - ``permissionDecision: "defer"`` is print-mode only — interactive sessions warn
      and ignore it (and ``"allow"`` there also bypasses prompts).

    So the gate steps aside with only schema-neutral fields. Codex hooks and the kimi
    shim treat any envelope without the literal ``"decision": "block"`` as allow.
    """
    envelope: dict[str, object] = {
        "continue": True,
        "hookSpecificOutput": {"hookEventName": "PreToolUse"},
    }
    if system_message:
        envelope["systemMessage"] = system_message
        print(system_message, file=sys.stderr)
    print(json.dumps(envelope))


def default_python_bin(workspace: Path) -> str:
    """Resolve the workspace venv Python, Windows-safe, with portable fallbacks.

    ``.dadaia/.venv/<scripts>/python<suffix>`` (``Scripts/python.exe`` on Windows,
    ``bin/python`` on POSIX) → ``sys.executable`` → bare ``python``. No bash dependency.
    """
    venv_python = (
        workspace
        / ".dadaia"
        / ".venv"
        / PLATFORM.venv_scripts_dir
        / f"python{PLATFORM.venv_exe_suffix}"
    )
    if venv_python.is_file():
        return str(venv_python)
    if sys.executable:
        return sys.executable
    return "python"
