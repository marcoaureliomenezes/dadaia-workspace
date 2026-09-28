"""Governance validator: backlog single-source invariants, bug archive age.

Single-responsibility sibling of the SpecsDoctor coordinator: the archive-overdue signal
(SPEC-DOC-041), the bug ids SPEC-DOC-048 cites, and the single-source loose-file
invariant (SPEC-DOC-035). Leaf-only: imports the shared leaves + core, never a sibling
validator.

**Whether a bug record is valid is not asked here.** `bugs.py check` is the one
validator (the doctor re-emits it as LEDGER-BUGS-SCHEMA); this module reads raw JSON
lines and skips any it cannot read.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

# SPEC-DOC-035 (SPEC v0.12.0 FR5, ADR D5/D9): the single-source invariant — the only two
# filenames permitted loose directly under ``specs/backlog/``. Anything else (a per-entry
# item that survived the v0.12.0 consolidation, or was hand-authored outside `dadaia
# backlog new`) is drift.
_BACKLOG_SINGLE_SOURCE_FILES: frozenset[str] = frozenset({"BACKLOG.json", "AGENTS.md"})

#: `bugs.py archive`'s own default ``--threshold-days``.
_ARCHIVE_THRESHOLD_DAYS = 90


def _parse_ts(value: str) -> datetime | None:
    """An ISO-8601 UTC value, or ``None`` when unparseable (never treated as overdue)."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class GovernanceValidator:
    """Bug/backlog governance: single-source backlog invariants, bug archive age."""

    def __init__(self, specs_dir: Path, public_dir: Path | None = None) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir
        self._ledger = specs_dir / "bugs" / "BUGS.jsonl"

    def _bug_lines(self) -> Iterator[dict[str, Any]]:
        """Every ledger line that is a JSON object; the rest is `bugs.py check`'s."""
        if not self._ledger.is_file():
            return
        for raw in self._ledger.read_text(encoding="utf-8").split("\n"):
            try:
                record = json.loads(raw)
            except ValueError:
                continue
            if isinstance(record, dict):
                yield record

    def known_bug_ids(self) -> frozenset[str]:
        """The id of every line, whatever its status or validity — SPEC-DOC-048 judges
        membership in the ledger, never liveness."""
        return frozenset(str(r["id"]) for r in self._bug_lines() if "id" in r)

    def check_bug_archive_overdue(self, *, now: datetime | None = None) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-041 — WARN when a record closed (``closed_at``, never the filing date
        ``ts``) longer ago than the archive threshold is still live. Never a block."""
        cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=_ARCHIVE_THRESHOLD_DAYS)
        issues: list[SpecsDoctorIssue] = []
        for record in self._bug_lines():
            closed_at = record.get("closed_at")
            moment = _parse_ts(closed_at) if isinstance(closed_at, str) else None
            if moment is not None and moment < cutoff:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-041",
                        severity=Severity.WARNING,
                        description=(
                            f"bugs/BUGS.jsonl record {record.get('id')!r} has been terminal "
                            f"({record.get('status')!r}) since {closed_at} — past the "
                            f"{_ARCHIVE_THRESHOLD_DAYS}-day archive threshold."
                        ),
                        path=str(self._ledger),
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
