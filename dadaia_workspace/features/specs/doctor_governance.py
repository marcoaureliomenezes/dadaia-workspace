"""Governance validator: backlog single-source invariants, bug status/JSONL.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the bug/backlog governance
invariants: the bug-ledger
invariant (SPEC-DOC-033), the archive-overdue signal (SPEC-DOC-041), and the
single-source loose-file invariant (SPEC-DOC-035). Leaf-only: imports the shared leaves
+ core, plus one documented cross-feature leaf edge (``features.backlog.document`` —
``setup.cfg``'s ``features-no-cross-feature`` ``ignore_imports``), never a sibling
validator.

**The doctor reads ``BUGS.jsonl`` through the ONE store, never a second hand-kept
parser.** ``check_bugs_jsonl_invariant``/``check_bug_archive_overdue`` call
``self._bug_store_factory(self.specs_dir)`` — the SAME factory
``container.build_bug_record_store`` the CLI composition root wires everywhere else a
bug record is read or written (``cli/commands/specs.py``'s ``doctor`` command, mirroring
``cli/commands/bugs.py``). ``scan()``/``iter_records()`` are the store's own two read
methods (``infrastructure.jsonl_record_store.JsonlRecordStore``); the record-level
parsing is ``BugRecord.from_dict``, never a second, hand-rolled field check.

**Governance completeness is not diagnosed here.** Completeness is enforced
prospectively, at the WRITE seam (``core.models.bugs.BugRecord.resolve``/``supersede``/
``defer``/``reject``: status is unreachable without its own required fields), never
re-diagnosed against history — a historical record that reached an incomplete terminal
status before this seam existed is simply never re-checked.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dadaia_workspace.core.models.bugs import (
    BUG_ARCHIVE_THRESHOLD_DAYS,
    BugRecord,
)
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore, MalformedLine

# SPEC-DOC-035 (SPEC v0.12.0 FR5, ADR D5/D9): the single-source invariant — the only two
# filenames permitted loose directly under ``specs/backlog/``. Anything else (a per-entry
# item that survived the v0.12.0 consolidation, or was hand-authored outside `dadaia
# backlog new`) is drift.
_BACKLOG_SINGLE_SOURCE_FILES: frozenset[str] = frozenset({"BACKLOG.json", "AGENTS.md"})


def _parse_bug_record_ts(value: str) -> datetime | None:
    """Parse a ``BugRecord.ts`` ISO-8601 UTC value; ``None`` on anything unparseable
    (an unparseable timestamp is never treated as overdue — A2.8's own no-guess rule)."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class GovernanceValidator:
    """Bug/backlog governance: single-source backlog invariants, bug status/JSONL."""

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
        bug_store_factory: Callable[[Path], JsonlRecordStore[BugRecord]] | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir
        # DI seam: the composition root wires container.build_bug_record_store — the
        # SAME factory `cli.commands.bugs` already calls (`cli/commands/specs.py`'s
        # `doctor` command). Required whenever a bugs/BUGS.jsonl ledger is actually
        # read (`_bug_store` below); a construction site whose fixture never writes
        # one (most non-bugs doctor tests) never needs it.
        self._bug_store_factory = bug_store_factory

    def _bug_store(self) -> JsonlRecordStore[BugRecord]:
        if self._bug_store_factory is None:
            raise ValueError(
                "GovernanceValidator requires bug_store_factory to read "
                "bugs/BUGS.jsonl — wire container.build_bug_record_store "
                "(SpecsDoctor(bug_store_factory=...))"
            )
        return self._bug_store_factory(self.specs_dir)

    def check_bugs_jsonl_invariant(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-033: the single canonical ``specs/bugs/BUGS.jsonl`` ledger
        invariant. **Line validity** (ERROR) — each non-blank line must parse as a
        :class:`~dadaia_workspace.core.models.bugs.BugRecord` through
        :meth:`~dadaia_workspace.core.models.bugs.BugRecord.from_dict`, the model's
        OWN parser — never a hand-rolled field check. Every line
        :meth:`~dadaia_workspace.infrastructure.jsonl_record_store.JsonlRecordStore.scan` cannot
        parse surfaces as exactly ONE
        :class:`~dadaia_workspace.infrastructure.jsonl_record_store.MalformedLine` -> ONE ERROR here.

        **Governance completeness is not diagnosed here.** A well-formed record —
        however incomplete for its own status — is not re-checked: completeness is
        enforced prospectively, at the
        :meth:`~dadaia_workspace.core.models.bugs.BugRecord.resolve`/``supersede``/
        ``defer``/``reject`` write seam, never retroactively against history.

        Absent ``bugs/`` dir -> no-op.
        """
        ledger_path = self.specs_dir / "bugs" / "BUGS.jsonl"
        if not ledger_path.is_file():
            return []

        issues: list[SpecsDoctorIssue] = []
        for parsed in self._bug_store().scan():
            if not isinstance(parsed, MalformedLine):
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-033",
                    severity=Severity.ERROR,
                    description=(
                        f"bugs/BUGS.jsonl line {parsed.lineno}: {parsed.reason} — "
                        "every JSONL row must be one bug-record object "
                        "(SPEC-DOC-033, ERROR)."
                    ),
                    path=str(ledger_path),
                )
            )
        return issues

    def check_bug_archive_overdue(self, *, now: datetime | None = None) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-041 — WARN when a terminal :class:`BugRecord` CLOSED (``closed_at``,
        0.4.7 FR4 — never ``ts``, the filing date) longer ago than
        :data:`~dadaia_workspace.core.models.bugs.BUG_ARCHIVE_THRESHOLD_DAYS` and is
        still live (not yet moved by ``dadaia bugs archive``). Never a block; the
        exit code is unchanged. Absent ``bugs/`` dir -> no-op.
        """
        ledger_path = self.specs_dir / "bugs" / "BUGS.jsonl"
        if not ledger_path.is_file():
            return []
        cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=BUG_ARCHIVE_THRESHOLD_DAYS)
        issues: list[SpecsDoctorIssue] = []
        for record in self._bug_store().iter_records():
            if record.closed_at is None:
                continue
            closed_at = _parse_bug_record_ts(record.closed_at)
            if closed_at is not None and closed_at < cutoff:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-041",
                        severity=Severity.WARNING,
                        description=(
                            f"bugs/BUGS.jsonl record {record.id!r} has been terminal "
                            f"({record.status!r}) since {record.closed_at} — past the "
                            f"{BUG_ARCHIVE_THRESHOLD_DAYS}-day archive threshold; run "
                            "'dadaia bugs archive' (SPEC-DOC-041, WARNING — never a "
                            "block, D15)."
                        ),
                        path=str(ledger_path),
                    )
                )
        return issues

    def check_unarchived_terminal_backlog(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-035 (re-targeted, SPEC v0.12.0 FR5/ADR D5/D9): the single-source
        invariant — any ``*.md`` loose directly under ``specs/backlog/`` other than
        ``BACKLOG.md`` and ``README.md`` is drift → WARN.

        The physical model changed from "one file per backlog item" to "one document,
        ``BACKLOG.md``, with ``## ACTIVE`` + ``## LEDGER``" (ADR #14); a loose per-entry
        file is now itself the drift signal, regardless of any status text it carries —
        either a stray survivor of the v0.12.0 consolidation, or a file hand-authored
        outside ``dadaia backlog new``. ``specs/backlog/_archive/`` is excluded
        (non-recursive glob already skips it — it is a subdirectory, not a
        ``*.md`` sibling).
        """
        backlog_dir = self.specs_dir / "backlog"
        if not backlog_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for entry in sorted(backlog_dir.glob("*.md")):
            if entry.name in _BACKLOG_SINGLE_SOURCE_FILES:
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-035",
                    severity=Severity.WARNING,
                    description=(
                        f"backlog/{entry.name} is a loose per-entry file directly under "
                        "specs/backlog/ — the single source is BACKLOG.json (## ACTIVE + "
                        "## LEDGER); fold it into BACKLOG.json and move the superseded "
                        "file into specs/backlog/_archive/ (SPEC-DOC-035, WARNING)."
                    ),
                    path=str(entry),
                )
            )
        return issues
