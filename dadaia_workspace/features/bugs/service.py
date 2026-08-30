"""Bug-record service — the one write seam + read view over the bug ledger.

Every consumer (``dadaia bugs status``/``stats``/``update``/``resolve|supersede|defer|
reject``/``archive``, the CLI composition root) reads and writes through
:class:`BugService`, which holds the generic
:class:`~dadaia_workspace.infrastructure.jsonl_record_store.JsonlRecordStore` (DI seam
— the concrete store is built at the CLI composition root and injected here, so this
service never resolves a path itself; ADR-0001 retired the single-adapter
``RecordStore`` Protocol this used to type against — the concrete class IS the port
now, there being no second adapter to abstract over). :meth:`register` appends exactly one
:class:`~dadaia_workspace.core.models.bugs.BugRecord` line; :meth:`apply_update`
rewrites an existing record's governance fields (never ``status`` — refused by
:meth:`~dadaia_workspace.core.models.bugs.BugRecord.apply_governance_update` itself);
:meth:`transition` is the ONE seam a status change goes through.

**FR8's one resolver seam (AS-1).** :meth:`BugService.resolved_commit` is the SOLE
resolver for a record's ``resolved_commit``: the stored value when present, derived
from git history otherwise (DI'd in via ``history_reader``/``repo_root``, both
optional — most construction sites never need a git walk and the seam degrades to
"stored or ``None``").
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jsonschema.exceptions import ValidationError

from dadaia_workspace.core.bug_provenance import classify_ledger_line, derive_commit_provenance
from dadaia_workspace.core.models.bugs import (
    BUG_ARCHIVE_THRESHOLD_DAYS,
    TERMINAL_EVENTS,
    BugRecord,
)
from dadaia_workspace.core.redaction import PatternLike
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

__all__ = [
    "BugArchiveResult",
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
class BugArchiveResult:
    """A2.8 — the outcome of one ``dadaia bugs archive`` run."""

    archived: int
    kept: int


class BugService:
    """The one write seam (AS-16) plus the read view over the bug ledger."""

    def __init__(
        self,
        record_store: JsonlRecordStore[BugRecord],
        *,
        archive_store: JsonlRecordStore[BugRecord] | None = None,
        denylist_terms: Sequence[tuple[str, str]] = (),
        baseline_patterns: Sequence[PatternLike] = (),
        history_reader: GitSubprocessClient | None = None,
        repo_root: Path | None = None,
        validate: Callable[[Mapping[str, object]], None] | None = None,
    ) -> None:
        self._record_store = record_store
        self._archive_store = archive_store
        # The SAME operator-denylist source the push scan already refuses on, DI'd in
        # via the CLI/container seam (features-no-infrastructure) — threaded through
        # both write paths (append, update/transition, A2.6).
        self._denylist_terms = tuple(denylist_terms)
        # The SAME packaged baseline privacy patterns the push-range scan already
        # refuses on (container.load_denylist_baseline_patterns) — threaded through
        # every transition method's write-once free-text field(s), D5.
        self._baseline_patterns = tuple(baseline_patterns)
        # FR8/AS-1: the resolved_commit resolver's git-facing DI — both optional
        # (container.build_git_history_reader() wires the real adapter; most
        # construction sites never need it, see :meth:`resolved_commit`).
        self._history_reader = history_reader
        self._repo_root = repo_root
        # bug-record-v1.schema.json's validator (container.build_bug_record_validator)
        # — optional; wired at :meth:`register` only (a freshly registered record is
        # the one write this service builds from raw, Optional-typed CLI input).
        self._validate = validate

    # -- writes ----------------------------------------------------------------------

    def register(
        self,
        *,
        bug_id: str,
        ts: str,
        reported_by: str,
        title: str | None,
        severity: str | None,
        surface: str | None,
        component: str,
        context: str,
        symptom: str | None,
        repro: str | None,
        expected: str | None,
    ) -> None:
        """Append one NEW, freshly-registered :class:`BugRecord` (``status="open"``).

        Refuses (:class:`BugDuplicateIdError`) a *bug_id* already present anywhere in
        the ledger. When a ``validate`` callable was injected (the schema, D9), the
        raw payload is validated FIRST — a missing/mistyped/out-of-enum field raises
        ``ValueError`` before any :class:`BugRecord` is constructed. Redacts every
        free-text field through the same seam the update path uses (A2.6) before
        appending.
        """
        existing = {record.id for record in self._record_store.iter_records()}
        if bug_id in existing:
            raise BugDuplicateIdError(bug_id)
        payload: dict[str, object] = {
            "id": bug_id,
            "ts": ts,
            "reported_by": reported_by,
            "title": title,
            "severity": severity,
            "surface": surface,
            "component": component,
            "context": context,
            "symptom": symptom,
            "repro": repro,
            "expected": expected,
            "status": "open",
            "cause": None,
            "caused_by": None,
            "lineage_source": None,
            "registration_commit": None,
            "registration_granularity": None,
            "resolved_commit": None,
            "resolution_granularity": None,
            "resolved_release": None,
            "audited": None,
        }
        if self._validate is not None:
            try:
                self._validate(payload)
            except ValidationError as exc:
                raise ValueError(str(exc.message)) from exc
        record = BugRecord.from_dict(payload).redact(self._denylist_terms)
        self._record_store.append(record)

    def apply_update(self, record_id: str, changes: Mapping[str, object]) -> BugRecord:
        """The one governance-write seam for every governance/write-once field OTHER
        than ``status`` (refused by :meth:`~dadaia_workspace.core.models.bugs.BugRecord
        .apply_governance_update` itself): the auditor's ``audited``/
        ``resolved_commit`` rewrite and any other non-status governance write. Redacts
        the WHOLE resulting record (A2.6) before the store's refuse-stale atomic
        rewrite (A2.9, A2.2c)."""

        def _mutate(record: BugRecord) -> BugRecord:
            updated = record.apply_governance_update(changes)
            return updated.redact(self._denylist_terms)

        return self._record_store.update(record_id, _mutate)

    def transition(
        self, record_id: str, method: Callable[..., BugRecord], **fields: str
    ) -> BugRecord:
        """The ONE governance-write seam a STATUS change goes through: calls *method*
        (an unbound :class:`~dadaia_workspace.core.models.bugs.BugRecord` transition
        method — ``BugRecord.resolve``/``.supersede``/``.defer``/``.reject``, passed
        directly by the caller, never a second verb->method mapping) INSIDE the
        record-store's atomic update, threading the operator's baseline privacy
        patterns (D5) — exactly like :meth:`apply_update` already does for a bare
        governance-field change, so a refused transition
        (:class:`~dadaia_workspace.core.models.bugs.IncompleteTransitionError`) never
        reaches the file: ``mutate()`` runs BEFORE
        :meth:`~dadaia_workspace.infrastructure.jsonl_record_store.JsonlRecordStore.update`
        ever touches disk, leaving the record byte-identical on refusal.
        """

        def _mutate(record: BugRecord) -> BugRecord:
            updated = method(record, privacy_patterns=self._baseline_patterns, **fields)
            return updated.redact(self._denylist_terms)

        return self._record_store.update(record_id, _mutate)

    def archive(
        self, *, now: datetime | None = None, threshold_days: int = BUG_ARCHIVE_THRESHOLD_DAYS
    ) -> BugArchiveResult:
        """A2.8 — move every terminal record older than *threshold_days* from the live
        ledger to the archive store, through
        :meth:`~dadaia_workspace.infrastructure.jsonl_record_store.JsonlRecordStore.remove`
        (v0.5.0 S1 FR23 firing, A1) — the SAME refuse-stale seam :meth:`apply_update`
        already uses, never a second, unsealed raw-file rewrite. Idempotent: a second
        run with nothing newly eligible never touches either file (proven
        byte-identical by a fixture).
        """
        if self._archive_store is None:
            raise ValueError("BugService.archive() requires an archive_store")
        cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=threshold_days)
        all_records = list(self._record_store.iter_records())
        eligible_ids = {
            record.id
            for record in all_records
            if record.status in TERMINAL_EVENTS and _parse_ts(record.ts) < cutoff
        }
        if not eligible_ids:
            return BugArchiveResult(archived=0, kept=len(all_records))

        removed = self._record_store.remove(eligible_ids)
        for record in removed:
            self._archive_store.append(record)
        return BugArchiveResult(archived=len(removed), kept=len(all_records) - len(removed))

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
        :func:`~dadaia_workspace.core.bug_provenance.derive_commit_provenance`,
        classified through :func:`~dadaia_workspace.core.bug_provenance
        .classify_ledger_line` (permanent, S1 FR23 firing A2 — the walked history spans
        both shapes). It runs only when *record* has no stored value AND this service
        was constructed with both
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
            classify_ledger_line,
        )
        derived = provenance.get(record.id)
        return derived.resolved_commit if derived is not None else None

    def status(self, *, include_closed: bool = False) -> list[BugRecord]:
        """Return every ledger record, open-only by default, sorted by ``id``."""
        records = list(self._record_store.iter_records())
        selected = [r for r in records if include_closed or r.status == "open"]
        return sorted(selected, key=lambda r: r.id)

    def stats(self) -> BugStats:
        """Aggregate every ledger record by status and by severity."""
        records = list(self._record_store.iter_records())
        by_status: Counter[str] = Counter(r.status for r in records)
        by_severity: Counter[str] = Counter(r.severity for r in records if r.severity)
        return BugStats(
            total=len(records), by_status=dict(by_status), by_severity=dict(by_severity)
        )


def _parse_ts(value: str) -> datetime:
    """Parse a ``BugRecord.ts`` ISO-8601 UTC value; naive/unparseable -> epoch (never
    archived — a record whose age cannot be established is kept, never silently moved)."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.fromtimestamp(0, tz=UTC)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
