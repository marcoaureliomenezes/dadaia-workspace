"""ADR-SUPERSEDED-CITATION: a memory atom, skill or rule
citing a superseded decision is an error; accepted and proposed citations are silent.
Size: SMALL."""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.specs.doctor_adr import superseded_adr_citations
from dadaia_workspace.features.specs.doctor_types import finding_path


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

    assert [(i.code, Path(finding_path(i) or "").name) for i in issues] == [
        ("ADR-SUPERSEDED-CITATION", "ARCHITECTURE.md"),
        ("ADR-SUPERSEDED-CITATION", "SKILL.md"),
    ]
    assert all("0005" in i.message for i in issues)


def test_no_superseded_record_means_silence(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0001", "status": "accepted"})
    (specs / "memory").mkdir()
    (specs / "memory" / "QUALITY.md").write_text("ADR: 0001 (accepted)\n", encoding="utf-8")
    assert superseded_adr_citations(specs, None) == []


def test_a_record_holding_u2028_is_read_whole(tmp_path: Path) -> None:
    """A U+2028
    inside a superseded record's text keeps that record one line."""
    specs = tmp_path / "specs"
    (specs / "ADRs").mkdir(parents=True)
    record = {"id": "0005", "title": "a\u2028b", "status": "superseded"}
    (specs / "ADRs" / "decisions.jsonl").write_text(json.dumps(record, ensure_ascii=False), "utf-8")
    (specs / "memory").mkdir()
    (specs / "memory" / "QUALITY.md").write_text("ADR: 0005\n", encoding="utf-8")
    assert [i.code for i in superseded_adr_citations(specs, None)] == ["ADR-SUPERSEDED-CITATION"]


def test_a_superseded_id_inside_a_fixed_section_is_not_judged(tmp_path: Path) -> None:
    """Generated text is judged by its fragment: the id inside the block is silent, the same
    id in prose outside it is exactly one finding."""
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0005", "status": "superseded"})
    (specs / "memory").mkdir()
    arch = specs / "memory" / "ARCHITECTURE.md"
    block = "<!-- dadaia:fixed adr-list -->\n- 0042 — replaces ADR 0005\n<!-- /dadaia:fixed adr-list -->\n"
    arch.write_text(block, encoding="utf-8")
    assert superseded_adr_citations(specs, None) == []

    arch.write_text(f"prose cites ADR 0005\n\n{block}", encoding="utf-8")
    assert [i.code for i in superseded_adr_citations(specs, None)] == ["ADR-SUPERSEDED-CITATION"]


def test_a_citation_never_spans_a_fixed_section(tmp_path: Path) -> None:
    """The word ADR before a block and a number after it are two sentences, not a citation."""
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0005", "status": "superseded"})
    (specs / "memory").mkdir()
    block = "<!-- dadaia:fixed adr-list -->\n- 0042 — a title\n<!-- /dadaia:fixed adr-list -->\n"
    (specs / "memory" / "ARCHITECTURE.md").write_text(
        f"see ADR\n{block}0005 rows\n", encoding="utf-8"
    )
    assert superseded_adr_citations(specs, None) == []


def test_a_whitespace_only_line_ends_a_citation_as_a_blank_line_does(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0005", "status": "superseded"})
    (specs / "memory").mkdir()
    note = specs / "memory" / "ARCHITECTURE.md"
    note.write_text("see ADR\n  \n0005 rows\n", encoding="utf-8")
    assert superseded_adr_citations(specs, None) == []
    note.write_text("see ADR\n  0005 rows\n", encoding="utf-8")
    assert [i.code for i in superseded_adr_citations(specs, None)] == ["ADR-SUPERSEDED-CITATION"]
