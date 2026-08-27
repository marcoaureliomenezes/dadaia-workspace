"""Pure, read-only fold over ``RELEASE.jsonl`` records (v0.5.0 FR4, D3/D7/D11, T-050-11).

``RELEASE.jsonl`` is the append-only event stream that replaces ``ACTIVE.md``'s phase
field and ``CLOSURE.md``'s closure narrative (SPEC FR4). Its envelope is exactly
``{ts, event, agent, data}`` — seven canonical kinds, no ``session_id`` — validated at
authoring time against ``public/schemas/releases/release-event-v1.schema.json``.

**This module never performs file I/O.** It parses already-read text and folds already-
parsed events; ``core/`` file I/O is a ratchet (``tests/contract/test_core_file_io_purity.py``,
architect A9) and adding this module's stem to that ratchet's authorized set would also
require re-opening ``specs/memory/architecture.md`` — MEMORY, writable only in
DEFINITION/CLOSURE. The three callers FR4 names (``hooks/sdd_gate.py``, ``container.py``,
``features/specs/doctor_release.py``) each own their OWN tiny tri-state disk read, in the
exact shape ``hooks.sdd_gate._active_field`` already uses for ``ACTIVE.md`` — precedent
already exists for that split (``_active_field`` in ``hooks`` vs ``doctor_common.read_active_md``
in ``features/specs``, two independent readers of the same file, for the same
layer-boundary reason). What lands in exactly ONE place here is the FOLD semantics: which
``phase`` record wins, which milestone record wins, and what counts as an immutability
violation.

A contract test (``tests/contract/test_release_events_read_only.py``) asserts this module's
source contains no write call (``open(..., "w"/"a")``, ``.write_text(``, ``atomic_write(``) —
milestone and phase records are appended elsewhere, by agents with file tools, because
``RELEASE.jsonl`` is append-only (no read-modify-write race to guard against here).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "MILESTONE_KINDS",
    "ReleaseEvent",
    "ReleaseEventKind",
    "ReleaseFold",
    "fold_release_events",
    "parse_release_events",
]


class ReleaseEventKind(StrEnum):
    """The seven canonical release-event kinds (D3/D7/D11).

    The first Draft carried fifteen; ``created``, ``spec_status``, ``review``, ``push``,
    ``pr``, ``ship`` and ``archive`` were dropped because each is already recorded
    elsewhere (git history for commits/pushes/reviews, ``phase: ARCHIVED`` *is* the
    archive record, ``shipped`` alone covers the ship fact) and none is required by D3.
    """

    PHASE = "phase"
    DEFINED = "defined"
    IMPLEMENTED = "implemented"
    SHIPPED = "shipped"
    AUDITED = "audited"
    RC = "rc"
    NOTE = "note"


#: The three sha-bearing milestone kinds (D3) — immutable facts, appended at most once
#: meaningfully per release. A later record of the same kind is a rewrite attempt, never
#: folded over the first (see :func:`fold_release_events`).
MILESTONE_KINDS: frozenset[ReleaseEventKind] = frozenset(
    {ReleaseEventKind.DEFINED, ReleaseEventKind.IMPLEMENTED, ReleaseEventKind.SHIPPED}
)

_EVENT_KIND_VALUES: frozenset[str] = frozenset(k.value for k in ReleaseEventKind)
_MILESTONE_KIND_VALUES: frozenset[str] = frozenset(k.value for k in MILESTONE_KINDS)


@dataclass(frozen=True)
class ReleaseEvent:
    """One decoded ``RELEASE.jsonl`` record. ``data`` is the event-specific payload —
    this module never interprets ``data``'s inner shape beyond exposing it (the schema,
    not this fold, is the shape authority for each kind)."""

    ts: str
    event: str
    agent: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReleaseFold:
    """The fold result over one release's already-parsed event stream.

    ``phase`` is the LAST ``phase`` record's ``data["phase"]`` value, or ``""`` when no
    ``phase`` record is present — the gate's own MEMORY-phase resolution reads the
    newest phase declaration (D3). ``milestones`` maps each milestone kind
    (``defined``/``implemented``/``shipped``) to its FIRST record. ``duplicate_milestones``
    carries every LATER record of a kind already present in ``milestones`` — an
    immutability-violation finding, never silently folded over the first (D3's "immutable
    facts", enforced here at the model level; the doctor is the WARNING surface, D15).
    """

    phase: str
    milestones: dict[str, ReleaseEvent]
    duplicate_milestones: tuple[ReleaseEvent, ...]


def parse_release_events(text: str) -> tuple[tuple[ReleaseEvent, ...], tuple[str, ...]]:
    """Decode ``text`` (the raw content of a ``RELEASE.jsonl`` file) into events.

    Pure — no I/O. A malformed line (bad JSON, missing/malformed envelope field, an
    unrecognised ``event`` kind, or a non-object ``data``) is skipped and recorded in the
    returned error list, keyed by 1-based line number; one bad line never loses the
    well-formed records around it (an append-only ledger tolerates partial corruption).
    """
    events: list[ReleaseEvent] = []
    errors: list[str] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {lineno}: invalid JSON ({exc})")
            continue
        if not isinstance(obj, dict):
            errors.append(f"line {lineno}: not a JSON object")
            continue
        ts, event, agent = obj.get("ts"), obj.get("event"), obj.get("agent")
        data = obj.get("data", {})
        if not isinstance(ts, str) or not isinstance(event, str) or not isinstance(agent, str):
            errors.append(f"line {lineno}: missing/malformed ts, event or agent")
            continue
        if event not in _EVENT_KIND_VALUES:
            errors.append(f"line {lineno}: unknown event kind {event!r}")
            continue
        if not isinstance(data, dict):
            errors.append(f"line {lineno}: 'data' is not an object")
            continue
        events.append(ReleaseEvent(ts=ts, event=event, agent=agent, data=data))
    return tuple(events), tuple(errors)


def fold_release_events(events: tuple[ReleaseEvent, ...] | list[ReleaseEvent]) -> ReleaseFold:
    """Fold an already-parsed event stream into phase + milestone state.

    Pure — no I/O, no ordering assumption beyond append order (the caller supplies
    events in file order; this fold does not re-sort by ``ts``). See :class:`ReleaseFold`
    for the exact phase/milestone semantics.
    """
    phase = ""
    milestones: dict[str, ReleaseEvent] = {}
    duplicates: list[ReleaseEvent] = []
    for evt in events:
        if evt.event == ReleaseEventKind.PHASE.value:
            value = evt.data.get("phase")
            if isinstance(value, str) and value:
                phase = value
        elif evt.event in _MILESTONE_KIND_VALUES:
            if evt.event in milestones:
                duplicates.append(evt)
            else:
                milestones[evt.event] = evt
    return ReleaseFold(phase=phase, milestones=milestones, duplicate_milestones=tuple(duplicates))
