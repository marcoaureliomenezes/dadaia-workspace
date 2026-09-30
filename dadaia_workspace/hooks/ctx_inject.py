"""Context-injection hook (SessionStart, UserPromptSubmit, PostCompact): transport for
:func:`injection_policy.decide_injection`. Re-injects when the session's ``bound_at`` or
the PostCompact marker is newer than its sentinel (``ctx-inject-fired-<sid>``)."""

from __future__ import annotations

import contextlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import invocation, session_store, workspace_layout
from dadaia_workspace.features.spec_context import injection_policy
from dadaia_workspace.features.workspace import onboarding
from dadaia_workspace.hooks import _common

_DIGEST_FIELDS: tuple[str, ...] = ("slug", "title", "tldr", "path")

_SENTINEL_PREFIX = "ctx-inject-fired-"
_COMPACT_PREFIX = "ctx-compact-"


def _session_bound_at(workspace: Path, session_id: str) -> float | None:
    record = session_store.read_session(workspace, session_id)
    raw = record.get("bound_at") if isinstance(record, dict) else None
    try:
        return datetime.fromisoformat(raw).timestamp() if isinstance(raw, str) else None
    except ValueError:
        return None


def _resolve_context() -> str:
    """The session's bind — never the cwd's repo: an unbound session injects no memory."""
    return invocation.resolve(env=os.environ, cwd=Path.cwd()).bind.context_name or ""


def _emit(payload: str) -> None:
    if os.environ.get("DADAIA_HOOK_OUTPUT", "") in ("codex-json", "json"):
        event = os.environ.get("DADAIA_HOOK_EVENT", "UserPromptSubmit")
        out = {"hookEventName": event, "additionalContext": payload}
        print(json.dumps({"hookSpecificOutput": out}))
    else:
        sys.stdout.write(payload)


def _digest_catalog(raw: str) -> str:
    """The catalog reduced to :data:`_DIGEST_FIELDS`; the raw text when it does not parse."""
    try:
        features = json.loads(raw).get("features")
    except (ValueError, AttributeError):
        return raw
    if not isinstance(features, list):
        return raw
    digested = [
        {k: f[k] for k in _DIGEST_FIELDS if k in f} for f in features if isinstance(f, dict)
    ]
    return json.dumps({"features": digested}, ensure_ascii=False, indent=2)


def _tech_stack_section(raw: str) -> str:
    """``ARCHITECTURE.md``'s ``## Tech Stack`` section to the next ``## ``; ``""`` when absent."""
    lines = raw.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "## Tech Stack"), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end]).strip()


def _build_memory(specs_dir: Path) -> str:
    """The tech-stack section + the catalog digest (else ``index.md``)."""
    memory_dir = specs_dir / "memory"
    if not memory_dir.is_dir():
        return ""
    parts = ["", "=== workspace memory (tech + catalog) ==="]
    architecture = memory_dir / "ARCHITECTURE.md"
    if architecture.is_file():
        with contextlib.suppress(OSError):
            section = _tech_stack_section(architecture.read_text(encoding="utf-8"))
            if section:
                parts.append(section)
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


def _read_sentinel(sentinel: Path) -> tuple[float | None, str]:
    """``(mtime, recorded slug)``; ``(None, "")`` when absent."""
    try:
        mtime = sentinel.stat().st_mtime
    except OSError:
        return None, ""
    text = ""
    with contextlib.suppress(OSError):
        text = sentinel.read_text(encoding="utf-8").strip()
    return mtime, text.removeprefix("ctx=").strip() if text.startswith("ctx=") else ""


def _stamp_sentinel(tmp_dir: Path, sentinel: Path, slug: str) -> None:
    with contextlib.suppress(OSError):
        tmp_dir.mkdir(parents=True, exist_ok=True)
        sentinel.write_text(f"ctx={slug}\n" if slug else "", encoding="utf-8")


def _read_help_digest(workspace: Path) -> str:
    """The CLI help digest install/reconcile built, or ``""`` — the hook never builds it."""
    try:
        return (workspace / ".dadaia" / "agentic" / "help-digest.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def _head(workspace: Path, header: str, focus: str | None, bound: bool | None) -> list[str]:
    """The header and the onboarding next step ``doctor`` reports."""
    trees = invocation.alive_context_trees(workspace)
    step = onboarding.next_step(workspace, trees, focus, bound)
    return [header] if step is None else [header, step.text()]


def _generic_preflight(workspace: Path, session: str | None, lost: str) -> str:
    """The unbound session's payload: next step (rebinding *lost* first) and ALIVE contexts."""
    sections = _head(workspace, "[no bound context]", lost or None, False if session else None)
    if ghost := os.environ.get("DADAIA_CONTEXT"):  # a stale export is surfaced, never obeyed
        sections.append(f"! DADAIA_CONTEXT={ghost} is not this session's bind — ignored")
    if alive := invocation.alive_context_names(workspace):
        sections += ["", "=== ALIVE contexts (bind one to inject its memory) ==="]
        sections += [f"- {name}" for name in alive] + ["=== end ALIVE contexts ==="]
    if digest := _read_help_digest(workspace):
        sections += ["", digest.rstrip("\n")]
    return "\n".join(sections) + "\n"


def _worktrees(workspace: Path, context: str) -> list[str]:
    """The doctor's worktree listing for *context* (AC1.10), each fix under its line."""
    from dadaia_workspace.container import build_doctor_service  # the hook's one composition

    try:
        found = build_doctor_service(workspace).check_worktrees(context)
    except Exception:  # noqa: BLE001 — fail-open: a hook never crashes the session
        return []
    return [
        f"{f.code} {f.verdict} {f.message}" + (f"\n  fix: {f.fix}" if f.fix else "") for f in found
    ]


def _emit_bootstrap(workspace: Path, context: str) -> None:
    sections = _head(workspace, f"[{context}]", context, True)
    specs = invocation.resolve_context_specs_dir(workspace, context)
    if memory := _build_memory(specs) if specs else "":
        sections.append(memory)
    if worktrees := _worktrees(workspace, context):
        sections += ["", "=== open worktrees ===", *worktrees, "=== end worktrees ==="]
    if digest := _read_help_digest(workspace):
        sections.append(digest.rstrip("\n"))
    _emit("\n".join(sections) + "\n")


def main() -> int:
    payload = _common.read_stdin_json()
    try:
        workspace = invocation.resolve(env=os.environ, cwd=Path.cwd()).workspace_root
    except Exception:  # noqa: BLE001 — fail-open: emit nothing rather than crash
        workspace = None
    if workspace is None:
        _emit("")
        return 0
    own = _common.resolve_session_id() or None
    if own:  # the operator's prompt is activity too: renew the liveness clock
        session_store.touch_last_seen_at(workspace, own, now=datetime.now(tz=UTC).isoformat())
    session_id = own or "workspace"
    tmp_dir = workspace / workspace_layout.MARKER_DIR
    sentinel = tmp_dir / f"{_SENTINEL_PREFIX}{session_id}"
    compact_marker = tmp_dir / f"{_COMPACT_PREFIX}{session_id}"
    sentinel_mtime, recorded_slug = _read_sentinel(sentinel)
    event: injection_policy.Event = "prompt"
    if os.environ.get("DADAIA_HOOK_EVENT") == "PostCompact":  # Kimi: stamp, then emit
        event = "postcompact"
        with contextlib.suppress(OSError):
            tmp_dir.mkdir(parents=True, exist_ok=True)
            compact_marker.write_text("", encoding="utf-8")
    elif payload.get("hook_event_name") == "SessionStart" and payload.get("source") in (
        "compact",
        "clear",
    ):
        event = "session_restart"

    def newer(stamp: float | None) -> bool:
        return sentinel_mtime is not None and stamp is not None and stamp > sentinel_mtime

    decision = injection_policy.decide_injection(
        event=event,
        context=_resolve_context(),
        recorded_slug=recorded_slug,
        sentinel_exists=sentinel_mtime is not None,
        compacted=newer(_read_sentinel(compact_marker)[0]),
        rebound=newer(_session_bound_at(workspace, session_id)),
    )
    if decision.emit == "bootstrap":
        _emit_bootstrap(workspace, decision.context)
    elif decision.emit == "preflight":
        _emit(_generic_preflight(workspace, own, decision.context))
    if decision.stamp_slug is not None:
        _stamp_sentinel(tmp_dir, sentinel, decision.stamp_slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
