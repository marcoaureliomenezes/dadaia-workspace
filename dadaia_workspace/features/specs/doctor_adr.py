"""ADR-SUPERSEDED-CITATION (0.4.7 c5 FR4): a memory atom, rule file or skill that cites
an ADR id whose record is ``superseded`` — ERROR. A rule pointing at a dead decision is
the drift the community asks CI to fail on; the successor lives in ``decisions.jsonl``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

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


def superseded_adr_citations(specs_dir: Path, public_dir: Path | None) -> list[SpecsDoctorIssue]:
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
    issues: list[SpecsDoctorIssue] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            cited = set(_ADR_CITATION_RE.findall(path.read_text(encoding="utf-8")))
            for adr_id in sorted(cited & superseded):
                issues.append(
                    SpecsDoctorIssue(
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
