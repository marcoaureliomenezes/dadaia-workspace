"""Pre-commit presence advisory — NO-LOCKS WARN-only (v0.1.76 FR3; split out of
``service.py`` at v0.5.1 K7).

Never returns ``allowed=False``: the pre-commit chokepoint reads the same fail-soft
presence records the write gate reads and, when another live session appears, attaches
an advisory ``warn`` line — the commit proceeds regardless (NO-LOCKS DOCTRINE).

The presence read is INJECTED (``others_alive``), never a direct
``features.spec_context.presence`` import — matching this package's existing
"every I/O/process seam is injected, the CLI wires the real adapter" contract
(:func:`~dadaia_workspace.features.chokepoints.push_gate.push_gate_decision` already
requires *object_source* the same way). This is what lets ``chokepoints -> spec_context``
drop out of the import-linter ``ignore_imports`` list entirely (v0.5.1 K7): the CLI
composition root (``cli/commands/ci.py``) passes ``presence.others_alive`` directly —
zero adapter needed, since the injected callable's signature already matches it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from dadaia_workspace.features.chokepoints.branch_policy import Decision, context_slug_for_path

__all__ = [
    "PresenceRecordLike",
    "bundled_ledger_advisory",
    "context_slug_for_path",
    "pre_commit_decision",
]


class PresenceRecordLike(Protocol):
    """Structural shape ``spec_context.presence.PresenceRecord`` already satisfies —
    declared here (rather than imported) so this module never holds a
    ``features -> features`` edge for a single-field read. Read-only properties (not
    plain attributes) so a frozen dataclass structurally satisfies it, mirroring
    ``denylist_scan.BaselinePatternLike``'s existing idiom for the same reason."""

    @property
    def session_id(self) -> str: ...

    @property
    def last_seen_at(self) -> str: ...


def _age_seconds(heartbeat: object, *, now: datetime) -> int | None:
    """Whole-second age of ``heartbeat`` (for the block message); ``None`` if unparseable."""
    if not isinstance(heartbeat, str) or not heartbeat:
        return None
    try:
        hb = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
    except ValueError:
        return None
    if hb.tzinfo is None:
        hb = hb.replace(tzinfo=UTC)
    return int((now - hb).total_seconds())


def _advisory_message(ctx: str, holder_sid: str, age: int | None) -> str:
    """The advisory WARN line for another live presence record.

    Per the forbidden-law canon (architecture "the message never instructs the operator to
    rebind, relaunch, or steal"), it states who else appears active and that the commit was
    allowed regardless; it must NOT contain "rebind", "relaunch", or "lock steal".
    """
    age_part = f" (last heartbeat ~{age}s ago)" if age is not None else ""
    return (
        f"[pre-commit] WARN: context '{ctx}' shows another session '{holder_sid}'{age_part} — "
        "commit allowed (NO-LOCKS DOCTRINE: races between sessions are accepted and surfaced, "
        "never blocked; no action required)."
    )


def pre_commit_decision(
    workspace: Path,
    ctx: str | None,
    *,
    env_sid: str | None,
    others_alive: Callable[[Path, str, str], Sequence[PresenceRecordLike]],
    now: datetime | None = None,
) -> Decision:
    """Decide whether a commit into ``ctx`` may proceed (v0.1.76 FR3, WARN-only).

    NO-LOCKS DOCTRINE: this ALWAYS returns ``allowed=True``. Advisory detection reads the
    same fail-soft presence records as the write gate, via the injected *others_alive*
    (matches ``spec_context.presence.others_alive``'s own signature — the CLI passes it
    straight through, no adapter needed).

    v0.5.1 K7: the legacy ``caller_pid``/``pid_probe``/``ancestry`` parameters are
    DELETED — dead since the liveness-probe path they served was retired (their bodies
    were never read; the pre-K7 tests already asserted the probes must never run).
    """
    clock = now or datetime.now(tz=UTC)

    # Out of scope: not a recognized Spec Context repo — nothing to detect either.
    if ctx is None:
        return Decision(allowed=True, message="[pre-commit] not a Spec Context repo; allow.")

    own_sid = env_sid or "pre-commit-anonymous"
    others = others_alive(workspace, ctx, own_sid)
    if not others:
        return Decision(
            allowed=True,
            message=f"[pre-commit] no other live presence on '{ctx}'; allow.",
        )

    other = others[0]
    age = _age_seconds(other.last_seen_at, now=clock)
    return Decision(
        allowed=True,
        message="[pre-commit] commit allowed.",
        warn=_advisory_message(ctx, other.session_id, age),
    )


_LEDGER_REL = "specs/bugs/BUGS.jsonl"


def bundled_ledger_advisory(staged_paths: Sequence[str]) -> str | None:
    """FR8-isolation advisory (F015/F036, 20260827-canon-v6-first-audit) — WARN-only.

    A `dd-gitflow-default` §4 shape-1 registration stages the ledger ALONE; a shape-3
    fix stages the ledger with code + its regression test. Staging the ledger together
    with OTHER ``specs/**`` paths is the bundling that produced release-squash
    provenance and swept unrelated staged content into ledger commits. Pure and
    NO-LOCKS: returns one warn line (never a block) when ``specs/bugs/BUGS.jsonl`` is
    staged alongside another ``specs/`` path outside ``specs/bugs/``, else ``None``.
    """
    posix = [p.replace("\\", "/") for p in staged_paths]
    if _LEDGER_REL not in posix:
        return None
    bundled = [p for p in posix if p.startswith("specs/") and not p.startswith("specs/bugs/")]
    if not bundled:
        return None
    return (
        f"[pre-commit] WARN: {_LEDGER_REL} is staged together with {len(bundled)} other "
        f"specs/ path(s) (e.g. {bundled[0]}) — commit allowed (NO-LOCKS); FR8 isolation "
        "prefers the ledger line in its own commit (dd-gitflow-default §4, shapes 1/3)."
    )
