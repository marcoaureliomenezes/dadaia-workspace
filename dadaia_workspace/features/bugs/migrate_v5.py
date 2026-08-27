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

**T-050-09 extends this module with the pieces FR3 names as "the migration module"'s
own job (A2.5), still never the pure derivation itself.** :func:`classify_ledger_line`
is the boundary adapter :func:`~dadaia_workspace.core.bug_provenance
.derive_commit_provenance` is injected with (the v5/v6 shape decoding stays here, never
migrates into ``core``); :data:`LEGACY_SURFACE_MAP`/:func:`map_legacy_surface` are FR3
step 6d's "table in the migration module"; :func:`run_migration` is the one-shot runner
**scaffolding** that composes a caller-supplied
:class:`~dadaia_workspace.core.protocols.git_history_reader.GitHistoryReader` with the
two above. All four die with this module at 0.6.0, same as :func:`read_ledger` — their
tests are marked ``Intent: SCAFFOLD — T-050-09 — expires: 0.6.0`` (qa-engineer amendment
10), distinct from ``core/bug_provenance.py``'s own ``CONTRACT`` tests, which outlive
this module.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from dataclasses import replace
from pathlib import Path

from dadaia_workspace.core.bug_provenance import (
    ClassifiedLedgerLine,
    DerivedBugProvenance,
    LedgerLineKind,
    derive_commit_provenance,
)
from dadaia_workspace.core.models.bugs import (
    TERMINAL_EVENTS,
    BugEvent,
    BugEventKind,
    BugRecord,
)
from dadaia_workspace.core.protocols.git_history_reader import GitHistoryReader

__all__ = [
    "LEGACY_SURFACE_MAP",
    "classify_ledger_line",
    "map_legacy_surface",
    "read_ledger",
    "run_migration",
]

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


def classify_ledger_line(raw_line: str) -> ClassifiedLedgerLine | None:
    """FR3 step 2's "boundary adapter" (A2.5) — classify ONE added ledger line as a
    registration or a terminal line for its bug id, or ``None`` when the line is
    neither (malformed JSON, a non-object, a ``picked``/``archived`` v5 event, or a v6
    record whose ``status`` this function does not recognise).

    THE one place that decodes the v5/v6 shape for :mod:`core.bug_provenance`'s pure
    derivation (:func:`~dadaia_workspace.core.bug_provenance.derive_commit_provenance`
    takes this as its injected ``classify_line`` callable — the module boundary A3.10
    exists to keep the derivation itself free of this decoding). Understands BOTH
    shapes :func:`read_ledger` already understands, by the SAME ``"event" in raw``
    discriminator: a v5 :class:`~dadaia_workspace.core.models.bugs.BugEvent` line
    (``reported`` -> registration, one of :data:`TERMINAL_EVENTS` -> terminal,
    ``picked``/``archived`` -> ``None``, FR2's "contributes nothing"), or a v6
    :class:`~dadaia_workspace.core.models.bugs.BugRecord` line (``status == "open"`` ->
    registration, ``status`` in :data:`TERMINAL_EVENTS` -> terminal, anything else ->
    ``None``).
    """
    try:
        raw = json.loads(raw_line)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    if "event" in raw:
        bug_id = raw.get("bug_id")
        event = raw.get("event")
        if not isinstance(bug_id, str) or not bug_id:
            return None
        if event == BugEventKind.REPORTED.value:
            return ClassifiedLedgerLine(bug_id=bug_id, kind=LedgerLineKind.REGISTRATION)
        if event in TERMINAL_EVENTS:
            return ClassifiedLedgerLine(bug_id=bug_id, kind=LedgerLineKind.TERMINAL)
        return None  # `picked`/`archived` — contribute nothing (FR2).
    bug_id = raw.get("id")
    status = raw.get("status")
    if not isinstance(bug_id, str) or not bug_id:
        return None
    if status == "open":
        return ClassifiedLedgerLine(bug_id=bug_id, kind=LedgerLineKind.REGISTRATION)
    if isinstance(status, str) and status in TERMINAL_EVENTS:
        return ClassifiedLedgerLine(bug_id=bug_id, kind=LedgerLineKind.TERMINAL)
    return None


#: Legacy free-text ``surface``/``component`` values observed on a v5 ``reported``
#: event, mapped onto ``bug-record-v1.schema.json``'s closed ``surface`` enum (FR3 step
#: 6d, SA-Q5: "the enum derives from the feature-package list the independence contract
#: uses ... the forensic's normalizer becomes FR3's legacy mapping table"). Deliberately
#: NOT exhaustive here — enumerating every historical string requires scanning the REAL
#: corpus, which T-050-10's actual migration run does and this task explicitly does not
#: (this task never runs against the real ledger); this table seeds the two example
#: strings this module's own docstring already named (``"gate"``, ``"dadaia certify"``)
#: as the mapping MECHANISM's proof, and T-050-10 extends it with every unmapped string
#: its migration report finds. One row per legacy string, exact match, case-sensitive —
#: no fuzzy/guessed mapping (FR3: "nothing is guessed and nothing is dropped").
LEGACY_SURFACE_MAP: Mapping[str, str] = {
    "gate": "chokepoints",
    "dadaia certify": "certification",
}


def map_legacy_surface(
    raw_surface: str, canonical_surfaces: AbstractSet[str]
) -> tuple[str, str | None]:
    """Map one legacy free-text ``surface`` value onto the closed enum.

    *canonical_surfaces* is the caller-supplied enum member set (T-050-29 is the task
    that publishes the single Python-side source for it, per A2.12's "one source, two
    consumers" rule — this module does not hardcode a second, independently-maintained
    copy of that 30-member list; it takes the set as a parameter, exactly like
    :func:`derive_commit_provenance` takes its classifier). Returns
    ``(mapped_surface, original_if_unmapped)``: when *raw_surface* is already a
    canonical member, or :data:`LEGACY_SURFACE_MAP` maps it onto one, the pair is
    ``(surface, None)``; otherwise the pair is ``("unknown", raw_surface)`` — the
    original is preserved (never dropped) for the migration report's ``unknown`` list
    (FR3 step 6d, A3.11).
    """
    mapped = LEGACY_SURFACE_MAP.get(raw_surface, raw_surface)
    if mapped in canonical_surfaces:
        return mapped, None
    return "unknown", raw_surface


def run_migration(
    repo: Path,
    pathspec: str,
    history_reader: GitHistoryReader,
) -> dict[str, DerivedBugProvenance]:
    """The one-shot runner **scaffolding** (T-050-09) — composes an injected
    :class:`~dadaia_workspace.core.protocols.git_history_reader.GitHistoryReader` with
    :func:`classify_ledger_line` and
    :func:`~dadaia_workspace.core.bug_provenance.derive_commit_provenance` to derive
    every bug id's commit provenance from *repo*'s real history over *pathspec*.

    **Scaffolding, not the migration.** This function performs no ledger write, no
    report, no CLI wiring — T-050-10 is the task that runs the full FR3 migration
    (rewrites ``bugs.jsonl`` -> ``BUGS.jsonl``, writes the migration report, wires a CLI
    verb) and it is EXPECTED to call something shaped like this, but this task never
    invokes it against the real ``specs/bugs/`` history (per its own instructions) —
    only fixture tests, with a fake :class:`GitHistoryReader`, exercise it. No
    ``infrastructure``/``subprocess`` import here: *history_reader* arrives already
    constructed (``container.build_git_history_reader()`` in production), matching
    `features-no-infrastructure`/`features-no-subprocess` — this module never imports
    either directly, even for its own runner.
    """
    commits = history_reader.log_added_lines(repo, pathspec)
    return derive_commit_provenance(commits, classify_ledger_line)
