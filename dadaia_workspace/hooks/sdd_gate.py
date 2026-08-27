"""PreToolUse SDD gate (the canonical, cross-platform gate surface).

This hook is the enforcement entrypoint the harness invokes as
``python -m dadaia_workspace.hooks.sdd_gate``. It does NOT re-derive the gate policy:
it delegates classification + decision to :func:`gate_policy.classify_path` and
:func:`gate_policy.evaluate`, which is the single source of truth (avoids a third
drifting copy alongside the bash gate).

1. **PATH-first context slug.** The context is derived via the single resolution
   authority (:func:`dadaia_workspace.container.resolve_context`, ``DADAIA.md`` §3),
   called with ``target_path=fpath`` so the write-target path (``repos/<slug>/...``)
   wins ahead of every other rung — a write under ``repos/B/...`` therefore never
   touches ``repos/A``'s presence, even while ``DADAIA_CONTEXT`` names a different
   context (T-50-02, SPEC v0.5.0 FR1). A write under NO repo falls through to
   ``DADAIA_CONTEXT``, then this session's own live record, then the repo containing
   the current working directory, before resolving unattributed.
2. **PROTECTED is the sole fail-CLOSED path.** ``.dadaia/sessions/`` writes are blocked
   unconditionally (SEC-01); every other class fails OPEN.
3. **Fail-open posture.** No non-PROTECTED, non-self-READ write blocks because of
   another session. Mode is strictly self-scoped: ``DADAIA_MODE`` → this session's
   own record → IMPLEMENTATION. Mutating writes upsert advisory presence.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dadaia_workspace.features.spec_context import gate_policy, session_identity
from dadaia_workspace.hooks import _common

_SLUG_STRIP = re.compile(r"[^A-Za-z0-9_-]")

#: Default mode when neither the env override nor a session record resolves one. Missing-mode
#: sessions stay IMPLEMENTATION-capable — Decision D-3 / FR-R4-04.
_DEFAULT_MODE = "IMPLEMENTATION"


def _resolve_holder_pid(payload: dict[str, object]) -> int:
    """Resolve the LONG-LIVED pid to record in the presence record (WS-R2 lineage).

    The gate runs as a short-lived ``python -m dadaia_workspace.hooks.sdd_gate`` child
    that exits milliseconds after the write. Recording ``os.getpid()`` (this child's own
    pid) would make the recorded pid meaningless the instant the hook exits. We
    therefore record a pid that **outlives the hook**:

    1. If the harness stdin payload carries an explicit harness pid (``harness_pid`` /
       ``parent_pid`` / ``ppid``), prefer it — it names the long-lived harness process
       most precisely. (No current harness sends one; this is forward-compatible and
       lets tests pin a known-alive pid.)
    2. Otherwise ``os.getppid()`` — the parent that spawned this hook child, i.e. the
       harness process. It stays alive for the whole session.

    A non-positive or unparseable payload pid falls back to ``os.getppid()``.
    """
    for key in ("harness_pid", "parent_pid", "ppid"):
        raw = payload.get(key)
        if isinstance(raw, int) and raw > 0:
            return raw
        if isinstance(raw, str):
            try:
                value = int(raw.strip())
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    return os.getppid()


def _resolve_workspace() -> Path:
    """Resolve the workspace root: ``WORKSPACE_ROOT`` env wins, else walk up from cwd."""
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def _context_slug(fpath: Path) -> str:
    """Derive the context slug via the single resolution authority (T-50-02, SPEC v0.5.0
    FR1 — re-points consumer "E").

    Delegates to :func:`dadaia_workspace.container.resolve_context` with
    ``target_path=fpath`` (``core.specs_resolver`` is a forbidden direct import for
    ``hooks`` — ``bind-resolution-seam-is-a-single-home``, ZERO ``ignore_imports`` —
    so the composition-root seam in ``container`` is the sanctioned path). ``target_path``
    is what preserves this hook's PATH-FIRST semantics through the authority's rung 0: a
    target under ``<ws>/repos/<slug>/...`` belongs to context ``<slug>`` regardless of
    ``DADAIA_CONTEXT`` or which context is first-ALIVE in the registry — rung 0 is
    consulted before rung 1 (the env var).

    **Intended semantic widening (SPEC FR1, this task's acceptance criterion):** a write
    under NO repo used to resolve via ``DADAIA_CONTEXT`` only (the old 2-rung ladder this
    function used to implement). It now falls through the authority's remaining rungs —
    this session's own LIVE record (rung 2), then the repo containing the current
    working directory (rung 3) — before giving up unattributed. The result is sanitized
    to ``[A-Za-z0-9_-]`` (CWE-22), matching the authority's own allowlist.
    """
    # Direct core import (F-01, v0.5.0 code review): the container is the DI
    # composition root and costs ~2s of import graph per one-shot hook process; the
    # seam contract sanctions hooks as direct importers of the single authority.
    from dadaia_workspace.core.specs_resolver import resolve_context

    slug = resolve_context(target_path=fpath) or ""
    return _SLUG_STRIP.sub("", slug)


def _resolve_mode(workspace: Path, session_id: str, ctx: str = "") -> str:
    """Resolve the session's bind mode. First hit wins:

    1. ``DADAIA_MODE`` env fast-path override — an operator-shell escape (the harness never
       sets this; it is honored only when the operator deliberately exports it).
    2. The CLI-owned session record keyed by the **resolved harness session id**
       (``session_identity.read_session``) — this session's OWN bind, if it bound itself.
    3. Default ``IMPLEMENTATION``: no env and no self record.

    A foreign session's bind can never change this result. ``ctx`` is accepted for
    call-site compatibility but is not consulted.

    Fail-soft: every lookup returns ``None`` on missing/malformed input, so mode
    resolution never raises.
    """
    del ctx
    env_mode = os.environ.get("DADAIA_MODE")
    if env_mode:
        return env_mode
    rec = session_identity.read_session(workspace, session_id)
    if rec is not None:
        raw = rec.get("mode")
        if raw:
            return str(raw)
    return _DEFAULT_MODE


def _active_field(specs_dir: Path, field: str) -> str | None:
    """Read a ``<field>: <value>`` line from ``releases/ACTIVE.md`` (tri-state).

    v0.1.50 FR1 (audit F-3): the return distinguishes three outcomes —
    ``str`` (readable; ``""`` when the field is missing), ``""`` when the file does
    not exist (a fresh context legitimately has no ACTIVE.md — "no release" truth),
    and ``None`` when the file exists but could NOT be read (a genuine I/O failure).
    Callers must treat ``None`` as UNKNOWN, never as "none".
    """
    active = specs_dir / "releases" / "ACTIVE.md"
    try:
        text = active.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError:
        return None
    pat = re.compile(rf"^{re.escape(field)}:\s*(.+?)\s*$", re.MULTILINE)
    m = pat.search(text)
    return m.group(1) if m else ""


def _release_jsonl_phase(specs_dir: Path, release_id: str) -> str | None:
    """Tri-state ``RELEASE.jsonl`` phase fold, in the shape of :func:`_active_field`
    (v0.5.0 FR4, T-050-11, A4.1a).

    Hooks never import the container (standing law) — this reads
    ``core.release_events`` directly, the fold's one home, and does its OWN tiny disk
    read exactly the way :func:`_active_field` already does for ``ACTIVE.md`` (the same
    split already exists there: this function vs ``doctor_common.read_active_md``, two
    independent readers of one file, for the same layer-boundary reason).
    ``_active_field``/``ACTIVE.md`` stays the gate's sole decision authority in this
    expand phase (A4.5) — a disagreement between the two is a doctor WARNING
    (SPEC-DOC-042), never a gate decision (D15: never a block). Fail-soft: any
    unexpected parse condition never raises past this function.
    """
    from dadaia_workspace.core.release_events import fold_release_events, parse_release_events

    path = specs_dir / "releases" / release_id / "RELEASE.jsonl"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError:
        return None
    events, _errors = parse_release_events(text)
    return fold_release_events(events).phase


def _evaluate_target(
    payload: dict[str, object], workspace: Path, raw_path: str
) -> tuple[gate_policy.Decision, str]:
    """Evaluate ONE write-target path through the gate policy.

    Returns ``(ALLOW, "")`` for any allow path and ``(BLOCK, reason)`` for a blocked one.
    Fail-open: an unresolvable/unattributable MUTATING write yields ALLOW (matches shell).
    The caller (``main``) iterates every ``apply_patch`` file header and lets the most
    restrictive verdict win (FR-W4-04) — the first BLOCK short-circuits the whole patch.
    """
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = workspace / fpath

    # Workspace-relative path for the policy classifier (POSIX-style separators).
    try:
        rel_path = fpath.resolve().relative_to(workspace.resolve()).as_posix()
    except (ValueError, OSError):
        rel_path = fpath.as_posix()

    cls = gate_policy.classify_path(rel_path)

    # PROTECTED short-circuit (sole fail-CLOSED path): no context/lease work needed.
    if cls == gate_policy.PathClass.PROTECTED:
        return gate_policy.evaluate(
            workspace,
            rel_path,
            ctx="",
            phase="",
            session_id="",
            release="",
            mode="",
        )

    ctx = _context_slug(fpath)
    # F-02 (v0.5.0 code review): the authority returns the context NAME; the on-disk
    # directory is the registry's repo_slug, and the two legitimately differ
    # (`context create <name> --repo <slug>`). Map before joining, like
    # container._context_specs_dir does — otherwise ACTIVE.md is read from a
    # non-existent dir and MEMORY writes are wrongly phase-blocked.
    if ctx:
        from dadaia_workspace.core.specs_resolver import repo_slug_for_context

        specs_dir = workspace / "repos" / repo_slug_for_context(workspace, ctx) / "specs"
    else:
        specs_dir = workspace / "specs"
    phase = _active_field(specs_dir, "phase") or ""
    release_raw = _active_field(specs_dir, "release")
    release = release_raw or "none"
    # T-050-11 (FR4 expand half, A4.1a): call the fold directly (hooks never import the
    # container) so RELEASE.jsonl is exercised on the write hot path from the first task
    # that lands it. `_active_field`/ACTIVE.md stays the sole decision authority driving
    # `gate_policy.evaluate` below until the contract step (T-050-21A, A4.1) repoints
    # every remaining consumer — the fold's result is intentionally unused here; a
    # disagreement is a doctor WARNING (SPEC-DOC-042), never a gate decision.
    if release_raw:
        _release_jsonl_phase(specs_dir, release_raw)
    session_id = _common.resolve_session_id(payload, default="anon-session")
    # Mode resolution order (v0.1.76 FR4, strictly self-scoped): DADAIA_MODE env
    # override → self-keyed session record → default. No context-incumbent fallback —
    # a foreign session's bind can never change what THIS session's write resolves to.
    mode = _resolve_mode(workspace, session_id, ctx)

    # MUTATING with no resolvable context → fail open (UNGATED, no presence target),
    # matching legacy shell behavior. NOTE: a READ-bound session that *does* resolve a
    # context is still blocked below by gate_policy.evaluate (self-scoped, opt-in); the
    # no-context fail-open only covers MUTATING writes the gate cannot attribute to any
    # context (no slug, no DADAIA_CONTEXT).
    if cls == gate_policy.PathClass.MUTATING and not ctx:
        return gate_policy.Decision.ALLOW, ""

    runtime = os.environ.get("DADAIA_RUNTIME", "unknown")
    return gate_policy.evaluate(
        workspace,
        rel_path,
        ctx=ctx,
        phase=phase,
        session_id=session_id,
        release=release,
        mode=mode,
        runtime=runtime,
        # NF-1: record a LONG-LIVED pid (the harness, via getppid / payload), never this
        # ephemeral hook child's own — a presence record naming a dead pid is misleading.
        pid=_resolve_holder_pid(payload),
    )


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """Pure SDD-gate policy over an ALREADY-PARSED hook payload.

    Returns a block reason string when the write must be BLOCKed, else ``None`` (ALLOW).
    Back-compat surface — the merged ``pre_gate`` entrypoint drives
    :func:`evaluate_payload_with_advisory` so an ALLOW's presence advisory survives.
    """
    block, _advisory = evaluate_payload_with_advisory(payload)
    return block


def evaluate_payload_with_advisory(payload: dict[str, object]) -> tuple[str | None, str | None]:
    """Evaluate the SDD gate returning ``(block_reason, allow_advisory)``.

    ``block_reason`` is non-``None`` when the write must be BLOCKed. ``allow_advisory``
    carries the NO-LOCKS presence advisory an allowed MUTATING write may produce (bug
    pre-gate-drops-live-presence-advisory-042: ``gate_policy.evaluate`` returns it, but
    the old bool-shaped surface flattened ALLOW to ``None`` and the mandated throttled
    warning never reached the caller).

    FR-W4-04: classify EVERY write target. A multi-file apply_patch surfaces every file
    header; the most restrictive verdict wins — the first BLOCK stops the whole patch.
    """
    name = _common.tool_name(payload)
    if not _common.is_write_tool(name):
        return None, None

    raw_paths = _common.target_paths(payload)
    if not raw_paths:
        # Fail-safe: unparseable target → ALLOW (never deadlock on a parse miss).
        return None, None

    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open: unresolved workspace must not block
        return None, None

    advisory: str | None = None
    for raw_path in raw_paths:
        decision, reason = _evaluate_target(payload, workspace, raw_path)
        if decision == gate_policy.Decision.BLOCK:
            return reason, None
        if reason and advisory is None:
            advisory = reason
    return None, advisory
