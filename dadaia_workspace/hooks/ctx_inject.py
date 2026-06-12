"""Context-injection hook (the canonical, cross-platform gate surface).

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
import time
from pathlib import Path

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.hooks import _common

#: Lean fields kept in the INJECTED catalog digest. The heavy ``summary`` is dropped from
#: the injection (catalog.json on disk is untouched — self-pull depth intact). Keeping
#: rank/slug/title/tldr/path is enough for the once-per-session first-pass scan; an agent
#: that needs depth self-pulls the full atom (Step 0 memory bootstrap).
_DIGEST_FIELDS: tuple[str, ...] = ("rank", "slug", "title", "tldr", "path")

#: Filename prefix of the once-per-session sentinel (``ctx-inject-fired-<sessionId>``).
_SENTINEL_PREFIX = "ctx-inject-fired-"

#: Age (seconds) after which a once-per-session sentinel is considered stale and GC'd at
#: inject time. Generous (24 h) so a long-running live session is never disturbed; a
#: session older than this would at worst re-inject the bootstrap once. The sweep home is
#: pinned HERE (inject time), not in ``spec_context/doctor.py`` — avoids the doctor
#: write-set overlap (T-011-14 write set: the doctor leg is conditional and unused).
#: DP-1 (v0.1.14): the value is sourced from ``core.kernel_tunables`` (single tunables home).
_SENTINEL_GC_TTL_SECONDS = kernel_tunables.SENTINEL_GC_TTL_SECONDS

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


def _digest_catalog(raw: str) -> str:
    """Return a tldr-digest of ``catalog.json`` text: drop ``summary``, keep lean fields.

    Each feature is reduced to :data:`_DIGEST_FIELDS` (rank/slug/title/tldr/path). The
    catalog FILE is never modified — this operates on the read-in text and returns the
    smaller string to INJECT. On any parse failure the raw text is returned verbatim
    (fail-open: a malformed catalog must not break the bootstrap).
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw
    if not isinstance(data, dict):
        return raw
    features = data.get("features")
    if not isinstance(features, list):
        return raw
    digested = [
        {k: feat[k] for k in _DIGEST_FIELDS if k in feat}
        for feat in features
        if isinstance(feat, dict)
    ]
    return json.dumps({"features": digested}, ensure_ascii=False, indent=2)


def _build_memory(specs_dir: Path) -> str:
    """Build the once-per-session memory bootstrap (tech-stack + catalog-digest/index)."""
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
    if catalog.is_file():
        with contextlib.suppress(OSError):
            parts.append(_digest_catalog(catalog.read_text(encoding="utf-8")))
    elif index.is_file():
        with contextlib.suppress(OSError):
            parts.append(index.read_text(encoding="utf-8"))
    parts.append("=== end memory bootstrap ===")
    return "\n".join(parts)


def _gc_stale_sentinels(tmp_dir: Path, *, now: float | None = None) -> None:
    """Sweep aged once-per-session sentinel files at inject time (fail-open).

    A sentinel (``ctx-inject-fired-*``) whose mtime is older than
    :data:`_SENTINEL_GC_TTL_SECONDS` is removed; fresh sentinels (other live sessions) and
    non-sentinel tmp files are left untouched. Any OS error during the scan is suppressed —
    GC is best-effort housekeeping and must never break the bootstrap.
    """
    cutoff = (now if now is not None else time.time()) - _SENTINEL_GC_TTL_SECONDS
    try:
        entries = list(tmp_dir.iterdir())
    except OSError:
        return
    for entry in entries:
        if not entry.name.startswith(_SENTINEL_PREFIX):
            continue
        with contextlib.suppress(OSError):
            if entry.is_file() and entry.stat().st_mtime < cutoff:
                entry.unlink()


def main() -> int:
    """Run the context-injection hook. Returns 0 always."""
    payload = _common.read_stdin_json()
    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open: emit nothing rather than crash
        _emit("")
        return 0

    session_id = _common.resolve_session_id(payload, default="workspace")

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
    sentinel = tmp_dir / f"{_SENTINEL_PREFIX}{session_id}"
    # Inject-time GC of stale sentinels (dead/aged sessions). Runs before the once-per-
    # session short-circuit so leftover sentinels are reaped on every fire, not only on
    # the first prompt of a session.
    _gc_stale_sentinels(tmp_dir)
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
