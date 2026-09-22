"""The v7 canonical-memory file shape (0.4.7 FR1, ADR 0023).

Intent: CONTRACT — 0.4.7 FR1

`specs/memory/` carries exactly two canonical files, and each states its sections in one
fixed order: `ARCHITECTURE.md` is `## Principles` / `## Tech Stack` / `## Structure`,
`QUALITY.md` is `## Principles` / `## Test architecture` / `## Gates`. The retired
`TECHSTACK.md` is gone: its body is `ARCHITECTURE.md`'s `## Tech Stack` section, the ONE
place the stack is stated, and the two-tier `Part 1 — Principles` / `Part 2 —
Implementation` split it replaces is forbidden by the same ordering assertion.

Every `### P-NN ·` block under `## Principles` carries a `Measured by:` line and an `ADR:`
line — `ADR: NNNN (proposed|accepted…)` mapping to a record in `specs/ADRs/decisions.jsonl`,
or the literal `ADR: none` for a principle that predates the ADR mechanism. P-ids are
unique across the pair. Neither file carries a `Changelog`/`History`/`Histórico`/`Versions`
heading — memory stays current-state. Each file carries its library-owned fixed block
(`slop-code`, `slop-tests`) intact.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dadaia_workspace.core.fixed_sections import extract_fixed_section
from dadaia_workspace.features.specs.memory_canon import MEMORY_TOPLEVEL_FILES

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MEMORY_DIR = _REPO_ROOT / "specs" / "memory"
_ADR_DECISIONS_PATH = _REPO_ROOT / "specs" / "ADRs" / "decisions.jsonl"

#: The v7 section order, per canonical file. The expected value comes from the SPEC's
#: FR1, never from the files themselves.
_CANONICAL_SECTIONS: dict[str, tuple[str, ...]] = {
    "ARCHITECTURE.md": ("Principles", "Tech Stack", "Structure"),
    "QUALITY.md": ("Principles", "Test architecture", "Gates"),
}

#: The library fixed block each canonical file carries (``core.fixed_sections``).
_FIXED_SECTION_IDS: dict[str, str] = {
    "ARCHITECTURE.md": "slop-code",
    "QUALITY.md": "slop-tests",
}

_TOP_LEVEL_HEADING_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
_FORBIDDEN_HEADING_RE = re.compile(
    r"^#{1,6}\s*(Changelog|History|Hist[oó]rico|Versions)\b", re.MULTILINE | re.IGNORECASE
)
_PRINCIPLE_HEADING_RE = re.compile(r"^### P-(\d{2}) ·.*$", re.MULTILINE)
_BLOCK_BOUNDARY_RE = re.compile(r"^(?:### P-\d{2} ·|## )", re.MULTILINE)
_MEASURED_BY_RE = re.compile(r"^Measured by: .+$", re.MULTILINE)
_ADR_LINE_RE = re.compile(r"^ADR: (?:none|(\d{4}) \((?:proposed|accepted)\b.*\))\s*$", re.MULTILINE)


def _memory_text(name: str) -> str:
    path = _MEMORY_DIR / name
    assert path.is_file(), f"canonical memory file missing: {path.relative_to(_REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def _top_level_headings(text: str) -> list[str]:
    return _TOP_LEVEL_HEADING_RE.findall(text)


def _principle_blocks(text: str) -> list[tuple[str, str]]:
    """``(P-id, body)`` per ``### P-NN ·`` block, bounded by the next principle heading
    or the next ``## `` heading — never leaking into a later block."""
    blocks: list[tuple[str, str]] = []
    for match in _PRINCIPLE_HEADING_RE.finditer(text):
        start = match.end()
        boundary = _BLOCK_BOUNDARY_RE.search(text, start)
        end = boundary.start() if boundary else len(text)
        blocks.append((match.group(1), text[start:end]))
    return blocks


def _block_violations(body: str) -> list[str]:
    violations: list[str] = []
    if not _MEASURED_BY_RE.search(body):
        violations.append("missing a `Measured by:` line")
    if not _ADR_LINE_RE.search(body):
        violations.append("missing an `ADR: NNNN (proposed|accepted...)` or `ADR: none` line")
    return violations


def _adr_record_ids() -> frozenset[str]:
    """Every ADR record id in ``decisions.jsonl`` — proposed/accepted/rejected/superseded
    alike (a superseded record is retired in place). Malformed lines are skipped:
    ``test_adr_canon.py`` owns the JSONL shape; here only the id set matters."""
    ids: set[str] = set()
    if not _ADR_DECISIONS_PATH.is_file():
        return frozenset()
    for line in _ADR_DECISIONS_PATH.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            ids.add(record["id"])
    return frozenset(ids)


# ------------------------------------------------------------------ the canonical pair


def test_the_canonical_pair_is_architecture_and_quality() -> None:
    assert MEMORY_TOPLEVEL_FILES == ("ARCHITECTURE.md", "QUALITY.md")
    assert sorted(p.name for p in _MEMORY_DIR.glob("*.md")) == [
        "AGENTS.md",
        "ARCHITECTURE.md",
        "QUALITY.md",
    ]
    assert not (_MEMORY_DIR / "TECHSTACK.md").exists(), (
        "memory/TECHSTACK.md left the canon at specs_pattern_version 7 — its body is "
        "ARCHITECTURE.md's `## Tech Stack` section."
    )


def test_each_canonical_file_states_its_sections_in_the_v7_order() -> None:
    for name, expected in _CANONICAL_SECTIONS.items():
        headings = _top_level_headings(_memory_text(name))
        assert headings == list(expected), (
            f"{name} must carry exactly the v7 sections {list(expected)!r}, in order; "
            f"found {headings!r}"
        )

    # Mutation fixture — RED: the retired two-tier shape is no longer conformant.
    two_tier = "## Part 1 — Principles\nx\n\n## Part 2 — Implementation\ny\n"
    assert _top_level_headings(two_tier) != list(_CANONICAL_SECTIONS["ARCHITECTURE.md"])

    # Mutation fixture — RED: a fourth section (drift back toward a narrative append).
    drifted = "## Principles\nx\n\n## Tech Stack\ny\n\n## Structure\nz\n\n## Notes\nw\n"
    assert _top_level_headings(drifted) != list(_CANONICAL_SECTIONS["ARCHITECTURE.md"])

    # Mutation fixture — RED: the right sections in the wrong order.
    reordered = "## Tech Stack\ny\n\n## Principles\nx\n\n## Structure\nz\n"
    assert _top_level_headings(reordered) != list(_CANONICAL_SECTIONS["ARCHITECTURE.md"])


def test_each_canonical_file_carries_its_library_fixed_block() -> None:
    for name, section_id in _FIXED_SECTION_IDS.items():
        body = extract_fixed_section(_memory_text(name), section_id)
        assert body, f"{name} lost its `{section_id}` fixed block"

    # Mutation fixture — RED: a file with the markers stripped.
    assert extract_fixed_section("## Principles\nno markers here\n", "slop-code") is None


# --------------------------------------------------------------------- current state


def test_no_history_or_changelog_heading() -> None:
    for name in _CANONICAL_SECTIONS:
        text = _memory_text(name)
        match = _FORBIDDEN_HEADING_RE.search(text)
        assert match is None, (
            f"{name} carries a forbidden history-shaped heading: {match.group(0)!r} — "
            "canonical memory stays current-state only."
        )

    for forbidden in ("## Changelog", "### History", "## Histórico", "#### Versions"):
        mutated = f"{forbidden}\n- v1: did a thing\n"
        assert _FORBIDDEN_HEADING_RE.search(mutated) is not None, (
            f"detector failed to fire on a synthetic {forbidden!r} heading"
        )


# ------------------------------------------------------------------ principle blocks


def test_every_principle_block_carries_measured_by_and_adr_line() -> None:
    for name in _CANONICAL_SECTIONS:
        blocks = _principle_blocks(_memory_text(name))
        assert blocks, f"{name} carries no `### P-NN ·` principle block"
        for pid, body in blocks:
            violations = _block_violations(body)
            assert not violations, f"{name} P-{pid} block is incomplete: {violations}."

    missing_measured_by = "### P-99 · A synthetic principle.\nADR: 9999 (proposed)\n"
    assert "missing a `Measured by:` line" in _block_violations(
        _principle_blocks(missing_measured_by)[0][1]
    )

    missing_adr = "### P-99 · A synthetic principle.\nMeasured by: `pytest something`.\n"
    assert "missing an `ADR: NNNN (proposed|accepted...)` or `ADR: none` line" in _block_violations(
        _principle_blocks(missing_adr)[0][1]
    )

    complete = (
        "### P-99 · A synthetic principle.\n"
        "Measured by: `pytest something`.\n"
        "ADR: 9999 (proposed)\n"
        "Rationale: because.\n"
    )
    assert not _block_violations(_principle_blocks(complete)[0][1])

    pre_canon = "### P-98 · Another one.\nMeasured by: `pytest else`.\nADR: none\n"
    assert not _block_violations(_principle_blocks(pre_canon)[0][1])


def test_principle_ids_are_unique_across_the_pair() -> None:
    seen: dict[str, str] = {}
    for name in _CANONICAL_SECTIONS:
        for pid, _body in _principle_blocks(_memory_text(name)):
            assert pid not in seen, (
                f"P-{pid} appears in both {seen.get(pid)!r} and {name!r} — "
                "principle ids are unique across the canonical pair."
            )
            seen[pid] = name
    assert seen, "no P-NN principle ids found across the canonical pair"


def test_every_principle_maps_to_an_existing_adr_record_or_declares_adr_none() -> None:
    known = _adr_record_ids()
    for name in _CANONICAL_SECTIONS:
        for pid, body in _principle_blocks(_memory_text(name)):
            match = _ADR_LINE_RE.search(body)
            assert match is not None, f"{name} P-{pid} carries no parseable ADR line"
            adr_number = match.group(1)
            if adr_number is None:
                continue  # `ADR: none` — a pre-canon principle
            assert adr_number in known, (
                f"{name} P-{pid} points at ADR {adr_number}, but no record with that id "
                "exists in specs/ADRs/decisions.jsonl."
            )

    assert "9999" not in known

    none_body = _principle_blocks("### P-97 · Synthetic.\nADR: none\n")[0][1]
    assert _ADR_LINE_RE.search(none_body) is not None
    assert _ADR_LINE_RE.search(none_body).group(1) is None  # type: ignore[union-attr]


def test_principles_live_only_under_the_principles_section() -> None:
    """A `### P-NN ·` block outside `## Principles` would be a second, competing home
    for a canonical statement — the drift the v7 shape exists to prevent."""
    for name in _CANONICAL_SECTIONS:
        text = _memory_text(name)
        principles_start = text.index("## Principles")
        next_section = _TOP_LEVEL_HEADING_RE.search(text, principles_start + 1)
        assert next_section is not None, f"{name} has no section after `## Principles`"
        for match in _PRINCIPLE_HEADING_RE.finditer(text):
            assert principles_start < match.start() < next_section.start(), (
                f"{name}: {match.group(0)!r} sits outside the `## Principles` section"
            )
