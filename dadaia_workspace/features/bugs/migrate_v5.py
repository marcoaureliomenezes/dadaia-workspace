"""The v5 ledger boundary adapter (v0.5.0 FR2/A2.5, AR-1 ruling answer (a)).

**Deletable, imported by nothing outside ``features/bugs``.** ``specs/bugs/bugs.jsonl``
is still, at T-050-08, the LIVE ledger in its pre-canon-v6 shape: every historical line
is a :class:`~dadaia_workspace.core.models.bugs.BugEvent` (``reported``/``resolved``/
...), one event per physical line, many lines per bug id. FR2's record model
(:class:`~dadaia_workspace.core.models.bugs.BugRecord`) is one line per id — so until
FR3/T-050-10 physically rewrites the file (``bugs.jsonl`` -> ``BUGS.jsonl``, one record
per id, commit provenance derived from git history), :func:`read_ledger` is the ONE
place that decodes the v5 shape on the READ side: it folds every v5 event for a given
``bug_id`` into a single in-memory :class:`BugRecord`, exactly mirroring the semantics
the pre-T-050-08 ``BugService._fold``/``BugState`` used (a reopen — a later ``reported``
— replaces the immutable-core snapshot; the latest terminal event supplies ``status``;
``picked``/``archived`` annotations contribute nothing, per FR2: "the value, its
transition and picked_by all disappear").

**Deliberately minimal — no git, no cause-mining (T-050-08 scope).**
``registration_commit``/``resolved_commit``/``registration_granularity``/
``resolution_granularity``/``cause``/``caused_by``/``lineage_source`` all stay ``None``:
deriving them from git history (FR3, ``core/bug_provenance.py``) and mining ``cause``
from free prose are T-050-09/T-050-10's job, not this adapter's. The FR23 evidence
triple (``evidence_loop``/``evidence_seam``/``evidence_diff``) IS carried verbatim on a
terminal event — a direct 1:1 field copy, not an inference — because A2.11 requires it
"restored, not re-invented" and T-050-10's physical migration will copy the identical
value again from the identical source, so doing it here too is harmless.

**Ephemeral output — never round-tripped to disk.** A record this adapter folds may
carry a ``surface``/``component`` value that is NOT a member of
``bug-record-v1.schema.json``'s closed ``surface`` enum (the legacy free-text values a
v5 ``reported`` event carried, e.g. ``"gate"``, ``"dadaia certify"``); mapping legacy
free text onto the closed enum is FR3's "table in the migration module" (SPEC FR3 step
6d), not this task's. :func:`read_ledger`'s result is therefore a pure in-memory
rendering view for ``dadaia bugs status``/``stats``/``specs doctor`` — it is never
passed to :meth:`~dadaia_workspace.core.models.bugs.BugRecord.to_dict`/written back to
the ledger by anything in this module.

Deleted whole once T-050-10 rewrites the physical ledger to pure v6-record shape and
``features/bugs/service.py`` drops this import (D-F's "contract" step) — a contract
test (T-050-09, A3.10) then asserts no permanent module still imports it.
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path

from dadaia_workspace.core.models.bugs import (
    TERMINAL_EVENTS,
    BugEvent,
    BugEventKind,
    BugRecord,
)

__all__ = ["read_ledger"]

_LOG = logging.getLogger(__name__)


def read_ledger(path: Path) -> list[BugRecord]:
    """Read *path* (the live ``bugs.jsonl``) and return one :class:`BugRecord` per bug
    id, sorted by ``id``.

    Every physical line is classified by shape: a JSON object carrying an ``"event"``
    key is a v5 :class:`BugEvent` line (folded, see the module docstring); a JSON
    object with no ``"event"`` key is treated as an already-native v6
    :class:`BugRecord` line (parsed as-is — the shape a fresh ``dadaia bugs append``
    writes going forward, T-050-08's own "switch" half of D-F) and takes precedence
    over any v5-folded record sharing the same id, though the two should never collide
    in practice (a v5 id is retired the moment its v6 successor is registered).
    Malformed JSON, a non-object line, or a line failing BOTH shapes' required-field
    parse is skipped with a logged WARNING — one corrupt line never breaks the whole
    read (mirrors ``infrastructure.jsonl_record_store.JsonlRecordStore``'s own
    tolerance). Splits on ``"\\n"`` only, never ``str.splitlines()`` (T-045-20's root-cause
    fix, carried forward at every reader this release leaves standing). Absent file ->
    ``[]``.
    """
    if not path.is_file():
        return []
    v5_events: list[BugEvent] = []
    native_records: dict[str, BugRecord] = {}
    text = path.read_text(encoding="utf-8")
    for lineno, raw_line in enumerate(text.split("\n"), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            _LOG.warning("skipping malformed ledger line %s:%d: %s", path, lineno, exc)
            continue
        if not isinstance(raw, dict):
            _LOG.warning("skipping non-object ledger line %s:%d", path, lineno)
            continue
        if "event" in raw:
            try:
                v5_events.append(BugEvent.from_dict(raw))
            except (ValueError, TypeError) as exc:
                _LOG.warning("skipping invalid v5 bug-event line %s:%d: %s", path, lineno, exc)
            continue
        try:
            native_records[str(raw.get("id"))] = BugRecord.from_dict(raw)
        except (ValueError, TypeError) as exc:
            _LOG.warning("skipping invalid bug-record line %s:%d: %s", path, lineno, exc)

    folded = _fold_v5_events(v5_events)
    folded.update(native_records)
    return sorted(folded.values(), key=lambda record: record.id)


def _fold_v5_events(events: list[BugEvent]) -> dict[str, BugRecord]:
    """Fold a v5 event stream into one :class:`BugRecord` per ``bug_id`` (see module
    docstring for the exact semantics carried over from the pre-T-050-08 fold)."""
    records: dict[str, BugRecord] = {}
    for event in events:
        if event.event == BugEventKind.REPORTED.value:
            records[event.bug_id] = BugRecord(
                id=event.bug_id,
                ts=event.ts,
                reported_by=event.reported_by,
                title=event.title or "",
                severity=event.severity or "",
                surface=event.surface or "",
                component=event.component or "",
                context=event.context or "",
                symptom=event.symptom or "",
                repro=event.repro or "",
                expected=event.expected or "",
                status="open",
            )
            continue
        if event.event not in TERMINAL_EVENTS:
            continue  # `picked`/`archived`: contribute nothing to the record (FR2).
        current = records.get(event.bug_id)
        if current is None:
            # Terminal-without-reported is incoherent history (the doctor's own
            # SPEC-DOC-033 finding) — this adapter never synthesizes a phantom record
            # for it; there is nothing to fold onto.
            continue
        records[event.bug_id] = replace(
            current,
            status=event.event,
            superseded_by=event.superseded_by
            if event.event == BugEventKind.SUPERSEDED.value
            else current.superseded_by,
            evidence_loop=event.evidence_loop or current.evidence_loop,
            evidence_seam=event.evidence_seam or current.evidence_seam,
            evidence_diff=event.evidence_diff or current.evidence_diff,
        )
    return records
