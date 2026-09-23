"""Intent: CONTRACT — ADR-SUPERSEDED-CITATION (0.4.7 c5 FR4): a memory atom, skill or rule
citing a superseded decision is an error; accepted and proposed citations are silent.
Size: SMALL."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.doctor_adr import superseded_adr_citations

pytestmark = pytest.mark.unit


def _ledger(specs: Path, *records: dict[str, str]) -> None:
    (specs / "ADRs").mkdir(parents=True, exist_ok=True)
    (specs / "ADRs" / "decisions.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )


def test_superseded_citation_in_memory_and_skill_is_an_error(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0005", "status": "superseded"}, {"id": "0021", "status": "accepted"})
    (specs / "memory").mkdir()
    (specs / "memory" / "ARCHITECTURE.md").write_text("ADR: 0005 (accepted)\n", encoding="utf-8")
    public = tmp_path / "public"
    (public / "skills" / "dd-x").mkdir(parents=True)
    (public / "skills" / "dd-x" / "SKILL.md").write_text(
        "see ADR 0021 and ADR-0005\n", encoding="utf-8"
    )

    issues = superseded_adr_citations(specs, public)

    assert [(i.code, Path(i.path or "").name) for i in issues] == [
        ("ADR-SUPERSEDED-CITATION", "ARCHITECTURE.md"),
        ("ADR-SUPERSEDED-CITATION", "SKILL.md"),
    ]
    assert all("0005" in i.description for i in issues)


def test_no_superseded_record_means_silence(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0001", "status": "accepted"})
    (specs / "memory").mkdir()
    (specs / "memory" / "QUALITY.md").write_text("ADR: 0001 (accepted)\n", encoding="utf-8")
    assert superseded_adr_citations(specs, None) == []
