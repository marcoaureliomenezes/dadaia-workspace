"""PreToolUse SDD gate (the canonical, cross-platform gate surface).

This hook is the enforcement entrypoint the harness invokes as
``python -m dadaia_workspace.hooks.sdd_gate``. It does NOT re-derive the gate policy:
it delegates classification + decision to :func:`gate_policy.classify_path` and
:func:`gate_policy.evaluate`, which is the single source of truth (avoids a third
drifting copy alongside the bash gate).

1. **One Invocation per target.** Session, context, root, mode, release and phase are
   resolved in ONE call to :func:`dadaia_workspace.core.invocation.resolve`, called
   with ``target_path=fpath`` so the write-target path (``repos/<slug>/...``) wins
   ahead of every other rung — a write under ``repos/B/...`` therefore never touches
   ``repos/A``'s presence, even while ``DADAIA_CONTEXT`` names a different context.
   Because the workspace root is ALSO derived from the target first (the K1 open-bug
   fix), a write under NO repo still falls through the same Invocation's remaining
   rungs — ``DADAIA_CONTEXT``, this session's own live record, the repo containing the
   current working directory — before resolving unattributed, and the root every rung
   agrees on is never a different one than the root the write target actually lives
   under.
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

from dadaia_workspace.core import invocation
from dadaia_workspace.features.spec_context import gate_policy
from dadaia_workspace.hooks import _common

_SLUG_STRIP = re.compile(r"[^A-Za-z0-9_-]")

#: The gate's own anonymous-session sentinel (FR5): an unresolvable session id never
#: creates a presence record — the write is still allowed, there is simply nothing to
#: be advisory about. Matches ``gate_policy._ANON_SESSION_ID``.
_ANON_SESSION_ID = "anon-session"


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


def _context_slug(fpath: Path) -> str:
    """Derive the context slug for *fpath* via the single resolution authority.

    A convenience one-liner over :func:`dadaia_workspace.core.invocation.resolve`
    (``target_path=fpath`` — rung 0 — wins ahead of every other rung); the result is
    sanitized to ``[A-Za-z0-9_-]`` (CWE-22), matching the authority's own allowlist.
    ``_evaluate_target`` below resolves its own Invocation directly (this function
    exists for callers that only need the slug).
    """
    inv = invocation.resolve(target_path=fpath, env=os.environ, cwd=Path.cwd())
    return _SLUG_STRIP.sub("", inv.context_name or "")


def _resolve_mode(workspace: Path, session_id: str, ctx: str = "") -> str:
    """Resolve the session's bind mode — a thin call onto the single mode-resolution
    rule (:func:`dadaia_workspace.core.invocation.resolve_mode`). ``ctx`` is accepted
    for call-site compatibility but is not consulted (mode is strictly self-scoped)."""
    del ctx
    return invocation.resolve_mode(workspace, session_id, os.environ)


def _evaluate_target(
    payload: dict[str, object], workspace: Path, raw_path: str
) -> tuple[gate_policy.Decision, str]:
    """Evaluate ONE write-target path through the gate policy.

    Builds exactly ONE :class:`~dadaia_workspace.core.invocation.Invocation` for
    *raw_path* (session, context, root, mode, release, phase — resolved once) and
    reads every field the policy needs off it. Returns ``(ALLOW, "")`` for any allow
    path and ``(BLOCK, reason)`` for a blocked one. Fail-open: an unresolvable/
    unattributable MUTATING write yields ALLOW. The caller (``main``) iterates every
    ``apply_patch`` file header and lets the most restrictive verdict win (FR-W4-04) —
    the first BLOCK short-circuits the whole patch.
    """
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = workspace / fpath

    # The Invocation's OWN workspace root is target-path-first (the K1 open-bug fix:
    # a cwd sitting inside a nested, independently sentinel-bearing sandbox must never
    # shadow the real root that actually owns *fpath*) — it is the authority for THIS
    # target, falling back to the outer cwd/env-resolved *workspace* only when the
    # target itself resolves no root at all (an unparseable/relative-path edge case).
    inv = invocation.resolve(target_path=fpath, payload=payload, env=os.environ, cwd=Path.cwd())
    effective_workspace = inv.workspace_root or workspace

    # Workspace-relative path for the policy classifier (POSIX-style separators).
    try:
        rel_path = fpath.resolve().relative_to(effective_workspace.resolve()).as_posix()
    except (ValueError, OSError):
        rel_path = fpath.as_posix()

    cls = gate_policy.classify_path(rel_path)

    # PROTECTED short-circuit (sole fail-CLOSED path): no context/lease work needed.
    if cls == gate_policy.PathClass.PROTECTED:
        return gate_policy.evaluate(
            effective_workspace,
            rel_path,
            ctx="",
            phase="",
            session_id="",
            release="",
            mode="",
        )

    ctx = inv.context_name or ""
    # FR5: an anonymous identity (no harness-native id, no payload session_id) never
    # creates a presence record — degrades presence accuracy only, never the write.
    session_id = inv.session_id or _ANON_SESSION_ID

    # MUTATING with no resolvable context → fail open (UNGATED, no presence target),
    # matching legacy shell behavior. NOTE: a READ-bound session that *does* resolve a
    # context is still blocked below by gate_policy.evaluate (self-scoped, opt-in); the
    # no-context fail-open only covers MUTATING writes the gate cannot attribute to any
    # context (no slug, no DADAIA_CONTEXT).
    if cls == gate_policy.PathClass.MUTATING and not ctx:
        return gate_policy.Decision.ALLOW, ""

    runtime = os.environ.get("DADAIA_RUNTIME", "unknown")
    return gate_policy.evaluate(
        effective_workspace,
        rel_path,
        ctx=ctx,
        phase=inv.phase,
        session_id=session_id,
        release=inv.release,
        mode=inv.mode,
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
        workspace = invocation.resolve(env=os.environ, cwd=Path.cwd()).workspace_root
        if workspace is None:
            raise RuntimeError("workspace not resolved")
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
