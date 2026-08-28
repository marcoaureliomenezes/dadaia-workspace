"""FR17 memory two-tier file-shape contract (v0.5.0 A17.1/A17.2/A17.5).

Intent: CONTRACT — 0.5.0 A17.1

`specs/memory/{ARCHITECTURE,QUALITY,TECHSTACK}.md` are each split into exactly two
top-level (``## ``) parts, Part 1 before Part 2 (A17.1). Every ``### P-NN ·`` block inside
Part 1 carries a ``Measured by:`` line and an ``ADR:`` line (A17.2) — the field is
spelled ``ADR:``, not SPEC FR17's illustrative ``Accepted by: ADR NNNN``, because every
promoted principle is `proposed` until the operator accepts it at T-050-31 (T-050-28
coverage table §5 R2) and writing ``Accepted by:`` today would assert an acceptance
nobody gave. The ``ADR:`` line is either ``ADR: NNNN (proposed|accepted...)``, mapping to
an existing record in ``specs/ADRs/decisions.jsonl`` or
``specs/ADRs/_superseded/superseded.jsonl`` (v0.5.0 specs-canon closure: ADRs moved to
one JSONL record per decision), or the literal ``ADR: none`` — a pre-canon principle
that predates the ADR mechanism entirely (the 28 mechanical, auto-generated markdown
ADRs this trio originally pointed at were deleted as non-canon; a FUTURE change to one
of these principles requires a real ADR, but the principle's OWN pre-existing text does
not retroactively need one manufactured for it).
P-ids are unique across the trio. No file carries a ``Changelog``/``History``/
``Histórico``/``Versions`` heading — memory stays current-state (A17.5).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MEMORY_DIR = _REPO_ROOT / "specs" / "memory"
_ADR_DECISIONS_PATH = _REPO_ROOT / "specs" / "ADRs" / "decisions.jsonl"
_ADR_SUPERSEDED_PATH = _REPO_ROOT / "specs" / "ADRs" / "_superseded" / "superseded.jsonl"

_MEMORY_FILES = ("ARCHITECTURE.md", "QUALITY.md", "TECHSTACK.md")

_PART1_HEADING = "Part 1 — Principles"
_PART2_HEADING = "Part 2 — Implementation"

_TOP_LEVEL_HEADING_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
_FORBIDDEN_HEADING_RE = re.compile(
    r"^#{1,6}\s*(Changelog|History|Hist[oó]rico|Versions)\b", re.MULTILINE | re.IGNORECASE
)
_PRINCIPLE_HEADING_RE = re.compile(r"^### P-(\d{2}) ·.*$", re.MULTILINE)
_BLOCK_BOUNDARY_RE = re.compile(r"^(?:### P-\d{2} ·|## )", re.MULTILINE)
_MEASURED_BY_RE = re.compile(r"^Measured by: .+$", re.MULTILINE)
_ADR_LINE_RE = re.compile(r"^ADR: (?:none|(\d{4}) \((?:proposed|accepted)\b.*\))\s*$", re.MULTILINE)


# --------------------------------------------------------------------------- file loading


def _memory_text(name: str) -> str:
    path = _MEMORY_DIR / name
    assert path.is_file(), f"memory atom missing: {path.relative_to(_REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def _top_level_headings(text: str) -> list[str]:
    return _TOP_LEVEL_HEADING_RE.findall(text)


def _principle_blocks(text: str) -> list[tuple[str, str]]:
    """Return (P-id, body) for every ``### P-NN ·`` block, body bounded by the next
    principle heading or the next ``## `` heading (never leaking into a later block)."""
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


def _adr_number_of(body: str) -> str | None:
    """The ``NNNN`` capture, or ``None`` for either "no ADR: line at all" or the literal
    ``ADR: none`` — the two cases the caller must distinguish."""
    match = _ADR_LINE_RE.search(body)
    if match is None:
        return None
    return match.group(1)


def _adr_record_ids() -> frozenset[str]:
    """Every ADR record id across BOTH specs/ADRs/decisions.jsonl and
    specs/ADRs/_superseded/superseded.jsonl (v0.5.0 specs-canon closure) — the
    union is the complete authored inventory, live + superseded. Malformed lines
    are skipped (this contract's own test_adr_canon.py owns validating the JSONL
    shape itself; here we only need the id set)."""
    ids: set[str] = set()
    for path in (_ADR_DECISIONS_PATH, _ADR_SUPERSEDED_PATH):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("id"), str):
                ids.add(obj["id"])
    return frozenset(ids)


def _adr_file_exists(adr_number: str) -> bool:
    return adr_number in _adr_record_ids()


# ------------------------------------------------------------------------------- A17.1


def test_each_memory_file_has_exactly_two_parts_in_order() -> None:
    for name in _MEMORY_FILES:
        headings = _top_level_headings(_memory_text(name))
        assert headings == [_PART1_HEADING, _PART2_HEADING], (
            f"{name} must carry exactly two top-level parts, in order "
            f"[{_PART1_HEADING!r}, {_PART2_HEADING!r}]; found {headings!r}"
        )

    # Mutation fixture — RED condition: a third top-level heading (drift back toward a
    # changelog-style section) must be caught, not silently accepted.
    mutated = (
        "## Part 1 — Principles\ncontent\n\n"
        "## Part 2 — Implementation\ncontent\n\n"
        "## Changelog\nstale narrative\n"
    )
    assert _top_level_headings(mutated) != [_PART1_HEADING, _PART2_HEADING]

    # Mutation fixture — RED condition: Part 2 before Part 1 (order violated).
    reordered = "## Part 2 — Implementation\ncontent\n\n## Part 1 — Principles\ncontent\n"
    assert _top_level_headings(reordered) != [_PART1_HEADING, _PART2_HEADING]


# ------------------------------------------------------------------------------- A17.5


def test_no_history_or_changelog_heading() -> None:
    for name in _MEMORY_FILES:
        text = _memory_text(name)
        match = _FORBIDDEN_HEADING_RE.search(text)
        assert match is None, (
            f"{name} carries a forbidden history-shaped heading: {match.group(0)!r} — "
            "memory stays current-state only (A17.5)."
        )

    # Mutation fixture — RED condition: the exact forbidden heading shape must fire.
    for forbidden in ("## Changelog", "### History", "## Histórico", "#### Versions"):
        mutated = f"{forbidden}\n- v1: did a thing\n"
        assert _FORBIDDEN_HEADING_RE.search(mutated) is not None, (
            f"detector failed to fire on a synthetic {forbidden!r} heading"
        )


# ------------------------------------------------------------------------------- A17.2


def test_every_principle_block_carries_measured_by_and_adr_line() -> None:
    for name in _MEMORY_FILES:
        blocks = _principle_blocks(_memory_text(name))
        assert blocks, f"{name} carries no `### P-NN ·` principle block"
        for pid, body in blocks:
            violations = _block_violations(body)
            assert not violations, f"{name} P-{pid} block is incomplete: {violations} (A17.2)."

    # Mutation fixture — RED condition: a block missing `Measured by:`.
    missing_measured_by = "### P-99 · A synthetic principle.\nADR: 9999 (proposed)\n"
    body = _principle_blocks(missing_measured_by)[0][1]
    assert "missing a `Measured by:` line" in _block_violations(body)

    # Mutation fixture — RED condition: a block missing the `ADR:` line.
    missing_adr = "### P-99 · A synthetic principle.\nMeasured by: `pytest something`.\n"
    body = _principle_blocks(missing_adr)[0][1]
    assert "missing an `ADR: NNNN (proposed|accepted...)` or `ADR: none` line" in _block_violations(
        body
    )

    # Mutation fixture — GREEN: a complete synthetic block carries no violation.
    complete = (
        "### P-99 · A synthetic principle.\n"
        "Measured by: `pytest something`.\n"
        "ADR: 9999 (proposed)\n"
        "Rationale: because.\n"
    )
    body = _principle_blocks(complete)[0][1]
    assert not _block_violations(body)

    # Mutation fixture — GREEN: `ADR: none` (a pre-canon principle) is also complete.
    complete_pre_canon = (
        "### P-98 · Another synthetic principle.\n"
        "Measured by: `pytest something else`.\n"
        "ADR: none\n"
    )
    body = _principle_blocks(complete_pre_canon)[0][1]
    assert not _block_violations(body)


def test_principle_ids_are_unique_across_the_trio() -> None:
    seen: dict[str, str] = {}
    for name in _MEMORY_FILES:
        for pid, _body in _principle_blocks(_memory_text(name)):
            assert pid not in seen, (
                f"P-{pid} appears in both {seen.get(pid)!r} and {name!r} — "
                "principle ids must be unique across the trio (A17.2)."
            )
            seen[pid] = name
    assert seen, "no P-NN principle ids found across the memory trio"

    # Mutation fixture — RED condition: the same synthetic id appears twice.
    left = _principle_blocks("### P-01 · Left.\nMeasured by: x.\nADR: 0001 (proposed)\n")
    right = _principle_blocks("### P-01 · Right.\nMeasured by: y.\nADR: 0002 (proposed)\n")
    duplicate_seen: dict[str, str] = {}
    duplicate_found = False
    for source_name, blocks in (("left.md", left), ("right.md", right)):
        for pid, _body in blocks:
            if pid in duplicate_seen:
                duplicate_found = True
            duplicate_seen[pid] = source_name
    assert duplicate_found, "duplicate-id mutation fixture failed to reproduce a collision"


def test_every_principle_maps_to_an_existing_adr_file_or_declares_adr_none() -> None:
    for name in _MEMORY_FILES:
        for pid, body in _principle_blocks(_memory_text(name)):
            adr_line_match = _ADR_LINE_RE.search(body)
            assert adr_line_match is not None, f"{name} P-{pid} carries no parseable ADR line"
            adr_number = adr_line_match.group(1)
            if adr_number is None:
                continue  # `ADR: none` — a pre-canon principle; nothing to map to
            assert _adr_file_exists(adr_number), (
                f"{name} P-{pid} points at ADR {adr_number}, but no record with "
                f"that id exists in specs/ADRs/decisions.jsonl or "
                f"specs/ADRs/_superseded/superseded.jsonl (A17.2/A18.4)."
            )

    # Mutation fixture — RED condition: an ADR number with no backing file.
    assert _adr_file_exists("9999") is False

    # Mutation fixture — `_adr_number_of` returns None for `ADR: none` (never treated as
    # "no parseable ADR line", the RED condition above's own distinct failure mode).
    none_body = _principle_blocks("### P-97 · Synthetic.\nADR: none\n")[0][1]
    assert _ADR_LINE_RE.search(none_body) is not None
    assert _adr_number_of(none_body) is None
