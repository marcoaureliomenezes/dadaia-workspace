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

**One fixer, one canonical shape (0.4.7 FR1).** :meth:`normalize_records` rewrites
every committed record of the ledger AND the histo into the shape
:meth:`~dadaia_workspace.core.models.bugs.BugRecord.to_dict` emits today — that is how
the seven retired derived-provenance keys leave 541 committed records, and how a
terminal record that predates the ``closed_at`` invariant is stamped. No git walk is
involved in either: the derived cache this service used to resolve from history is
deleted, cache and walk together.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jsonschema.exceptions import ValidationError

from dadaia_workspace.core.atomic_write import ConcurrentModificationError, atomic_write
from dadaia_workspace.core.models.bugs import (
    BUG_ARCHIVE_THRESHOLD_DAYS,
    TERMINAL_EVENTS,
    BugRecord,
)
from dadaia_workspace.core.redaction import PatternLike
from dadaia_workspace.infrastructure.jsonl_record_store import (
    JsonlRecordStore,
    StaleRecordWriteError,
)

__all__ = [
    "BugArchiveResult",
    "BugDuplicateIdError",
    "BugService",
    "BugStats",
    "normalize_component",
]

_LOG = logging.getLogger(__name__)

#: The ``surface`` value a NEW registration may never choose (0.4.7 FR1): it exists so
#: the 268 records whose feature could not be mapped stay valid, not as an escape hatch.
_LEGACY_SURFACE = "unknown"

#: The literal a fixer passes to ``--caused-by`` when this bug has no prior cause —
#: the one word that is NOT looked up in the ledger.
_NO_LINEAGE = "none"


_DOTTED_MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$")


def normalize_component(value: str, *, repo_root: Path | None = None) -> str:
    """Canonicalize a bug record's ``component`` toward ``path#symbol`` (F017).

    Conservative and NEVER raising (the bugs lane is ADDITIVE — registration must
    never block): a path-shaped or dotted-module value is normalized to the on-disk
    repo-relative form (backslashes -> ``/``, dots -> ``/``, ``.py`` and the
    ``dadaia_workspace/`` prefix added when that file actually exists under
    *repo_root*); anything else (free text) passes through stripped. The 539-record
    ledger held 3+ spellings of the same file — this seam is where spellings converge.
    """
    text = value.strip()
    if not text:
        return ""
    path_part, sep, symbol = text.partition("#")
    path_part = path_part.strip().replace("\\", "/")
    if any(ch in path_part for ch in " |()"):
        return text  # free text — tolerated untouched (beyond the strip)
    if "/" not in path_part and _DOTTED_MODULE_RE.match(path_part):
        path_part = path_part.replace(".", "/")
    if repo_root is not None:
        for candidate in (
            path_part,
            f"{path_part}.py",
            f"dadaia_workspace/{path_part}",
            f"dadaia_workspace/{path_part}.py",
        ):
            if (repo_root / candidate).is_file():
                path_part = candidate
                break
    return f"{path_part}#{symbol}" if sep else path_part


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
    """A2.8 — the outcome of one ``dadaia bugs archive`` run. Carries the records it
    MOVED, not just how many: the caller writes one governance event per moved record
    (0.4.7 FR2), and the count is derived from them rather than reported beside them."""

    records: tuple[BugRecord, ...] = ()
    kept: int = 0

    @property
    def archived(self) -> int:
        return len(self.records)


class BugService:
    """The one write seam (AS-16) plus the read view over the bug ledger."""

    def __init__(
        self,
        record_store: JsonlRecordStore[BugRecord],
        *,
        archive_store: JsonlRecordStore[BugRecord] | None = None,
        denylist_terms: Sequence[tuple[str, str]] = (),
        baseline_patterns: Sequence[PatternLike] = (),
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
        # The component normalizer probes the containing repo for the on-disk spelling.
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
    ) -> BugRecord:
        """Append one NEW, freshly-registered :class:`BugRecord` (``status="open"``).

        Refuses (:class:`BugDuplicateIdError`) a *bug_id* already present anywhere in
        the ledger. When a ``validate`` callable was injected (the schema, D9), the
        Returns the appended record (the caller's governance event hashes it). The
        raw payload is validated FIRST — a missing/mistyped/out-of-enum field raises
        ``ValueError`` before any :class:`BugRecord` is constructed. Redacts every
        free-text field through the same seam the update path uses (A2.6) before
        appending.
        """
        if surface == _LEGACY_SURFACE:
            raise ValueError(
                f"surface {_LEGACY_SURFACE!r} is a legacy sentinel, valid only on the records "
                "that already carry it; fix: pass the feature package or non-feature layer "
                "this bug lives in (dadaia bugs append --help lists them)"
            )
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
            "component": normalize_component(component, repo_root=self._repo_root),
            "context": context,
            "symptom": symptom,
            "repro": repro,
            "expected": expected,
            "status": "open",
            "cause": None,
            "caused_by": None,
            "resolved_release": None,
            "audited": None,
            "closed_at": None,
        }
        if self._validate is not None:
            try:
                self._validate(payload)
            except ValidationError as exc:
                raise ValueError(str(exc.message)) from exc
        record = BugRecord.from_dict(payload).redact(self._denylist_terms)
        self._record_store.append(record)
        return record

    def apply_update(self, record_id: str, changes: Mapping[str, object]) -> BugRecord:
        """The one governance-write seam for every governance/write-once field OTHER
        than ``status`` (refused by :meth:`~dadaia_workspace.core.models.bugs.BugRecord
        .apply_governance_update` itself): the auditor's ``audited`` rewrite and any
        other non-status governance write. Redacts
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

        self._validate_caused_by(fields.get("caused_by"))

        def _mutate(record: BugRecord) -> BugRecord:
            updated = method(record, privacy_patterns=self._baseline_patterns, **fields)
            return updated.redact(self._denylist_terms)

        return self._record_store.update(record_id, _mutate)

    def _validate_caused_by(self, caused_by: str | None) -> None:
        """Lineage is declared at ``resolve`` and nowhere else (0.4.7 FR1), so this is
        the ONE place it is checked: ``caused_by`` names a record of this ledger (live
        or archived) or the literal ``none``. An unvalidated free-text lineage field is
        how a second, unreadable lineage home grew."""
        if caused_by is None or caused_by == _NO_LINEAGE:
            return
        known = {record.id for record in self._record_store.iter_records()}
        if self._archive_store is not None:
            known |= {record.id for record in self._archive_store.iter_records()}
        if caused_by not in known:
            raise ValueError(
                f"caused_by {caused_by!r} is not a record of this bug ledger "
                f"({self._record_store.path.name}); fix: pass an existing bug id or "
                f"the literal '{_NO_LINEAGE}'"
            )

    def archive(
        self, *, now: datetime | None = None, threshold_days: int = BUG_ARCHIVE_THRESHOLD_DAYS
    ) -> BugArchiveResult:
        """A2.8 — move every record CLOSED more than *threshold_days* ago from the
        live ledger to the archive store. Ageing is by ``closed_at`` (0.4.7 FR4):
        ``ts`` is the FILING date, so a bug filed long ago and closed yesterday used
        to be archivable the day it closed. ``closed_at`` is non-null iff the status
        is terminal, so the status test IS the closed_at test — one condition, not two, through
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
            if record.closed_at is not None and _parse_ts(record.closed_at) < cutoff
        }
        if not eligible_ids:
            return BugArchiveResult(kept=len(all_records))

        removed = self._record_store.remove(eligible_ids)
        for record in removed:
            self._archive_store.append(record)
        return BugArchiveResult(records=tuple(removed), kept=len(all_records) - len(removed))

    def normalize_records(self) -> int:
        """Rewrite every committed record of the ledger and the histo into its canonical
        ``bug-record-v1`` shape, returning how many lines changed — the ONE fixer
        ``LEDGER-BUGS-SCHEMA`` runs (0.4.7 FR1).

        Two classes of drift, one pass, because both are "this line is not what
        :meth:`BugRecord.to_dict` emits today":

        * the seven retired derived-provenance keys (``lineage_source``,
          ``registration_commit``/``_granularity``, ``resolved_commit``/
          ``resolution_granularity``, ``root_cause``, ``migration_note``) — a
          git-derived CACHE :meth:`BugRecord.from_dict` now ignores, so re-serializing
          strips them losslessly;
        * a terminal record carrying no ``closed_at`` — the invariant 0.4.7 candidate 1
          shipped without (bug
          ``bugs-update-cannot-heal-terminal-record-missing-closed-at``). The stamp is
          the record's OWN filing date ``ts``, and nothing else: the ledger's git
          history is NOT consulted, the walk that used to date the terminal line having
          been deleted with the cache. ``ts`` is the honest floor — never a date later
          than the truth, and the one bound ``__post_init__`` enforces anyway.

        Runs on RAW lines because an unconstructible record is exactly what it repairs;
        a line it cannot parse is preserved verbatim rather than dropped. Costs nothing
        when there is nothing to do — that is load-bearing, the doctor calling a fixer
        once per reported issue.
        """
        stores = [self._record_store]
        if self._archive_store is not None:
            stores.append(self._archive_store)
        return sum(self._normalize_file(store.path) for store in stores)

    def _normalize_file(self, path: Path) -> int:
        if not path.is_file():
            return 0
        before = path.read_text(encoding="utf-8")
        lines = before.split("\n")
        changed = 0
        for index, line in enumerate(lines):
            canonical = _canonical_line(line)
            if canonical is not None and canonical != line.strip():
                lines[index] = canonical
                changed += 1
        if not changed:
            return 0
        try:
            atomic_write(path, "\n".join(lines), newline="", expected_previous=before)
        except ConcurrentModificationError as exc:
            raise StaleRecordWriteError(path.name) from exc
        return changed

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


def _canonical_line(line: str) -> str | None:
    """The canonical serialization of the record *line* holds — ``None`` when the line
    is blank or this fixer cannot read it (preserved verbatim, never dropped).

    The ``closed_at`` stamp happens on the RAW mapping, before construction, precisely
    because the model refuses to construct a terminal record without it.
    """
    stripped = line.strip()
    if not stripped:
        return None
    try:
        raw = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    if (
        raw.get("status") in TERMINAL_EVENTS
        and raw.get("closed_at") is None
        and isinstance(raw.get("ts"), str)
    ):
        raw["closed_at"] = raw["ts"]
    try:
        record = BugRecord.from_dict(raw)
    except (TypeError, ValueError):
        return None
    return json.dumps(record.to_dict(), sort_keys=True, ensure_ascii=False)
