"""The `specs/ADRs/decisions.jsonl` reader — the ONE module that opens the ADR ledger.

Two rules live here because both read that one file: ADR-SUPERSEDED-CITATION over the
tree that cites decisions, and LEDGER-ADR-SCHEMA over the records and their numbering.

ADR-SUPERSEDED-CITATION: a memory atom, rule file or skill that cites
an ADR id whose record is ``superseded`` — ERROR. A rule pointing at a dead decision is
the drift the community asks CI to fail on; the successor lives in ``decisions.jsonl``.
"""

from __future__ import annotations

import re
from contextlib import suppress
from pathlib import Path

from dadaia_workspace.core.doctor_rules import Rule, SectionFinding
from dadaia_workspace.features.specs.doctor_types import Severity, specs_finding
from dadaia_workspace.infrastructure.ledger_scripts import load_owner

#: The ADR ledger, relative to a specs tree.
LEDGER = "ADRs/decisions.jsonl"

#: An ADR id as memory atoms, skills and rules cite it: `ADR: 0007`, `ADR 0007`, `ADR-0007`.
_ADR_CITATION_RE = re.compile(r"\bADR[:\s-]+(\d{4})\b")


def _superseded_ids(ledger: Path) -> set[str]:
    """An unreadable line supersedes nothing here; it is `adr_record_issues`' finding."""
    owner = load_owner("dd-bug-resolution", "_ledger")
    ids: set[str] = set()
    for raw in ledger.read_text(encoding="utf-8").split("\n"):
        with suppress(owner.LineError):
            ids |= {str(r.get("id")) for r in owner.parse(raw) if r.get("status") == "superseded"}
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
    records: list[tuple[int, dict[str, object]]] = []
    owner = load_owner("dd-bug-resolution", "_ledger")
    schema = owner.load_schema("decision-record-v1")
    for number, raw in enumerate(ledger.read_text(encoding="utf-8").split("\n"), start=1):
        try:
            parsed = owner.parse(raw)
        except owner.LineError as exc:
            issues.append(_record_issue(ledger, number, f"line {exc}"))
            continue
        for record in parsed:
            records.append((number, record))
            issues.extend(
                _record_issue(ledger, number, m)
                for m in owner.validate(record, schema, schema, "record")
            )
    for position, (number, record) in enumerate(records, start=1):
        if (adr_id := record.get("id")) != (want := f"{position:04d}"):
            issues.append(
                _record_issue(ledger, number, f"id {adr_id!r} breaks 0001..N: expected {want}")
            )
            break
    accepted = {str(r.get("id")) for _, r in records if r.get("status") == "accepted"}
    for number, r in records:  # M2 (ADR 0151): only a ruled record changes a ruled one
        named = f"{r.get('supersedes') or ''},{r.get('amends') or ''}".split(",")
        ruled = r.get("status") == "accepted" and "ruling" in r
        if r.get("status") != "rejected" and not ruled and (hit := sorted(accepted & set(named))):
            issues.append(_record_issue(ledger, number, f"changes accepted {hit} without a ruling"))
    return issues


#: Who writes an ADR record, and the law forbidding a hand edit of one.
_VERBS, _LAW = "a `docs(adr)` propose or accept commit", "the ADR law, specs/ADRs/AGENTS.md"


def _record_issue(ledger: Path, line: int, message: str) -> SectionFinding:
    return specs_finding(
        code="LEDGER-ADR-SCHEMA",
        severity=Severity.ERROR,
        description=message,
        path=f"{LEDGER}:{line}",
        fix=load_owner("dd-bug-resolution", "_ledger").unwritten(ledger, line, _VERBS, _LAW),
    )


LEDGER_RULES: tuple[Rule[Path], ...] = (
    Rule(
        ("LEDGER-ADR-SCHEMA",),
        "ledgers",
        adr_record_issues,
        fix_help=load_owner("dd-bug-resolution", "_ledger").unwritten(
            Path("<specs>") / LEDGER, "the record named", _VERBS, _LAW
        ),
    ),
)
