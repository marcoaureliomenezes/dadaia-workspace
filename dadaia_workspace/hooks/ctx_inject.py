"""Context-injection hook (the canonical, cross-platform gate surface).

Invoked on SessionStart and UserPromptSubmit. It injects the lean workspace bootstrap
(context line + TECHSTACK.md + catalog — FR30, T-044-60: the four-point dispatcher
preflight restatement of ``DADAIA.md`` §1/§2 is deleted; it is law, not state). A
session-keyed sentinel
guards re-injection: subsequent prompts emit nothing UNLESS this session's own bind is
newer than the sentinel (T-50-03, SPEC v0.5.0 FR1 coupling 1) — bind is the SOLE trigger
for context-memory injection.

Bind-driven injection state machine (FR-W2-01 / FR-W2-02, v0.1.14; bound_at trigger,
T-50-03)
-----------------------------------------------------------------------------------
Context NAME resolution (``_resolve_context``) delegates to the single resolution
authority (``DADAIA.md`` §3, :func:`dadaia_workspace.container.resolve_context`): this
session's own self-keyed session record → ``DADAIA_CONTEXT`` env → this session's own
live harness-native record → the repo containing the cwd → ``""``. There is no
first-ALIVE fallback and — since T-50-03 — the bind-epoch marker subsystem is no longer
consulted here: a session bound ONLY via a bind-epoch marker (no harness id, no
``DADAIA_CONTEXT``) no longer resolves a context — the accepted FR1 coupling. T-50-04
deletes the marker subsystem's attribution algorithm (``_newest_qualifying_marker``) and
its harness-pid resolver (``_resolve_harness_pid``) outright — both had been uncalled
from the injection path since T-50-03.

The INJECTION TRIGGER (separate from name resolution, :func:`_session_bound_at`) is this
session's own session record ``bound_at`` timestamp compared against the sentinel's mtime —
not the resolved context name and not a bind-epoch marker's mtime. Re-injection rules:

- **No sentinel for this sid** → whatever context resolves (if any) is injected
  immediately and the sentinel is stamped — a session already bound before its first
  prompt gets its context on that very first prompt.
- **A LATER ``dadaia context bind`` than the sentinel** (this session's own record's
  ``bound_at`` newer than the sentinel's mtime) → re-inject and restamp the sentinel,
  even when the resolved context NAME is unchanged (**new pin, T-50-03**: a same-context
  re-bind now re-injects — a re-bind is how a mode/release change reaches a live
  session). A rebind to a DIFFERENT context also re-injects (the resolved name differs
  from the sentinel's recorded slug, independent of ``bound_at``).
- **Repeat prompt** (sentinel exists, no newer own-record ``bound_at``, same resolved
  name) → silent.

Parity invariants preserved verbatim from the rc-4 shell hook:

- **Sentinel** keyed on the harness-native session id, path BYTE-IDENTICAL to the shell
  sentinel ``.dadaia/tmp/ctx-inject-fired-<sessionId>``. Its CONTENT now carries the last
  injected slug (or an empty marker for the generic-preflight case) so a re-bind is
  detectable; an empty file remains a valid "already fired generic" sentinel.
- **Session id resolution**: ``DADAIA_SESSION_ID`` → ``CLAUDE_CODE_SESSION_ID`` →
  ``CODEX_SESSION_ID`` → stdin ``session_id`` → ``"workspace"``,
  sanitized to ``[A-Za-z0-9_-]``.
- **Output contract**: ``DADAIA_HOOK_OUTPUT`` in {``codex-json``, ``json``} emits the
  ``hookSpecificOutput.additionalContext`` envelope with ``hookEventName`` from
  ``DADAIA_HOOK_EVENT`` (default ``UserPromptSubmit``); otherwise raw payload to stdout.
- **Compact epoch (v0.2.8, kimi-code)**: with ``DADAIA_HOOK_EVENT=PostCompact`` the hook
  stamps ``.dadaia/tmp/ctx-compact-<sessionId>`` AND re-emits the bootstrap on stdout
  (observable contract; Kimi discards PostCompact stdout). The repeat-prompt guards
  treat a compact marker NEWER than the sentinel as a re-injection trigger, so the next
  ``UserPromptSubmit`` after a ``/compact`` re-injects the bootstrap exactly once
  (the sentinel restamp makes subsequent prompts silent again). Harnesses that never wire
  a PostCompact hook see byte-identical behavior — no marker, no trigger. This
  compaction-recovery mechanism (and the ``recorded_slug`` sentinel fallbacks) is
  untouched by T-50-03: the PostCompact / SessionStart(compact|clear) event blocks
  resolve context and emit UNCONDITIONALLY on every fire, independent of ``bound_at``.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.features.spec_context import session_identity
from dadaia_workspace.hooks import _common

#: Lean fields kept in the INJECTED catalog digest. The heavy ``summary`` is dropped from
#: the injection (catalog.json on disk is untouched — self-pull depth intact). Keeping
#: slug/title/tldr/path is enough for the once-per-session first-pass scan; an agent
#: that needs depth self-pulls the full atom (Step 0 memory bootstrap). ``rank`` is
#: deliberately NOT injected (F-77): in catalog.json it is the 1-based alphabetical
#: file order — a stable enumeration aid, not a priority signal — so injecting it
#: would only invite agents to misread file order as importance.
_DIGEST_FIELDS: tuple[str, ...] = ("slug", "title", "tldr", "path")

#: Filename prefix of the once-per-session sentinel (``ctx-inject-fired-<sessionId>``).
_SENTINEL_PREFIX = "ctx-inject-fired-"

#: Filename prefix of the per-session compact-epoch marker (``ctx-compact-<sessionId>``),
#: stamped by the PostCompact hook event (v0.2.8, kimi-code) and consumed by the
#: repeat-prompt guards as a re-injection trigger (mtime > sentinel mtime).
_COMPACT_PREFIX = "ctx-compact-"

#: Age (seconds) after which a once-per-session sentinel is considered stale and GC'd at
#: inject time. Generous (24 h) so a long-running live session is never disturbed; a
#: session older than this would at worst re-inject the bootstrap once. The sweep home is
#: pinned HERE (inject time), not in ``spec_context/doctor.py`` — avoids the doctor
#: write-set overlap (T-011-14 write set: the doctor leg is conditional and unused).
#: DP-1 (v0.1.14): the value is sourced from ``core.kernel_tunables`` (single tunables home).
_SENTINEL_GC_TTL_SECONDS = kernel_tunables.SENTINEL_GC_TTL_SECONDS


def _resolve_workspace() -> Path:
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def _alive_context_names(workspace: Path) -> list[str]:
    """Return the slugs of every ALIVE context in the registry (empty on any error)."""
    registry = workspace / ".dadaia" / "states" / "spec_contexts.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    names: list[str] = []
    for c in data.get("contexts", []):
        if str(c.get("state", "")).lower() == "alive":
            slug = str(c.get("repo_slug") or c.get("name") or "")
            if slug:
                names.append(slug)
    return names


def _session_bound_context(workspace: Path, session_id: str) -> str:
    """The context this session is bound to via its self-keyed session record, else ``""``.

    The bind CLI mints its own sid, so in the default flow a harness session's record is
    structurally absent — this leg fires only when the harness sid itself carries a bound
    record (e.g. an operator who exported ``DADAIA_SESSION_ID`` to match the bind sid).
    """
    record = session_identity.read_session(workspace, session_id)
    if not isinstance(record, dict):
        return ""
    return str(record.get("context") or "")


def _session_bound_at(workspace: Path, session_id: str) -> float | None:
    """This session's own record ``bound_at``, as an epoch float, else ``None``.

    T-50-03 (SPEC v0.5.0 FR1 coupling 1) — the INJECTION TRIGGER's source of truth. The
    session record's ``bound_at`` field is written by ``dadaia context bind``
    (``cli/commands/context.py``) on EVERY successful bind — including a same-context
    re-bind, which refreshes it — replacing the bind-epoch marker mtime the trigger used
    to compare. Fail-soft: an absent record, a missing/non-string/malformed ``bound_at``,
    or any parse error yields ``None`` (never a trigger — the caller degrades to "no
    rebind observed", never a crash).
    """
    record = session_identity.read_session(workspace, session_id)
    if not isinstance(record, dict):
        return None
    raw = record.get("bound_at")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return None


def _resolve_context(workspace: Path, session_id: str) -> str:
    """Resolve the context to inject, in the ``DADAIA.md`` §3 law order (F-03).

    Rung 1 ``DADAIA_CONTEXT`` first — every consumer agrees with the gate on the same
    prompt. Rung 2 is the session binding, read through TWO channels of the same record
    store: this hook's own payload/``DADAIA_SESSION_ID``-keyed record
    (:func:`_session_bound_context`), then the authority
    (:func:`dadaia_workspace.core.specs_resolver.resolve_context` — hooks are sanctioned
    DIRECT importers per the seam contract; the container is never imported on a hook
    path, F-01) which re-reads rung 2 via the harness-native env id and adds rung 3, the
    repo containing the current working directory. The bind-epoch marker subsystem
    (deleted, T-50-04) is NOT consulted — a session bound ONLY via a marker (no harness
    id, no ``DADAIA_CONTEXT``) no longer resolves a context.
    """
    # Law order (F-03, v0.5.0 code review): rung 1 `DADAIA_CONTEXT` beats rung 2 (any
    # session binding) — every consumer must agree with the gate on this or the same
    # prompt is attributed to one context and injected with another.
    env_context = os.environ.get("DADAIA_CONTEXT")
    if env_context:
        return env_context

    # Rung 2, payload-sid channel: the hook payload's session id can key a record the
    # env-derived harness id cannot (the bind CLI writes both under the same id in the
    # normal flow; this read is that same "own session binding", not a fourth rung).
    bound = _session_bound_context(workspace, session_id)
    if bound:
        return bound

    # Direct core import (F-01): never pay the container's import graph in a hook.
    from dadaia_workspace.core.specs_resolver import resolve_context

    return resolve_context() or ""


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

    Each feature is reduced to :data:`_DIGEST_FIELDS` (slug/title/tldr/path — ``rank``
    is excluded: it is alphabetical file order, not priority). The catalog FILE is
    never modified — this operates on the read-in text and returns the smaller string
    to INJECT. On any parse failure the raw text is returned verbatim (fail-open: a
    malformed catalog must not break the bootstrap).
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


#: Max non-empty lines of ``TECHSTACK.md`` kept in the bind-time SESSION bootstrap digest.
#: WS-C dehydration (v0.1.30 / T-30-E-05): the bootstrap is a lean session-orientation aid
#: for an interactive agent session, so the hook does not dump the FULL tech-stack body —
#: it emits a bounded digest plus a self-pull pointer. A small tech-stack file (≤ the cap)
#: is emitted in full; a large one is reduced.
_TECH_STACK_DIGEST_MAX_LINES = 24


def _digest_tech_stack(raw: str) -> str:
    """Return a bounded digest of ``TECHSTACK.md`` for the lean session bootstrap.

    Keeps the leading non-empty lines, capped at :data:`_TECH_STACK_DIGEST_MAX_LINES`. When
    the file is already within the cap it is returned verbatim (so a small atom is unchanged).
    A truncated digest appends a self-pull pointer: the full atom stays on disk for the agent
    to read directly when it needs more detail. Fail-open is implicit — the caller suppresses
    OSError around the read.
    """
    lines = raw.splitlines()
    non_empty_total = sum(1 for ln in lines if ln.strip())
    if non_empty_total <= _TECH_STACK_DIGEST_MAX_LINES:
        return raw.strip()
    kept: list[str] = []
    seen = 0
    for ln in lines:
        kept.append(ln)
        if ln.strip():
            seen += 1
        if seen >= _TECH_STACK_DIGEST_MAX_LINES:
            break
    return (
        "\n".join(kept).strip()
        + "\n\n… (tech-stack digest — self-pull specs/memory/TECHSTACK.md for full detail)"
    )


def _build_memory(specs_dir: Path) -> str:
    """Build the once-per-session LEAN memory bootstrap (tech-stack digest + catalog digest).

    WS-C (v0.1.30 / T-30-E-05): this is a session-orientation bootstrap for an interactive
    agent session — a lightweight orientation aid, not the full memory tree. The agent
    self-pulls deeper atoms (e.g. ``ARCHITECTURE.md``, a specific product atom) directly when
    a decision needs them, per the ``dadaia-step0-memory-bootstrap`` skill. So the bootstrap
    stays lean — a bounded tech-stack digest + the lean catalog tldr-digest, never the full
    memory tree.
    """
    memory_dir = specs_dir / "memory"
    if not memory_dir.is_dir():
        return ""
    parts = ["", "=== workspace memory (tech + catalog) ==="]
    tech = memory_dir / "TECHSTACK.md"
    if tech.is_file():
        with contextlib.suppress(OSError):
            parts.append(_digest_tech_stack(tech.read_text(encoding="utf-8")))
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
    """Sweep aged once-per-session sentinel/marker files at inject time (fail-open).

    A sentinel (``ctx-inject-fired-*``) or compact marker (``ctx-compact-*``) whose mtime
    is older than :data:`_SENTINEL_GC_TTL_SECONDS` is removed; fresh files (other live
    sessions) and unrelated tmp files are left untouched. Any OS error during the scan is
    suppressed — GC is best-effort housekeeping and must never break the bootstrap.
    """
    cutoff = (now if now is not None else time.time()) - _SENTINEL_GC_TTL_SECONDS
    try:
        entries = list(tmp_dir.iterdir())
    except OSError:
        return
    for entry in entries:
        if not entry.name.startswith((_SENTINEL_PREFIX, _COMPACT_PREFIX)):
            continue
        with contextlib.suppress(OSError):
            if entry.is_file() and entry.stat().st_mtime < cutoff:
                entry.unlink()


#: Sentinel-content prefix recording the last injected context slug. A sentinel whose
#: content is ``ctx=<slug>`` already injected that slug's memory; an empty/legacy sentinel
#: (no prefix) is treated as the generic-preflight state (no slug injected yet).
_SENTINEL_SLUG_PREFIX = "ctx="


def _read_sentinel(sentinel: Path) -> tuple[float | None, str]:
    """Return ``(mtime, recorded_slug)`` for the sentinel, or ``(None, "")`` if absent.

    The recorded slug is parsed from the ``ctx=<slug>`` content line; an empty or legacy
    sentinel yields ``""`` (generic-preflight state). Fail-soft on any OS error.
    """
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


def _generic_preflight(workspace: Path) -> str:
    """Generic preflight payload: ``[no bound context]`` + the ALIVE-context list.

    Emitted for an unbound session — NEVER any context memory (FR-W2-01). The ALIVE list is
    advisory (names from the registry) so the operator can bind one — it stays because it is
    useful only in this unbound case (FR30, T-044-60: the dispatcher preflight restatement of
    ``DADAIA.md`` §1/§2 is deleted from every emission path, bound or not).
    """
    sections = ["[no bound context]"]
    alive = _alive_context_names(workspace)
    if alive:
        sections.append("")
        sections.append("=== ALIVE contexts (bind one to inject its memory) ===")
        sections.extend(f"- {name}" for name in alive)
        sections.append("=== end ALIVE contexts ===")
    return "\n".join(sections) + "\n"


def _emit_bootstrap(workspace: Path, context: str) -> None:
    """Emit the bound context's bootstrap: the context header + the lean memory prefix.

    FR30 (T-044-60): no dispatcher preflight — it restates ``DADAIA.md`` §1/§2, which the
    agent already carries as law, not per-prompt state.
    """
    sections = [f"[{context}]"]
    memory = _build_memory(workspace / "repos" / context / "specs")
    if memory:
        sections.append(memory)
    _emit("\n".join(sections) + "\n")


def main() -> int:
    """Run the context-injection hook. Returns 0 always."""
    payload = _common.read_stdin_json()
    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open: emit nothing rather than crash
        _emit("")
        return 0

    session_id = _common.resolve_session_id(payload, default="workspace")

    # Sentinel — path BYTE-IDENTICAL to the shell sentinel: .dadaia/tmp/ctx-inject-fired-<id>.
    # Its content now records the last injected slug so a re-bind is detectable. Inject-time
    # GC of stale sentinels runs first so leftover sentinels are reaped on every fire.
    tmp_dir = workspace / ".dadaia" / "tmp"

    # PostCompact (v0.2.8, kimi-code): stamp the compact-epoch marker, then RE-EMIT the
    # bootstrap on stdout. Kimi's PostCompact is observation-only (the harness discards
    # stdout), so this never double-injects — the deterministic re-injection still
    # happens at the next UserPromptSubmit via the single authority. The emission follows
    # the observable-contract doctrine (projected-pre-gate-silent-allow: a silent hook is
    # unverifiable — external automation must SEE the re-injection happen). The sentinel
    # is deliberately NOT restamped here, so the next prompt still re-injects.
    if os.environ.get("DADAIA_HOOK_EVENT") == "PostCompact":
        with contextlib.suppress(OSError):
            tmp_dir.mkdir(parents=True, exist_ok=True)
            (tmp_dir / f"{_COMPACT_PREFIX}{session_id}").write_text("", encoding="utf-8")
        sentinel = tmp_dir / f"{_SENTINEL_PREFIX}{session_id}"
        _, recorded_slug = _read_sentinel(sentinel)
        # The emission resolves through the SAME single authority as a normal prompt
        # (T-50-03: self-keyed session record → DADAIA_CONTEXT → this session's own live
        # harness-native record → cwd's repo), falling back to the sentinel's recorded
        # slug: a bind with NO prior prompt leaves no sentinel file, but its session
        # record still names the bound context (consumer round-3 bug
        # kimi-postcompact-omits-bound-context-bootstrap).
        context = _resolve_context(workspace, session_id)
        if not context:
            context = recorded_slug
        if context and (workspace / "repos" / context / "specs").is_dir():
            _emit_bootstrap(workspace, context)
        else:
            _emit(_generic_preflight(workspace))
        return 0

    # Claude Code SessionStart re-injection (bug claude-compact-reinjection-missing):
    # a compact erased the injected bootstrap; a /clear wiped the whole context. Claude
    # Code ADDS SessionStart stdout back to context (unlike Kimi's discard-stdout
    # PostCompact), so the bootstrap re-emits at the event ITSELF and the sentinel is
    # restamped immediately — the next prompt stays silent (exactly-once discipline) and
    # no compact marker is stamped (it would double-inject at the next prompt). Detection
    # is payload-driven (hook_event_name + source), never an env prefix — the settings
    # command stays a plain, Windows-safe module invocation. Sources outside
    # {compact, clear} (startup/resume/fork) fall through to the normal bind-driven flow.
    if str(payload.get("hook_event_name") or "") == "SessionStart" and str(
        payload.get("source") or ""
    ) in ("compact", "clear"):
        sentinel = tmp_dir / f"{_SENTINEL_PREFIX}{session_id}"
        _, recorded_slug = _read_sentinel(sentinel)
        # Same single-authority resolution + recorded-slug fallback as PostCompact above.
        context = _resolve_context(workspace, session_id)
        if not context:
            context = recorded_slug
        if context and (workspace / "repos" / context / "specs").is_dir():
            _emit_bootstrap(workspace, context)
            _stamp_sentinel(tmp_dir, sentinel, context)
        else:
            _emit(_generic_preflight(workspace))
            _stamp_sentinel(tmp_dir, sentinel, "")
        return 0

    sentinel = tmp_dir / f"{_SENTINEL_PREFIX}{session_id}"
    _gc_stale_sentinels(tmp_dir)
    sentinel_mtime, recorded_slug = _read_sentinel(sentinel)
    sentinel_exists = sentinel_mtime is not None

    # Compact trigger: a compact marker newer than the sentinel forces re-injection on
    # this prompt (the sentinel restamp below makes the following prompt silent again).
    compact_marker = tmp_dir / f"{_COMPACT_PREFIX}{session_id}"
    compact_mtime: float | None = None
    with contextlib.suppress(OSError):
        compact_mtime = compact_marker.stat().st_mtime
    compacted = (
        sentinel_mtime is not None and compact_mtime is not None and compact_mtime > sentinel_mtime
    )

    context = _resolve_context(workspace, session_id)

    # T-50-03 injection trigger (SPEC v0.5.0 FR1 coupling 1): this session's OWN bind
    # (``bound_at``, self-keyed session record) newer than the sentinel forces
    # re-injection even when the resolved context NAME is unchanged — a same-context
    # re-bind is how a mode/release change reaches a live session (new pin: today a
    # same-context re-bind does NOT re-inject; under this trigger it MUST).
    bound_at = _session_bound_at(workspace, session_id)
    rebound = sentinel_mtime is not None and bound_at is not None and bound_at > sentinel_mtime

    if not context and compacted and recorded_slug:
        # Post-compact re-injection source: the single authority no longer resolves a
        # context on this prompt (e.g. the self-keyed session record was cleared/expired),
        # but a compaction just occurred. The sentinel's recorded slug is the last
        # injected context — the session's bound truth — and is what gets re-injected
        # after a compaction.
        context = recorded_slug

    # Unbound: generic preflight (NO memory). Emit once per session — a fresh session (no
    # sentinel) gets it and stamps the sentinel; a repeat prompt is silent, unless a
    # compaction just wiped the context (compacted ⇒ re-emit the preflight once).
    if not context:
        if sentinel_exists and not compacted:
            return 0
        _emit(_generic_preflight(workspace))
        _stamp_sentinel(tmp_dir, sentinel, "")
        return 0

    specs_dir = workspace / "repos" / context / "specs"
    if not specs_dir.is_dir():
        # Resolved a context with no specs tree — degrade to generic preflight once.
        if sentinel_exists and not compacted:
            return 0
        _emit(_generic_preflight(workspace))
        _stamp_sentinel(tmp_dir, sentinel, "")
        return 0

    # Re-injection guard: a repeat prompt for the SAME already-injected slug is silent. A
    # re-bind to a different context (recorded_slug != context), a compaction newer than
    # the sentinel, THIS session's own rebind (bound_at newer than the sentinel, T-50-03 —
    # covers a SAME-CONTEXT re-bind too), or a fresh session always (re-)injects that
    # context's memory and restamps the sentinel with the new slug.
    if sentinel_exists and recorded_slug == context and not compacted and not rebound:
        return 0

    sections = [f"[{context}]"]
    memory = _build_memory(specs_dir)
    if memory:
        sections.append(memory)
    _emit("\n".join(sections) + "\n")
    _stamp_sentinel(tmp_dir, sentinel, context)
    return 0


if __name__ == "__main__":
    sys.exit(main())
