"""ADR-SUPERSEDED-CITATION: a memory atom, skill or rule
citing a superseded decision is an error; accepted and proposed citations are silent.
Size: SMALL."""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.specs.doctor_adr import superseded_adr_citations
from dadaia_workspace.features.specs.doctor_types import finding_path
from tests.helpers.oslib import write_text
from tests.helpers.oslib import write_text as os_write_text


def _ledger(specs: Path, *records: dict[str, str]) -> None:
    (specs / "ADRs").mkdir(parents=True, exist_ok=True)
    write_text(specs / "ADRs" / "decisions.jsonl", "".join(json.dumps(r) + "\n" for r in records))


def test_superseded_citation_in_memory_and_skill_is_an_error(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0005", "status": "superseded"}, {"id": "0021", "status": "accepted"})
    (specs / "memory").mkdir()
    write_text(specs / "memory" / "ARCHITECTURE.md", "ADR: 0005 (accepted)\n")
    public = tmp_path / "public"
    (public / "skills" / "dd-x").mkdir(parents=True)
    write_text(public / "skills" / "dd-x" / "SKILL.md", "see ADR 0021 and ADR-0005\n")

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
    write_text(specs / "memory" / "QUALITY.md", "ADR: 0001 (accepted)\n")
    assert superseded_adr_citations(specs, None) == []


def test_a_record_holding_u2028_is_read_whole(tmp_path: Path) -> None:
    """A U+2028
    inside a superseded record's text keeps that record one line."""
    specs = tmp_path / "specs"
    (specs / "ADRs").mkdir(parents=True)
    record = {"id": "0005", "title": "a\u2028b", "status": "superseded"}
    os_write_text(specs / "ADRs" / "decisions.jsonl", json.dumps(record, ensure_ascii=False))
    (specs / "memory").mkdir()
    write_text(specs / "memory" / "QUALITY.md", "ADR: 0005\n")
    assert [i.code for i in superseded_adr_citations(specs, None)] == ["ADR-SUPERSEDED-CITATION"]


def test_a_superseded_id_inside_a_fixed_section_is_not_judged(tmp_path: Path) -> None:
    """Generated text is judged by its fragment: the id inside the block is silent, the same
    id in prose outside it is exactly one finding."""
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0005", "status": "superseded"})
    (specs / "memory").mkdir()
    arch = specs / "memory" / "ARCHITECTURE.md"
    block = "<!-- dadaia:fixed adr-list -->\n- 0042 — replaces ADR 0005\n<!-- /dadaia:fixed adr-list -->\n"
    write_text(arch, block)
    assert superseded_adr_citations(specs, None) == []

    write_text(arch, f"prose cites ADR 0005\n\n{block}")
    assert [i.code for i in superseded_adr_citations(specs, None)] == ["ADR-SUPERSEDED-CITATION"]


def test_a_citation_never_spans_a_fixed_section(tmp_path: Path) -> None:
    """The word ADR before a block and a number after it are two sentences, not a citation."""
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0005", "status": "superseded"})
    (specs / "memory").mkdir()
    block = "<!-- dadaia:fixed adr-list -->\n- 0042 — a title\n<!-- /dadaia:fixed adr-list -->\n"
    write_text(specs / "memory" / "ARCHITECTURE.md", f"see ADR\n{block}0005 rows\n")
    assert superseded_adr_citations(specs, None) == []


def test_a_whitespace_only_line_ends_a_citation_as_a_blank_line_does(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _ledger(specs, {"id": "0005", "status": "superseded"})
    (specs / "memory").mkdir()
    note = specs / "memory" / "ARCHITECTURE.md"
    write_text(note, "see ADR\n  \n0005 rows\n")
    assert superseded_adr_citations(specs, None) == []
    write_text(note, "see ADR\n  0005 rows\n")
    assert [i.code for i in superseded_adr_citations(specs, None)] == ["ADR-SUPERSEDED-CITATION"]
