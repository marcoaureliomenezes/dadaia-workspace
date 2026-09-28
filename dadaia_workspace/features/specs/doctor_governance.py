"""Governance validator: bug archive age, known bug ids.

Single-responsibility sibling of the SpecsDoctor coordinator: the archive-overdue signal
(SPEC-DOC-041) and the bug ids SPEC-DOC-048 cites. Leaf-only: imports the shared leaves + core, never a sibling
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

from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.features.specs.doctor_types import Severity, specs_finding

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
    """Bug governance: bug archive age, known bug ids."""

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

    def check_bug_archive_overdue(self, *, now: datetime | None = None) -> list[SectionFinding]:
        """SPEC-DOC-041 — WARN when a record closed (``closed_at``, never the filing date
        ``ts``) longer ago than the archive threshold is still live. Never a block."""
        cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=_ARCHIVE_THRESHOLD_DAYS)
        issues: list[SectionFinding] = []
        for record in self._bug_lines():
            closed_at = record.get("closed_at")
            moment = _parse_ts(closed_at) if isinstance(closed_at, str) else None
            if moment is not None and moment < cutoff:
                issues.append(
                    specs_finding(
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
