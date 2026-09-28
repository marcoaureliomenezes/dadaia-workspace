"""The `specs/ADRs/decisions.jsonl` reader — the ONE module that opens the ADR ledger.

Two rules live here because both read that one file: ADR-SUPERSEDED-CITATION over the
tree that cites decisions, and LEDGER-ADR-SCHEMA over the records and their numbering.

ADR-SUPERSEDED-CITATION: a memory atom, rule file or skill that cites
an ADR id whose record is ``superseded`` — ERROR. A rule pointing at a dead decision is
the drift the community asks CI to fail on; the successor lives in ``decisions.jsonl``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from dadaia_workspace.core.doctor_rules import Rule, SectionFinding
from dadaia_workspace.features.specs.doctor_types import Severity, specs_finding
from dadaia_workspace.features.specs.schemas import schema_errors

#: The ADR ledger, relative to a specs tree.
LEDGER = "ADRs/decisions.jsonl"

#: An ADR id as memory atoms, skills and rules cite it: `ADR: 0007`, `ADR 0007`, `ADR-0007`.
_ADR_CITATION_RE = re.compile(r"\bADR[:\s-]+(\d{4})\b")


def _superseded_ids(ledger: Path) -> set[str]:
    ids: set[str] = set()
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and record.get("status") == "superseded":
            ids.add(str(record.get("id")))
    return ids


def superseded_adr_citations(specs_dir: Path, public_dir: Path | None) -> list[SectionFinding]:
    """Every ``*.md`` under ``specs/memory`` and the library's skills, data and scaffold
    that cites a superseded decision id — one issue per (file, id)."""
    ledger = specs_dir / "ADRs" / "decisions.jsonl"
    if not ledger.is_file():
        return []
    superseded = _superseded_ids(ledger)
    if not superseded:
        return []
    roots = [specs_dir / "memory"]
    if public_dir is not None:
        roots.extend([public_dir / "skills", public_dir / "data", public_dir / "scaffold"])
    issues: list[SectionFinding] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            cited = set(_ADR_CITATION_RE.findall(path.read_text(encoding="utf-8")))
            for adr_id in sorted(cited & superseded):
                issues.append(
                    specs_finding(
                        code="ADR-SUPERSEDED-CITATION",
                        severity=Severity.ERROR,
                        description=(
                            f"{path.name} cites ADR {adr_id}, a superseded decision — "
                            "point at its successor in decisions.jsonl."
                        ),
                        path=str(path),
                    )
                )
    return issues


def adr_record_issues(specs_dir: Path) -> list[SectionFinding]:
    """Every record failing its schema, and the first id breaking 0001..N (file order).

    Located `path:line` relative to the specs tree: a finding pasted into a report never
    carries a local absolute path.
    """
    ledger = specs_dir / LEDGER
    if not ledger.is_file():
        return []
    issues: list[SectionFinding] = []
    ids: list[tuple[int, object]] = []
    for number, raw in enumerate(ledger.read_text(encoding="utf-8").split("\n"), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except ValueError as exc:
            issues.append(_record_issue(number, f"line is not valid JSON: {exc}"))
            continue
        ids.append((number, record.get("id") if isinstance(record, dict) else None))
        for message in schema_errors(record, "ADRs/decision-record-v1"):
            issues.append(_record_issue(number, message))
    for position, (number, adr_id) in enumerate(ids, start=1):
        if adr_id != (want := f"{position:04d}"):
            issues.append(_record_issue(number, f"id {adr_id!r} breaks 0001..N: expected {want}"))
            break
    return issues


def _record_issue(line: int, message: str) -> SectionFinding:
    return specs_finding(
        code="LEDGER-ADR-SCHEMA",
        severity=Severity.ERROR,
        description=message,
        path=f"{LEDGER}:{line}",
    )


LEDGER_RULES: tuple[Rule[Path], ...] = (
    Rule(
        ("LEDGER-ADR-SCHEMA",),
        "ledgers",
        adr_record_issues,
        fix_help=f"sed -i '<line>s|.*|<the corrected record>|' specs/{LEDGER}",
    ),
)
