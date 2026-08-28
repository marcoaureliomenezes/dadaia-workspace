"""ADR canon contract — specs/ADRs/ (FR19, D12).

Intent: CONTRACT — 0.5.0 A19.3

Validates the specs/ADRs/ decision-record canon this release introduces (D12): monotonic,
gap-free numbering with no duplicates across the committed inventory
(``specs/ADRs/NNNN-<slug>.md``, discovered by glob only — never a hand list), presence of
every required field (the ``# ADR NNNN — <title>`` heading, a valid ``Status:`` line, a
``Date:`` line, the four ``##`` sections, and ``## Confirmation``'s ``Measured by:`` line),
and the operator-only acceptance law (SPEC.md FR19: "any agent may author `proposed`; ONLY
the operator flips a Status to `accepted`" — "an agent that writes `accepted` has violated
the law"). An ADR carrying ``Status: accepted`` with no ``Accepted by: operator`` line is
refused.

Every RED condition below is proven on an in-memory mutation fixture, never a real file on
disk. The committed inventory itself may legitimately be EMPTY (v0.5.0 specs-canon closure:
the 28 mechanical, auto-generated ADRs this release shipped at authoring time were deleted
as non-canon — a decision record is now authored only when a real principle-level decision
needs one, never as a backfill) — every check below is written to hold vacuously true over
an empty inventory, and the per-file parametrized test collects zero cases rather than
failing when none exist.

No CLI verb and no `specs doctor` rule are introduced by this file (A19.4) — it is a
pytest-only contract over the files already on disk plus in-memory fixtures.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "specs" / "ADRs"
_ADR_FILENAME_RE = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

_REQUIRED_HEADINGS: tuple[str, ...] = (
    "## Context",
    "## Decision",
    "## Consequences",
    "## Confirmation",
)

_STATUS_RE = re.compile(r"^Status: (proposed|accepted|rejected|superseded by \d{4})$", re.MULTILINE)
_TITLE_RE = re.compile(r"^# ADR (\d{4}) — .+$", re.MULTILINE)
_DATE_RE = re.compile(r"^Date: \S.*$", re.MULTILINE)
_MEASURED_BY_RE = re.compile(r"^Measured by:", re.MULTILINE)
_ACCEPTED_BY_OPERATOR_RE = re.compile(r"^Accepted by: operator\b", re.MULTILINE)


def _discover_adr_files() -> list[Path]:
    """Every ADR this test validates is discovered by glob — never a hand list (D12)."""
    return sorted(
        (p for p in _ADR_DIR.glob("*.md") if _ADR_FILENAME_RE.match(p.name)),
        key=lambda p: p.name,
    )


_ADR_FILES: list[Path] = _discover_adr_files()
_ADR_IDS: list[str] = [p.name for p in _ADR_FILES]


def find_field_violations(filename: str, text: str) -> list[str]:
    """Pure validator: every required-field check for one ADR body, as violation strings.

    Shared by the real-file parametrized test below (asserting the empty list) and every
    in-memory mutation fixture (asserting the violation the mutation should trip).
    """
    violations: list[str] = []

    match = _ADR_FILENAME_RE.match(filename)
    if match is None:
        return [f"{filename}: filename does not match the NNNN-<slug>.md pattern"]
    number = int(match.group(1))

    title_match = _TITLE_RE.search(text)
    if title_match is None:
        violations.append(f"{filename}: missing the '# ADR NNNN — <title>' heading")
    elif int(title_match.group(1)) != number:
        violations.append(
            f"{filename}: title number {title_match.group(1)} does not match the filename "
            f"number {number:04d}"
        )

    status_match = _STATUS_RE.search(text)
    if status_match is None:
        violations.append(
            f"{filename}: missing a valid 'Status: proposed|accepted|rejected|superseded "
            "by NNNN' line"
        )
    elif status_match.group(1) == "accepted" and _ACCEPTED_BY_OPERATOR_RE.search(text) is None:
        violations.append(
            f"{filename}: Status: accepted with no 'Accepted by: operator' line — only the "
            "operator accepts (FR19/D12)"
        )

    if _DATE_RE.search(text) is None:
        violations.append(f"{filename}: missing a 'Date:' line")

    for heading in _REQUIRED_HEADINGS:
        if re.search(rf"^{re.escape(heading)}$", text, re.MULTILINE) is None:
            violations.append(f"{filename}: missing the required heading {heading!r}")

    if _MEASURED_BY_RE.search(text) is None:
        violations.append(f"{filename}: '## Confirmation' section missing a 'Measured by:' line")

    return violations


def find_numbering_violations(filenames: list[str]) -> list[str]:
    """Pure validator over a *list of filenames only* — numbering never needs file bodies."""
    violations: list[str] = []
    numbers: list[int] = []
    for name in filenames:
        match = _ADR_FILENAME_RE.match(name)
        if match is None:
            violations.append(f"{name}: filename does not match the NNNN-<slug>.md pattern")
            continue
        numbers.append(int(match.group(1)))

    if not numbers:
        return violations

    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        violations.append(f"duplicate ADR number(s): {duplicates}")

    distinct = sorted(set(numbers))
    expected = list(range(1, len(distinct) + 1))
    if distinct != expected:
        violations.append(
            f"numbering is not monotonic and gap-free from 0001: got {distinct}, "
            f"expected {expected}"
        )

    return violations


# ---------------------------------------------------------------------------------------
# The real, committed inventory — discovered by glob, never a hand list.
# ---------------------------------------------------------------------------------------


def test_adr_inventory_may_be_legitimately_empty() -> None:
    """An empty specs/ADRs/ inventory is valid (v0.5.0 specs-canon closure) — discovery
    itself must never raise regardless of population; every other check in this module
    (numbering, per-file field validation) is written to hold vacuously true when the
    discovered set is empty, never to require a minimum count."""
    assert isinstance(_ADR_FILES, list)


def test_adr_files_are_discovered_by_glob_never_a_hand_list() -> None:
    """Re-globbing at test time must reproduce the exact module-level discovery used to
    build every parametrization below — the inventory is never a hand-maintained list."""
    assert _discover_adr_files() == _ADR_FILES


def test_adr_numbering_is_monotonic_gap_free_and_duplicate_free() -> None:
    violations = find_numbering_violations([p.name for p in _ADR_FILES])
    assert violations == [], violations


@pytest.mark.parametrize("adr_path", _ADR_FILES, ids=_ADR_IDS)
def test_adr_carries_every_required_field(adr_path: Path) -> None:
    text = adr_path.read_text(encoding="utf-8")
    violations = find_field_violations(adr_path.name, text)
    assert violations == [], violations


# ---------------------------------------------------------------------------------------
# Mutation fixtures — one in-memory RED condition per required field, never a real file.
# ---------------------------------------------------------------------------------------

_VALID_FIXTURE = """\
# ADR 0001 — A fixture decision

Status: proposed
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Fixture context paragraph.

## Decision
We will do the fixture thing.

## Consequences
+ a benefit
- a cost

## Confirmation
Measured by: tests/contract/test_adr_canon.py itself.
"""


def test_valid_fixture_has_no_violations() -> None:
    """Baseline: the fixture every mutation below starts from is itself clean."""
    assert find_field_violations("0001-fixture.md", _VALID_FIXTURE) == []


def test_missing_title_is_red() -> None:
    mutated = _VALID_FIXTURE.replace("# ADR 0001 — A fixture decision\n\n", "")
    violations = find_field_violations("0001-fixture.md", mutated)
    assert any("ADR NNNN" in v for v in violations), violations


def test_missing_status_line_is_red() -> None:
    mutated = _VALID_FIXTURE.replace("Status: proposed\n", "")
    violations = find_field_violations("0001-fixture.md", mutated)
    assert any("Status:" in v for v in violations), violations


def test_invalid_status_value_is_red() -> None:
    mutated = _VALID_FIXTURE.replace("Status: proposed", "Status: in-review")
    violations = find_field_violations("0001-fixture.md", mutated)
    assert any("Status:" in v for v in violations), violations


def test_missing_date_line_is_red() -> None:
    mutated = _VALID_FIXTURE.replace("Date: 2026-08-27\n", "")
    violations = find_field_violations("0001-fixture.md", mutated)
    assert any("Date:" in v for v in violations), violations


@pytest.mark.parametrize("heading", _REQUIRED_HEADINGS)
def test_missing_required_heading_is_red(heading: str) -> None:
    mutated = _VALID_FIXTURE.replace(f"{heading}\n", "", 1)
    violations = find_field_violations("0001-fixture.md", mutated)
    assert any(heading in v for v in violations), violations


def test_confirmation_missing_measured_by_is_red() -> None:
    mutated = _VALID_FIXTURE.replace(
        "Measured by: tests/contract/test_adr_canon.py itself.\n",
        "no measure stated here.\n",
    )
    violations = find_field_violations("0001-fixture.md", mutated)
    assert any("Measured by" in v for v in violations), violations


def test_accepted_status_without_operator_attribution_is_red() -> None:
    """The operator-only acceptance law (FR19/D12): a ``Status: accepted`` line with no
    ``Accepted by: operator`` line is refused. Proven only on an in-memory fixture — no
    committed ADR is accepted yet (all 28 are ``Status: proposed``, per FR19's own text:
    "any agent may author `proposed`; ONLY the operator flips a Status to `accepted`")."""
    mutated = _VALID_FIXTURE.replace("Status: proposed", "Status: accepted")
    violations = find_field_violations("0001-fixture.md", mutated)
    assert any("Accepted by: operator" in v for v in violations), violations


def test_accepted_status_with_operator_attribution_is_green() -> None:
    mutated = _VALID_FIXTURE.replace("Status: proposed", "Status: accepted") + (
        "Accepted by: operator, 2026-08-27\n"
    )
    violations = find_field_violations("0001-fixture.md", mutated)
    assert violations == [], violations


def test_gap_in_numbering_is_red() -> None:
    violations = find_numbering_violations(["0001-a.md", "0003-b.md"])
    assert any("monotonic and gap-free" in v for v in violations), violations


def test_duplicate_numbering_is_red() -> None:
    violations = find_numbering_violations(["0001-a.md", "0001-b.md", "0002-c.md"])
    assert any("duplicate" in v for v in violations), violations


def test_numbering_not_starting_at_0001_is_red() -> None:
    violations = find_numbering_violations(["0002-a.md", "0003-b.md"])
    assert any("monotonic and gap-free" in v for v in violations), violations
