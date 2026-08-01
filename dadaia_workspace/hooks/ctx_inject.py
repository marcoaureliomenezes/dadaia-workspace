"""Context-injection hook (the canonical, cross-platform gate surface).

Invoked on SessionStart and UserPromptSubmit. It injects the lean workspace bootstrap
(context line + dispatcher preflight + tech-stack.md + catalog). A session-keyed sentinel
guards re-injection: subsequent prompts emit nothing UNLESS a ``dadaia context bind`` has
stamped a newer bind-epoch marker (FR-W2, ADR-G5) — bind is the SOLE trigger for
context-memory injection.

Bind-driven injection state machine (FR-W2-01 / FR-W2-02, v0.1.14)
-----------------------------------------------------------------
Context resolution chain (``_resolve_context``): ``DADAIA_CONTEXT`` env → self-keyed
session record (bound context) → newest bind-epoch marker newer than this session's
sentinel → ``""``. There is no first-ALIVE fallback.

Re-injection rules:

- **No sentinel for this sid** → generic preflight only (dispatcher preflight + the list
  of ALIVE contexts; NO context memory) and the sentinel is stamped. A pre-existing
  bind-epoch marker NEVER binds a fresh session — a marker qualifies only by being newer
  than an EXISTING sentinel.
- **A bind-epoch marker (or self-keyed bound context) newer than / different from the
  sentinel** → re-inject that context's memory and restamp the sentinel content with the
  injected slug. A re-bind to a different context therefore re-injects.
- **Repeat prompt** (sentinel exists, no qualifying newer marker, same slug) → silent.

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
  a PostCompact hook see byte-identical behavior — no marker, no trigger.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import time
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

_DISPATCHER_PREFLIGHT = """=== dispatcher preflight (SDD routing) ===
Before acting on a request in this workspace:
1. Resolve the active context (above) and the OWNING role for the
   artifact class you are about to touch: backlog -> project-manager;
   SPEC/PLAN/TASKS -> product-engineer; agents/skills/rules/hooks
   (the AI surface) -> ai-engineer audit; production code ->
   software-engineer; reviews -> code/security/qa reviewers.
2. Ordered lifecycle work is driven by dispatching the owning persona
   and having it follow the matching skill (grill-me before a SPEC,
   release-definition to author it, release-closure to close it).
   Ownership is a coordination convention; concurrent sessions are
   surfaced through advisory presence and never blocked.
3. If the operator asks for multi-agent / deep / AI-surface work and a
   subagent or dispatch tool is not in your active tool set, DISCOVER it
   first (e.g. tool_search for the agent/dispatch tool) BEFORE starting
   the main task -- do not silently proceed as a generic single agent.
4. Limitation (truthful): this harness does NOT auto-spawn subagents
   from static instruction files. Those files are reference docs;
   explicit dispatcher/operator fan-out is required.
=== end dispatcher preflight ==="""


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


def _newest_qualifying_marker(
    workspace: Path, sentinel_mtime: float | None, harness_pid: int
) -> str:
    """Newest bind-epoch marker that qualifies for re-injection, else ``""``.

    A marker qualifies only when BOTH hold:

    1. it is **newer than an EXISTING sentinel** (``sentinel_mtime`` is the sentinel's
       mtime, or ``None`` when no sentinel exists — then NOTHING qualifies, so a
       pre-existing marker never binds a fresh session, FR-W2-02); and
    2. ``harness_pid`` — this session's own harness pid — is a **member of the marker's
       recorded ancestry chain** (W1-7/W1-8, v0.1.47). The marker records the bind
       process's nearest-first ancestry pid chain; the hook's harness pid is the stable
       anchor that appears in it (the hook is a direct child of the harness, so its
       ``os.getppid()`` equals a chain entry) even after the ephemeral bind shell has died.
       A legacy/empty marker (empty chain) or a chain belonging to a DIFFERENT session
       (disjoint from this harness pid) is IGNORED, so a concurrent session's bind can
       never steal this session's context. When no marker is attributable, the caller
       falls back to generic preflight (never another session's context).

    The newest qualifying, attributed marker (by mtime) wins.
    """
    if sentinel_mtime is None:
        return ""
    qualifying: list[tuple[float, str]] = []
    for slug, mtime in session_identity.iter_bind_epochs(workspace):
        if mtime <= sentinel_mtime:
            continue
        marker_chain = session_identity.read_bind_epoch_pids(workspace, slug)
        if harness_pid not in marker_chain:
            continue
        qualifying.append((mtime, slug))
    if not qualifying:
        return ""
    qualifying.sort()
    return qualifying[-1][1]


def _resolve_context(
    workspace: Path, session_id: str, sentinel_mtime: float | None, harness_pid: int
) -> str:
    """Resolve the context to inject (FR-W2-01 chain). First-ALIVE fallback DELETED.

    Chain: ``DADAIA_CONTEXT`` env → self-keyed session record (bound context) → newest
    bind-epoch marker newer than this session's sentinel AND attributed to this session's
    harness pid (W1-7) → ``""`` (generic preflight).
    """
    env = os.environ.get("DADAIA_CONTEXT")
    if env:
        return env
    bound = _session_bound_context(workspace, session_id)
    if bound:
        return bound
    return _newest_qualifying_marker(workspace, sentinel_mtime, harness_pid)


def _resolve_harness_pid(payload: dict[str, object]) -> int:
    """Resolve this session's long-lived harness pid (W1-7 / T-47-16).

    Reuses the SDD gate's long-lived process resolution (``sdd_gate._resolve_holder_pid``): a
    payload-provided ``harness_pid``/``parent_pid``/``ppid`` wins, else ``os.getppid()``
    (this hook child's parent — the harness process). ``dadaia context bind`` stamps the
    bind-epoch marker with the bind process's ancestry chain, which contains this same
    harness pid deeper up, so the marker is attributed to this session by MEMBERSHIP
    (``harness_pid in marker_chain``) even after the ephemeral bind shell has died. Lazy
    import keeps the frequently-spawned hook's import surface minimal.
    """
    from dadaia_workspace.hooks.sdd_gate import _resolve_holder_pid

    return _resolve_holder_pid(payload)


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


#: Max non-empty lines of ``tech-stack.md`` kept in the bind-time SESSION bootstrap digest.
#: WS-C dehydration (v0.1.30 / T-30-E-05): the bootstrap is a lean session-orientation aid,
#: NOT the source of lifecycle-prompt context. Lifecycle prompts compose their context from
#: the Python dynamic selector (``ContextSelector`` + ``LifecyclePromptBuilder``), so the
#: hook no longer dumps the FULL tech-stack body — it emits a bounded digest plus a self-pull
#: pointer. A small tech-stack file (≤ the cap) is emitted in full; a large one is reduced.
_TECH_STACK_DIGEST_MAX_LINES = 24


def _digest_tech_stack(raw: str) -> str:
    """Return a bounded digest of ``tech-stack.md`` for the lean session bootstrap.

    Keeps the leading non-empty lines, capped at :data:`_TECH_STACK_DIGEST_MAX_LINES`. When
    the file is already within the cap it is returned verbatim (so a small atom is unchanged).
    A truncated digest appends a self-pull pointer: the full atom stays on disk and the
    dynamic selector resolves it per-step when a lifecycle prompt actually needs it. Fail-open
    is implicit — the caller suppresses OSError around the read.
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
        + "\n\n… (tech-stack digest — self-pull specs/memory/tech-stack.md for full detail; "
        "lifecycle prompts get tech context from the dynamic selector, not this bootstrap)"
    )


def _build_memory(specs_dir: Path) -> str:
    """Build the once-per-session LEAN memory bootstrap (tech-stack digest + catalog digest).

    WS-C (v0.1.30 / T-30-E-05): this is a session-orientation bootstrap for an interactive
    operator session — it is NOT the context source for lifecycle prompts. Lifecycle workflow
    steps compose their prompts entirely from the Python dynamic selector
    (``ContextSelector``) bounded by each fragment's ``max_context_policy``; nothing in the
    lifecycle prompt path reads this injection or its sentinel (A30). So the bootstrap stays
    lean — a bounded tech-stack digest + the lean catalog tldr-digest, never the full memory
    tree.
    """
    memory_dir = specs_dir / "memory"
    if not memory_dir.is_dir():
        return ""
    parts = ["", "=== workspace memory (tech + catalog) ==="]
    tech = memory_dir / "tech-stack.md"
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
    """Generic preflight payload: ``[no bound context]`` + dispatcher preflight + ALIVE list.

    Emitted for an unbound session — NEVER any context memory (FR-W2-01). The ALIVE list is
    advisory (names from the registry) so the operator can bind one.
    """
    sections = ["[no bound context]", "", _DISPATCHER_PREFLIGHT]
    alive = _alive_context_names(workspace)
    if alive:
        sections.append("")
        sections.append("=== ALIVE contexts (bind one to inject its memory) ===")
        sections.extend(f"- {name}" for name in alive)
        sections.append("=== end ALIVE contexts ===")
    return "\n".join(sections) + "\n"


def _emit_bootstrap(workspace: Path, context: str) -> None:
    """Emit the bound context's bootstrap (dispatcher preflight + memory bootstrap)."""
    sections = [f"[{context}]", "", _DISPATCHER_PREFLIGHT]
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
    # happens at the next UserPromptSubmit via the marker. The emission follows the
    # observable-contract doctrine (projected-pre-gate-silent-allow: a silent hook is
    # unverifiable — external automation must SEE the re-injection happen). The sentinel
    # is deliberately NOT restamped here, so the next prompt still re-injects.
    if os.environ.get("DADAIA_HOOK_EVENT") == "PostCompact":
        with contextlib.suppress(OSError):
            tmp_dir.mkdir(parents=True, exist_ok=True)
            (tmp_dir / f"{_COMPACT_PREFIX}{session_id}").write_text("", encoding="utf-8")
        sentinel = tmp_dir / f"{_SENTINEL_PREFIX}{session_id}"
        sentinel_mtime, recorded_slug = _read_sentinel(sentinel)
        harness_pid = _resolve_harness_pid(payload)
        # The emission resolves through the SAME chain as a normal prompt (DADAIA_CONTEXT
        # env → self-keyed session record → bind-epoch marker), falling back to the
        # sentinel's recorded slug: a bind with NO prior prompt leaves no sentinel file,
        # but its session record still names the bound context (hermes round-3 bug
        # kimi-postcompact-omits-bound-context-bootstrap).
        context = _resolve_context(workspace, session_id, sentinel_mtime, harness_pid)
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
        sentinel_mtime, recorded_slug = _read_sentinel(sentinel)
        harness_pid = _resolve_harness_pid(payload)
        # Same resolution chain + recorded-slug fallback as PostCompact above.
        context = _resolve_context(workspace, session_id, sentinel_mtime, harness_pid)
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

    # The harness pid this session runs under uses the same resolution as the SDD gate
    # (payload harness_pid → os.getppid()). A bind-epoch
    # marker is honored only when its recorded pid matches this, so a concurrent session's
    # bind cannot steal this session's context.
    harness_pid = _resolve_harness_pid(payload)

    context = _resolve_context(workspace, session_id, sentinel_mtime, harness_pid)

    if not context and compacted and recorded_slug:
        # Post-compact re-injection source: the bind-epoch marker qualified at bind time
        # but is now OLDER than the sentinel, so the FR-W2-01 chain can no longer resolve
        # the context. The sentinel's recorded slug is the last injected context — the
        # session's bound truth — and is what gets re-injected after a compaction.
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
    # the sentinel, or a fresh session always (re-)injects that context's memory and
    # restamps the sentinel with the new slug.
    if sentinel_exists and recorded_slug == context and not compacted:
        return 0

    sections = [f"[{context}]", "", _DISPATCHER_PREFLIGHT]
    memory = _build_memory(specs_dir)
    if memory:
        sections.append(memory)
    _emit("\n".join(sections) + "\n")
    _stamp_sentinel(tmp_dir, sentinel, context)
    return 0


if __name__ == "__main__":
    sys.exit(main())
