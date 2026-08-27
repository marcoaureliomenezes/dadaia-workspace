"""Bug-record service — the one write seam + read view over the bug ledger (v0.5.0 FR2).

D-F "switch": every consumer (``dadaia bugs status``/``stats``/``update``/``archive``,
the CLI composition root) now reads and writes through :class:`BugService`, which holds
the generic :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` (DI seam
— the concrete ``JsonlRecordStore`` is injected at the CLI composition root, so
``features`` never imports ``infrastructure``). The event fold (``BugEvent``'s
``advance_coherence`` state machine) is retired from the WRITE side entirely —
:meth:`register` appends exactly one :class:`~dadaia_workspace.core.models.bugs.BugRecord`
line, never an event; :meth:`apply_update` rewrites an existing record's governance
fields in place through the SAME seam (AS-16 — the fixer's resolve and the auditor's
``audited``/``resolved_commit`` write both go through this one method, A2.13).

**The live ledger is ``specs/bugs/BUGS.jsonl`` (T-050-10 physically migrated it).**
Every historical v5 event stream is now one native v6 :class:`BugRecord` line per bug
id, with ``registration_commit``/``resolved_commit`` derived from git history (FR3).
Every READ method here still goes through
:func:`~dadaia_workspace.features.bugs.migrate_v5.read_ledger` (A2.5) — it now decodes
the (all-native) v6 shape only, but keeps its v5-tolerant path so a workspace mid-way
through the migration, or a foreign write, never crashes the read. :meth:`archive`
moves a single PHYSICAL line per record — every migrated record is single-line
native v6 shape and is therefore archivable.

**FR8's one resolver seam (AS-1, v0.5.0 T-050-17).** :meth:`BugService.resolved_commit`
is the SOLE resolver for a record's ``resolved_commit``: the stored value when present,
derived from git history otherwise — one function, one caller-facing signature (A8.2).
``resolved_commit`` stays ``null`` at resolve time by construction (a commit cannot
contain its own sha); the field is a cache, and its ONE writer is FR14's pillar-1 audit,
in the same atomic in-place rewrite that sets ``audited`` (a later task) — never this
read-only seam, never a second commit. Derivation needs a real git walk, so it is
DI'd in via the constructor (``history_reader``/``repo_root``, both optional): most
``BugService`` construction sites (every ``append``, every plain ``status``/``stats``
read) never pass them and the seam degrades to "stored or ``None``", never raising and
never adding a blocking validation (A8.3).
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.bug_provenance import derive_commit_provenance
from dadaia_workspace.core.models.bugs import (
    BUG_ARCHIVE_THRESHOLD_DAYS,
    TERMINAL_EVENTS,
    BugRecord,
    governance_completeness_gaps,
)
from dadaia_workspace.core.protocols.git_history_reader import GitHistoryReader
from dadaia_workspace.core.protocols.record_store import RecordStore
from dadaia_workspace.features.bugs import migrate_v5

__all__ = [
    "BugArchiveResult",
    "BugCoherenceGap",
    "BugDuplicateIdError",
    "BugService",
    "BugStats",
]

_LOG = logging.getLogger(__name__)


class BugDuplicateIdError(ValueError):
    """Raised by :meth:`BugService.register` when *id* already exists in the ledger.

    v0.5.0 FR2: "a reopen is a new record with a new id declaring ``caused_by:
    <prior-id>``" — reusing an existing id would silently duplicate a line (the record
    store is keyed by ``id``, A13.4/A2.5) rather than express a reopen the model's own
    way, so registration refuses it up front rather than corrupting the ledger.
    """

    def __init__(self, bug_id: str) -> None:
        super().__init__(
            f"bug id {bug_id!r} already exists in the ledger — a reopen is a NEW record "
            "declaring 'caused_by: <prior-id>' via 'dadaia bugs append', never a second "
            "'reported' under the same id (v0.5.0 FR2)"
        )
        self.bug_id = bug_id


@dataclass(frozen=True)
class BugStats:
    """Aggregate counts across every folded record (open + terminal)."""

    total: int
    by_status: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class BugCoherenceGap:
    """A2.3 — one record whose governance fields are incomplete for its own ``status``."""

    bug_id: str
    status: str
    missing: tuple[str, ...]


@dataclass(frozen=True)
class BugArchiveResult:
    """A2.8 — the outcome of one ``dadaia bugs archive`` run."""

    archived: int
    kept: int


class BugService:
    """The one write seam (AS-16) plus the read view over the bug ledger."""

    def __init__(
        self,
        record_store: RecordStore[BugRecord],
        *,
        archive_store: RecordStore[BugRecord] | None = None,
        denylist_terms: Sequence[tuple[str, str]] = (),
        history_reader: GitHistoryReader | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self._record_store = record_store
        self._archive_store = archive_store
        # v0.4.5 FR6: the SAME operator-denylist source the push scan already refuses
        # on, DI'd in via the CLI/container seam (features-no-infrastructure) —
        # threaded through BOTH write paths (append, A2.6).
        self._denylist_terms = tuple(denylist_terms)
        # v0.5.0 FR8/AS-1 (T-050-17): the resolved_commit resolver's git-facing DI —
        # both optional (container.build_git_history_reader() wires the real adapter;
        # most construction sites never need it, see :meth:`resolved_commit`).
        self._history_reader = history_reader
        self._repo_root = repo_root

    # -- writes ----------------------------------------------------------------------

    def register(
        self,
        *,
        bug_id: str,
        ts: str,
        reported_by: str,
        title: str,
        severity: str,
        surface: str,
        component: str,
        context: str,
        symptom: str,
        repro: str,
        expected: str,
    ) -> Path:
        """Append one NEW, freshly-registered :class:`BugRecord` (``status="open"``).

        Refuses (:class:`BugDuplicateIdError`) an *bug_id* already present anywhere in
        the ledger (v5-folded history included, via :func:`migrate_v5.read_ledger`).
        Redacts every free-text field through the same seam the update path uses
        (A2.6) before appending. Returns the ledger path.
        """
        existing = {record.id for record in migrate_v5.read_ledger(self._record_store.path)}
        if bug_id in existing:
            raise BugDuplicateIdError(bug_id)
        record = BugRecord(
            id=bug_id,
            ts=ts,
            reported_by=reported_by,
            title=title,
            severity=severity,
            surface=surface,
            component=component,
            context=context,
            symptom=symptom,
            repro=repro,
            expected=expected,
            status="open",
        ).redact(self._denylist_terms)
        self._record_store.append(record)
        return self._record_store.path

    def apply_update(self, record_id: str, changes: Mapping[str, object]) -> BugRecord:
        """The one governance-write seam (AS-16/A2.13): registration's resolve, the
        fixer's resolve, and the auditor's ``audited``/``resolved_commit`` rewrite all
        call this same method. Delegates structural refusal (immutable-core changed,
        write-once field re-set with a differing value, unknown field) to
        :meth:`BugRecord.apply_governance_update` (A2.2), then redacts the WHOLE
        resulting record (A2.6 — identical posture to :meth:`register`) before the
        store's refuse-stale atomic rewrite (A2.9, A2.2c)."""

        def _mutate(record: BugRecord) -> BugRecord:
            updated = record.apply_governance_update(changes)
            return updated.redact(self._denylist_terms)

        return self._record_store.update(record_id, _mutate)

    def archive(
        self, *, now: datetime | None = None, threshold_days: int = BUG_ARCHIVE_THRESHOLD_DAYS
    ) -> BugArchiveResult:
        """A2.8 — move every NATIVE (v6-shaped) terminal record older than
        *threshold_days* from the live ledger to the archive store, through the same
        record-store seam. Idempotent: a second run with nothing newly eligible never
        touches either file (proven byte-identical by a fixture).

        Only records already in native v6 shape are eligible — a v5-folded record has
        no single physical line to move (see module docstring); T-050-10's physical
        migration is what makes every historical record archivable.
        """
        if self._archive_store is None:
            raise ValueError("BugService.archive() requires an archive_store")
        live_path = self._record_store.path
        if not live_path.is_file():
            return BugArchiveResult(archived=0, kept=0)
        cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=threshold_days)
        eligible_ids = {
            record.id
            for record in self._record_store.iter_records()
            if record.status in TERMINAL_EVENTS and _parse_ts(record.ts) < cutoff
        }
        text = live_path.read_text(encoding="utf-8")
        if not eligible_ids:
            kept = sum(1 for line in text.split("\n") if line.strip())
            return BugArchiveResult(archived=0, kept=kept)

        kept_lines: list[str] = []
        to_archive: list[BugRecord] = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            record_id = _line_record_id(stripped)
            if record_id in eligible_ids:
                to_archive.append(BugRecord.from_dict(json.loads(stripped)))
            else:
                kept_lines.append(line)

        for record in to_archive:
            self._archive_store.append(record)
        new_content = "".join(f"{line}\n" for line in kept_lines)
        atomic_write(live_path, new_content, newline="")
        return BugArchiveResult(archived=len(to_archive), kept=len(kept_lines))

    # -- reads -------------------------------------------------------------------------

    def resolved_commit(self, record: BugRecord) -> str | None:
        """FR8's one resolver seam (AS-1, A8.2) — the stored value when present,
        derived from real git history otherwise. One function, one caller-facing
        signature: the SAME method a read-only display (a future ``bugs status``/
        ``stats`` renderer) and this release's stored-equals-derived contract test
        both call.

        **Read-only.** Never writes ``resolved_commit`` back to the ledger — the
        field stays a cache by construction (a commit cannot contain its own sha) and
        its ONE writer is FR14's pillar-1 audit, in the same atomic in-place rewrite
        that sets ``audited`` (a later task; not this seam, not a second commit).

        Derivation needs a real git walk over ``specs/bugs/`` through
        :func:`~dadaia_workspace.core.bug_provenance.derive_commit_provenance`
        (``core/bug_provenance.py`` — the permanent half of FR3's split, A3.10),
        classified through :func:`~dadaia_workspace.features.bugs.migrate_v5
        .classify_ledger_line` (the SAME v5/v6 boundary adapter T-050-09/10 already
        use — the walked history spans both shapes). It runs only when *record* has
        no stored value AND this service was constructed with both
        ``history_reader``/``repo_root`` — most construction sites (every ``append``,
        a plain read with no derivation need) pass neither, and this method degrades
        to "stored or ``None``", never raising and never a new blocking validation
        (A8.3).

        Returns ``None`` for an open bug, for a resolved bug whose commit the walked
        history never captured (FR3 step 5 — ``null`` is correct there, not a
        failure, A8.2), and whenever derivation is unavailable.
        """
        if record.resolved_commit is not None:
            return record.resolved_commit
        if self._history_reader is None or self._repo_root is None:
            return None
        provenance = derive_commit_provenance(
            self._history_reader.log_added_lines(self._repo_root, "specs/bugs/"),
            migrate_v5.classify_ledger_line,
        )
        derived = provenance.get(record.id)
        return derived.resolved_commit if derived is not None else None

    def status(self, *, include_closed: bool = False) -> list[BugRecord]:
        """Return folded records, open-only by default, sorted by ``id``."""
        records = migrate_v5.read_ledger(self._record_store.path)
        selected = [r for r in records if include_closed or r.status == "open"]
        return sorted(selected, key=lambda r: r.id)

    def stats(self) -> BugStats:
        """Aggregate every folded record by status and by severity."""
        records = migrate_v5.read_ledger(self._record_store.path)
        by_status: Counter[str] = Counter(r.status for r in records)
        by_severity: Counter[str] = Counter(r.severity for r in records if r.severity)
        return BugStats(
            total=len(records), by_status=dict(by_status), by_severity=dict(by_severity)
        )

    def coherence_violations(self) -> list[BugCoherenceGap]:
        """A2.3 — every record whose governance fields are incomplete for its own
        ``status``, sorted by ``id``. Never blocks (D15); the caller renders these as a
        WARNING."""
        records = migrate_v5.read_ledger(self._record_store.path)
        gaps = [
            BugCoherenceGap(bug_id=record.id, status=record.status, missing=missing)
            for record in records
            if (missing := governance_completeness_gaps(record))
        ]
        return sorted(gaps, key=lambda gap: gap.bug_id)


def _parse_ts(value: str) -> datetime:
    """Parse a ``BugRecord.ts`` ISO-8601 UTC value; naive/unparseable -> epoch (never
    archived — a record whose age cannot be established is kept, never silently moved)."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.fromtimestamp(0, tz=UTC)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _line_record_id(stripped_line: str) -> str | None:
    """Best-effort ``"id"`` extraction from one physical JSONL line, for the archive
    rewrite's line-matching pass only — a malformed line yields ``None`` and is always
    KEPT (never silently dropped by archive)."""
    try:
        raw = json.loads(stripped_line)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    record_id = raw.get("id")
    return record_id if isinstance(record_id, str) else None
