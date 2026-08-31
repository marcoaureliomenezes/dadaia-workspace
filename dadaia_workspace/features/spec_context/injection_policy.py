"""Context-injection decision policy — pure, I/O-free (F009, 20260830 audit).

``hooks/ctx_inject.py`` was a 469-line hook holding a four-branch injection state
machine with three near-duplicate resolve-emit-stamp blocks; each historical fix
(kimi-postcompact-omits-bound-context-bootstrap, claude-compact-reinjection-missing,
the compact-marker trigger, the T-50-03 self-keyed rebind trigger) added a branch to
transport code testable only by simulating stdin+env+files. The DECISION now lives
here as one function over plain values; the hook computes the inputs and executes the
returned :class:`InjectionDecision` — policy never touches a file, stdin or env.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

__all__ = ["InjectionDecision", "decide_injection"]

#: What the hook must do: emit the bound context's bootstrap, the generic preflight,
#: or nothing.
Emission = Literal["bootstrap", "preflight", "none"]

#: The hook event kinds the policy distinguishes. ``postcompact`` is Kimi's
#: observation-only PostCompact (never stamps — the next prompt still re-injects);
#: ``session_restart`` is Claude Code's SessionStart with source compact/clear (emits
#: AND stamps — exactly-once discipline); everything else is a normal ``prompt``.
Event = Literal["postcompact", "session_restart", "prompt"]


@dataclass(frozen=True)
class InjectionDecision:
    """The transport-executable outcome: what to emit, for which context, and which
    slug to stamp into the sentinel (``None`` = leave the sentinel untouched)."""

    emit: Emission
    context: str = ""
    stamp_slug: str | None = None


def decide_injection(
    *,
    event: Event,
    context: str,
    recorded_slug: str,
    sentinel_exists: bool,
    compacted: bool,
    rebound: bool,
    has_specs: Callable[[str], bool],
) -> InjectionDecision:
    """Decide the injection for one hook invocation.

    Inputs are plain values the transport resolves: *context* is the single-authority
    resolution (self-keyed session record → DADAIA_CONTEXT → live harness record →
    cwd repo); *recorded_slug* is the sentinel's last-injected slug; *compacted* is
    "compact marker newer than sentinel"; *rebound* is "this session's own bound_at
    newer than the sentinel" (T-50-03 — covers a same-context re-bind); *has_specs*
    answers "does this context resolve to a specs tree" (the one I/O question,
    injected as a predicate so the table stays pure).
    """
    if event in ("postcompact", "session_restart"):
        # Recorded-slug fallback: a bind with no prior prompt leaves no sentinel, but
        # a compact/clear re-entry still deserves the bound context's bootstrap (bug
        # kimi-postcompact-omits-bound-context-bootstrap).
        ctx = context or recorded_slug
        stamps = event == "session_restart"
        if ctx and has_specs(ctx):
            return InjectionDecision("bootstrap", ctx, ctx if stamps else None)
        return InjectionDecision("preflight", "", "" if stamps else None)

    # prompt
    if not context and compacted and recorded_slug:
        # Post-compact re-injection source: the authority resolves nothing, but a
        # compaction just occurred — the sentinel's recorded slug is the session's
        # bound truth.
        context = recorded_slug
    if not context or not has_specs(context):
        # Unbound (or bound to a context with no specs tree): generic preflight, once
        # per session — silent on repeat prompts unless a compaction wiped context.
        if sentinel_exists and not compacted:
            return InjectionDecision("none")
        return InjectionDecision("preflight", "", "")
    if sentinel_exists and recorded_slug == context and not compacted and not rebound:
        # Repeat prompt for the same already-injected slug: silent.
        return InjectionDecision("none")
    return InjectionDecision("bootstrap", context, context)
