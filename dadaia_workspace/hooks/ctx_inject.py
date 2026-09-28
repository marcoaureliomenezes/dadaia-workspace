"""Context-injection hook (SessionStart, UserPromptSubmit, PostCompact).

Transport only: resolves the inputs, asks :func:`injection_policy.decide_injection`,
executes the decision. The bind (``core.invocation``) names the context; the one
re-injection predicate is "newer than this session's sentinel"
(``.dadaia/tmp/ctx-inject-fired-<sid>``, content ``ctx=<slug>``) — for the session's
own ``bound_at`` (a re-bind, same context included) and for the PostCompact marker
(``ctx-compact-<sid>``). ``DADAIA_HOOK_OUTPUT`` in {codex-json, json} wraps the payload
in ``hookSpecificOutput.additionalContext`` (event from ``DADAIA_HOOK_EVENT``)."""

from __future__ import annotations

import contextlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dadaia_workspace.core import invocation, session_store, workspace_layout
from dadaia_workspace.features.spec_context import injection_policy
from dadaia_workspace.features.workspace import onboarding
from dadaia_workspace.hooks import _common

#: The injected catalog fields: ``summary`` is self-pulled; ``rank`` is file order, not
#: priority (F-77).
_DIGEST_FIELDS: tuple[str, ...] = ("slug", "title", "tldr", "path")

_SENTINEL_PREFIX = "ctx-inject-fired-"
_COMPACT_PREFIX = "ctx-compact-"


def _session_bound_at(workspace: Path, session_id: str) -> float | None:
    """This session's own record ``bound_at`` (written by every bind) as epoch
    seconds, else ``None`` — fail-soft, never a trigger."""
    record = session_store.read_session(workspace, session_id)
    if not isinstance(record, dict):
        return None
    raw = record.get("bound_at")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return None


def _resolve_context(payload: dict[str, object]) -> str:
    """The session's bind (:func:`dadaia_workspace.core.invocation.resolve_bind`) — never
    the repo the cwd sits in: an unbound session injects no context memory."""
    return (
        invocation.resolve(payload=payload, env=os.environ, cwd=Path.cwd()).bind.context_name or ""
    )


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
    """The catalog reduced to :data:`_DIGEST_FIELDS` per feature; the raw text when
    it does not parse (fail-open)."""
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


_TECH_STACK_HEADING = "## Tech Stack"


def _tech_stack_section(raw: str) -> str:
    """``ARCHITECTURE.md``'s ``## Tech Stack`` section, whole, to the next ``## ``;
    ``""`` when absent."""
    lines = raw.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == _TECH_STACK_HEADING)
    except StopIteration:
        return ""
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start:end]).strip()


def _build_memory(specs_dir: Path) -> str:
    """The lean bootstrap: the tech-stack section + the catalog digest (else
    ``index.md``); deeper atoms are self-pulled (``dd-spec-navigator``)."""
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


_SENTINEL_SLUG_PREFIX = "ctx="


def _read_sentinel(sentinel: Path) -> tuple[float | None, str]:
    """``(mtime, recorded slug)``; ``(None, "")`` when absent (fail-soft)."""
    try:
        mtime = sentinel.stat().st_mtime
    except OSError:
        return None, ""
    slug = ""
    with contextlib.suppress(OSError):
        text = sentinel.read_text(encoding="utf-8").strip()
        if text.startswith(_SENTINEL_SLUG_PREFIX):
            slug = text[len(_SENTINEL_SLUG_PREFIX) :].strip()
    return mtime, slug


def _stamp_sentinel(tmp_dir: Path, sentinel: Path, slug: str) -> None:
    """Stamp the sentinel content with the injected slug (or empty for generic). Fail-soft."""
    with contextlib.suppress(OSError):
        tmp_dir.mkdir(parents=True, exist_ok=True)
        sentinel.write_text(
            f"{_SENTINEL_SLUG_PREFIX}{slug}\n" if slug else "",
            encoding="utf-8",
        )


def _read_help_digest(workspace: Path) -> str:
    """The derived CLI help digest, or ``""`` (fail-soft). Built by install/reconcile
    (`dadaia help tree --digest`) — NEVER here: the hook only reads the file."""
    try:
        return (workspace / ".dadaia" / "agentic" / "help-digest.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def _head(workspace: Path, header: str, focus: str | None, bound: bool | None) -> list[str]:
    """The ONE onboarding call site of SessionStart, bound or not: the header and the
    derived next step — the text ``doctor`` reports."""
    trees = invocation.alive_context_trees(workspace)
    step = onboarding.next_step(workspace, trees, focus, bound)
    return [header] if step is None else [header, step.text()]


def _generic_preflight(workspace: Path, session: str | None = None) -> str:
    """Generic preflight payload for an unbound session: ``[no bound context]``, the
    next step and the ALIVE-context list. NEVER any context memory (FR-W2-01)."""
    sections = _head(workspace, "[no bound context]", None, False if session else None)
    if ghost := os.environ.get("DADAIA_CONTEXT"):  # a stale export is surfaced, never obeyed
        sections.append(f"! DADAIA_CONTEXT={ghost} is not this session's bind — ignored")
    alive = invocation.alive_context_names(workspace)
    if alive:
        sections.append("")
        sections.append("=== ALIVE contexts (bind one to inject its memory) ===")
        sections.extend(f"- {name}" for name in alive)
        sections.append("=== end ALIVE contexts ===")
    digest = _read_help_digest(workspace)
    if digest:
        sections.append("")
        sections.append(digest.rstrip("\n"))
    return "\n".join(sections) + "\n"


def _emit_bootstrap(workspace: Path, context: str) -> None:
    """Emit the bound context's bootstrap: the header and next step (:func:`_head`) + the
    lean memory prefix."""
    sections = _head(workspace, f"[{context}]", context, True)
    specs = invocation.resolve_context_specs_dir(workspace, context)
    memory = _build_memory(specs) if specs else ""
    if memory:
        sections.append(memory)
    digest = _read_help_digest(workspace)
    if digest:
        sections.append(digest.rstrip("\n"))
    _emit("\n".join(sections) + "\n")


def main() -> int:
    """Run the context-injection hook. Transport only (F009): resolve the inputs,
    call :func:`injection_policy.decide_injection`, execute the decision. Returns 0
    always."""
    payload = _common.read_stdin_json()
    try:
        workspace = invocation.resolve(
            payload=payload, env=os.environ, cwd=Path.cwd()
        ).workspace_root
        if workspace is None:
            raise RuntimeError("workspace not resolved")
    except Exception:  # noqa: BLE001 — fail-open: emit nothing rather than crash
        _emit("")
        return 0

    session_id = _common.resolve_session_id(payload, default="workspace")

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
    ):  # Claude Code re-entry (bug claude-compact-reinjection-missing)
        event = "session_restart"

    def newer(stamp: float | None) -> bool:
        """The one re-injection predicate: *stamp* is newer than the sentinel."""
        return sentinel_mtime is not None and stamp is not None and stamp > sentinel_mtime

    compact_mtime = _read_sentinel(compact_marker)[0]
    decision = injection_policy.decide_injection(
        event=event,
        context=_resolve_context(payload),
        recorded_slug=recorded_slug,
        sentinel_exists=sentinel_mtime is not None,
        compacted=newer(compact_mtime),
        rebound=newer(_session_bound_at(workspace, session_id)),
    )

    own = _common.resolve_session_id(payload) or None
    if decision.emit == "bootstrap":
        _emit_bootstrap(workspace, decision.context)
    elif decision.emit == "preflight":
        _emit(_generic_preflight(workspace, own))
    if decision.stamp_slug is not None:
        _stamp_sentinel(tmp_dir, sentinel, decision.stamp_slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
