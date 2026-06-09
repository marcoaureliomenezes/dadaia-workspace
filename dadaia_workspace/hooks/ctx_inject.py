"""Context-injection hook (Windows-safe port of ``ctx-inject.sh``).

Invoked on SessionStart and UserPromptSubmit. It injects, ONCE per logical session, the
lean workspace bootstrap (context line + dispatcher preflight + tech-stack.md + catalog).
A session-keyed sentinel guards the ENTIRE injection so subsequent prompts emit nothing.

Parity invariants preserved verbatim from the rc-4 shell hook:

- **Once-per-session sentinel**, keyed on the harness-native session id, sentinel path
  BYTE-IDENTICAL to the shell sentinel ``.dadaia/tmp/ctx-inject-fired-<sessionId>``.
- **Session id resolution**: ``DADAIA_SESSION_ID`` → ``CLAUDE_CODE_SESSION_ID`` →
  ``CODEX_SESSION_ID`` → ``OPENCODE_SESSION_ID`` → stdin ``session_id`` → ``"workspace"``,
  sanitized to ``[A-Za-z0-9_-]``.
- **Output contract**: ``DADAIA_HOOK_OUTPUT`` in {``codex-json``, ``json``} emits the
  ``hookSpecificOutput.additionalContext`` envelope with ``hookEventName`` from
  ``DADAIA_HOOK_EVENT`` (default ``UserPromptSubmit``); otherwise raw payload to stdout.
- **Auto-context**: ``DADAIA_CONTEXT`` override, else first-ALIVE context in the registry;
  no nag, no halt — emits an (empty) payload and exits when nothing is resolvable.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

from dadaia_workspace.hooks import _common

_DISPATCHER_PREFLIGHT = """=== dispatcher preflight (SDD routing) ===
Before acting on a request in this workspace:
1. Resolve the active context (above) and the OWNING role for the
   artifact class you are about to touch: backlog -> project-manager;
   SPEC/PLAN/TASKS -> product-engineer; hooks/agents/skills/rules/
   workflows (the AI surface) -> ai-engineer audit; production code ->
   software-engineer; reviews -> code/security/qa reviewers.
2. Ownership is a COORDINATION CONVENTION, not a gate. No workflow
   (research, backlog/release definition, implementation+review,
   audits) is ever lock-blocked, and project-manager always spawns
   and writes freely. Route changes through the owning role by
   discipline. The ONLY deterministic lock is the single-session
   lease (one bound session per Spec Context for release-definition
   / implementation+review).
3. If the operator asks for multi-agent / deep / AI-surface work and a
   subagent or dispatch tool is not in your active tool set, DISCOVER it
   first (e.g. tool_search for the agent/dispatch tool) BEFORE starting
   the main task -- do not silently proceed as a generic single agent.
4. Limitation (truthful): this harness does NOT auto-spawn subagents
   from static .codex/.claude workflow files. Workflow files are
   reference docs; explicit dispatcher/operator fan-out is required.
=== end dispatcher preflight ==="""


def _resolve_workspace() -> Path:
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def _resolve_context(workspace: Path) -> str:
    """``DADAIA_CONTEXT`` override, else first-ALIVE context's slug from the registry."""
    env = os.environ.get("DADAIA_CONTEXT")
    if env:
        return env
    registry = workspace / ".dadaia" / "states" / "spec_contexts.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return ""
    for c in data.get("contexts", []):
        if str(c.get("state", "")).lower() == "alive":
            return str(c.get("repo_slug") or c.get("name") or "")
    return ""


def _emit(payload: str) -> None:
    """Emit the payload per ``DADAIA_HOOK_OUTPUT`` (codex-json/json envelope or raw)."""
    output = os.environ.get("DADAIA_HOOK_OUTPUT", "")
    if output in ("codex-json", "json"):
        event = os.environ.get("DADAIA_HOOK_EVENT", "UserPromptSubmit")
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": payload,
                    }
                }
            )
        )
    else:
        sys.stdout.write(payload)


def _write_runtime_ptr(workspace: Path, session_id: str) -> None:
    """Best-effort session-keyed runtime pointer (mirrors the shell ``.ptr`` write)."""
    if session_id == "workspace":
        return
    ptr_dir = workspace / ".dadaia" / "sessions" / "runtime"
    try:
        ptr_dir.mkdir(parents=True, exist_ok=True)
        (ptr_dir / f"{session_id}.ptr").write_text(session_id, encoding="utf-8")
    except OSError:
        return


def _build_memory(specs_dir: Path) -> str:
    """Build the once-per-session memory bootstrap (tech-stack + catalog/index)."""
    memory_dir = specs_dir / "memory"
    if not memory_dir.is_dir():
        return ""
    parts = ["", "=== workspace memory (tech + catalog) ==="]
    tech = memory_dir / "tech-stack.md"
    if tech.is_file():
        with contextlib.suppress(OSError):
            parts.append(tech.read_text(encoding="utf-8"))
    catalog = memory_dir / "product" / "catalog.json"
    index = memory_dir / "product" / "index.md"
    chosen = catalog if catalog.is_file() else (index if index.is_file() else None)
    if chosen is not None:
        with contextlib.suppress(OSError):
            parts.append(chosen.read_text(encoding="utf-8"))
    parts.append("=== end memory bootstrap ===")
    return "\n".join(parts)


def main() -> int:
    """Run the context-injection hook. Returns 0 always."""
    payload = _common.read_stdin_json()
    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open: emit nothing rather than crash
        _emit("")
        return 0

    session_id = _common.resolve_session_id(payload, default="workspace")
    _write_runtime_ptr(workspace, session_id)

    context = _resolve_context(workspace)
    if not context:
        _emit("")
        return 0
    specs_dir = workspace / "repos" / context / "specs"
    if not specs_dir.is_dir():
        _emit("")
        return 0

    # Once-per-session sentinel — guards the ENTIRE injection. Path is BYTE-IDENTICAL
    # to the shell sentinel: .dadaia/tmp/ctx-inject-fired-<sessionId>.
    tmp_dir = workspace / ".dadaia" / "tmp"
    sentinel = tmp_dir / f"ctx-inject-fired-{session_id}"
    if sentinel.exists():
        return 0
    try:
        tmp_dir.mkdir(parents=True, exist_ok=True)
        sentinel.touch()
    except OSError:
        # Cannot mark the sentinel — still emit once (better than crashing).
        pass

    sections = [f"[{context}]", "", _DISPATCHER_PREFLIGHT]
    memory = _build_memory(specs_dir)
    if memory:
        sections.append(memory)
    _emit("\n".join(sections) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
