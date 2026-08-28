"""ADR canon contract — specs/ADRs/ (v0.5.0 specs-canon closure, operator ruling
2026-08-28).

Intent: CONTRACT — v0.5.0 specs-canon closure

Validates the specs/ADRs/ decision-record canon this task introduces: JSONL, one
record per line (dadaia_workspace.core.models.adr.AdrRecord), monotonic gap-free ids
across BOTH ``specs/ADRs/decisions.jsonl`` AND
``specs/ADRs/_superseded/superseded.jsonl`` together (a superseded decision MOVES,
never copies — its id is never reused, never re-numbered), the status enum
{proposed, accepted, rejected, superseded}, and the operator-only acceptance law
(``accepted`` requires a non-null ``measured_by`` — a decision nobody can measure is
not a principle, it is prose).

Every RED condition below is proven on an in-memory mutation fixture, never a real
file on disk. Both committed files may legitimately be EMPTY (no real principle-level
decision has been authored yet under the JSONL canon — the 28 mechanical, auto-
generated markdown ADRs this repository shipped at authoring time were deleted as
non-canon; a decision record is now authored only when a real principle-level
decision needs one, never as a backfill) — every check below holds vacuously true
over an empty inventory.

No CLI verb and no ``specs doctor`` rule are introduced by this file (item 4's own
scope) — a pytest-only contract over the files already on disk plus in-memory
fixtures. Supersedes the pre-v0.5.0-specs-canon-closure markdown-ADR contract
(``NNNN-<slug>.md``, one file per decision) entirely — that machinery is deleted with
this rewrite.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "specs" / "ADRs"
_DECISIONS_PATH = _ADR_DIR / "decisions.jsonl"
_SUPERSEDED_PATH = _ADR_DIR / "_superseded" / "superseded.jsonl"

_STATUS_ENUM: frozenset[str] = frozenset({"proposed", "accepted", "rejected", "superseded"})
_REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "ts",
    "title",
    "status",
    "context",
    "decision",
    "consequences",
    "measured_by",
    "supersedes",
    "amends",
)


def _read_jsonl_records(path: Path) -> list[dict[str, object]]:
    """Every non-blank line of *path* parsed as a JSON object; an empty or absent
    file is an empty list — never an error (a legitimately empty inventory)."""
    if not path.is_file():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        obj = json.loads(stripped)
        assert isinstance(obj, dict), f"{path}: not a JSON object: {stripped!r}"
        records.append(obj)
    return records


def find_field_violations(record: dict[str, object]) -> list[str]:
    """Pure validator: every required-field/status/acceptance-law check for one
    record, as violation strings. Shared by the real-file assertion below and every
    in-memory mutation fixture."""
    violations: list[str] = []
    record_id = record.get("id", "<missing id>")

    for field in _REQUIRED_FIELDS:
        if field not in record:
            violations.append(f"{record_id}: missing required field {field!r}")

    status = record.get("status")
    if status is not None and status not in _STATUS_ENUM:
        violations.append(f"{record_id}: status {status!r} is not in {sorted(_STATUS_ENUM)}")

    if status == "accepted" and not record.get("measured_by"):
        violations.append(
            f"{record_id}: status 'accepted' requires a non-null 'measured_by' — a "
            "decision nobody can measure is not a principle, it is prose"
        )

    return violations


def find_numbering_violations(ids: list[str]) -> list[str]:
    """Pure validator over a *list of id strings only* (across BOTH files, combined
    by the caller) — numbering never needs the full record body."""
    violations: list[str] = []
    if not ids:
        return violations

    for value in ids:
        if not (len(value) == 4 and value.isdigit()):
            violations.append(f"{value!r}: id is not a 4-digit zero-padded string")

    numeric = [int(v) for v in ids if len(v) == 4 and v.isdigit()]
    duplicates = sorted({n for n in numeric if numeric.count(n) > 1})
    if duplicates:
        violations.append(f"duplicate id(s): {[f'{n:04d}' for n in duplicates]}")

    distinct = sorted(set(numeric))
    expected = list(range(1, len(distinct) + 1))
    if distinct != expected:
        violations.append(
            "numbering is not monotonic and gap-free from 0001: got "
            f"{[f'{n:04d}' for n in distinct]}, expected {[f'{n:04d}' for n in expected]}"
        )
    return violations


# ---------------------------------------------------------------------------------------
# The real, committed inventory — decisions.jsonl + _superseded/superseded.jsonl.
# ---------------------------------------------------------------------------------------


def test_committed_inventory_may_be_legitimately_empty() -> None:
    """Discovery itself must never raise regardless of population; every other check
    in this module holds vacuously true when the discovered set is empty."""
    assert isinstance(_read_jsonl_records(_DECISIONS_PATH), list)
    assert isinstance(_read_jsonl_records(_SUPERSEDED_PATH), list)


def test_every_committed_record_carries_every_required_field_and_a_valid_status() -> None:
    all_records = _read_jsonl_records(_DECISIONS_PATH) + _read_jsonl_records(_SUPERSEDED_PATH)
    for record in all_records:
        violations = find_field_violations(record)
        assert violations == [], violations


def test_committed_ids_are_monotonic_gap_free_and_duplicate_free_across_both_files() -> None:
    """The union of decisions.jsonl + _superseded/superseded.jsonl ids must be
    1..N gap-free — a moved (superseded) record's id is never reused, never
    re-numbered, so the two files' ids never overlap and always fill one sequence."""
    all_records = _read_jsonl_records(_DECISIONS_PATH) + _read_jsonl_records(_SUPERSEDED_PATH)
    ids = [str(record.get("id")) for record in all_records]
    violations = find_numbering_violations(ids)
    assert violations == [], violations


# ---------------------------------------------------------------------------------------
# Mutation fixtures — one in-memory RED condition per rule, never a real file.
# ---------------------------------------------------------------------------------------

_VALID_RECORD: dict[str, object] = {
    "id": "0001",
    "ts": "2026-08-28T12:00:00Z",
    "title": "A fixture decision",
    "status": "proposed",
    "context": "Fixture context paragraph.",
    "decision": "We will do the fixture thing.",
    "consequences": "+ a benefit\n- a cost",
    "measured_by": None,
    "supersedes": None,
    "amends": None,
}


def test_valid_fixture_has_no_violations() -> None:
    assert find_field_violations(_VALID_RECORD) == []


@pytest.mark.parametrize("field_name", ["id", "ts", "title", "context", "decision", "consequences"])
def test_missing_required_field_is_red(field_name: str) -> None:
    mutated = {k: v for k, v in _VALID_RECORD.items() if k != field_name}
    violations = find_field_violations(mutated)
    assert any(field_name in v for v in violations), violations


def test_invalid_status_value_is_red() -> None:
    mutated = {**_VALID_RECORD, "status": "in-review"}
    violations = find_field_violations(mutated)
    assert any("status" in v for v in violations), violations


def test_accepted_status_without_measured_by_is_red() -> None:
    mutated = {**_VALID_RECORD, "status": "accepted"}
    violations = find_field_violations(mutated)
    assert any("measured_by" in v for v in violations), violations


def test_accepted_status_with_measured_by_is_green() -> None:
    mutated = {
        **_VALID_RECORD,
        "status": "accepted",
        "measured_by": "tests/contract/test_x.py",
    }
    assert find_field_violations(mutated) == []


def test_gap_in_numbering_is_red() -> None:
    violations = find_numbering_violations(["0001", "0003"])
    assert any("monotonic and gap-free" in v for v in violations), violations


def test_duplicate_numbering_is_red() -> None:
    violations = find_numbering_violations(["0001", "0001", "0002"])
    assert any("duplicate" in v for v in violations), violations


def test_numbering_not_starting_at_0001_is_red() -> None:
    violations = find_numbering_violations(["0002", "0003"])
    assert any("monotonic and gap-free" in v for v in violations), violations


def test_non_4_digit_id_is_red() -> None:
    violations = find_numbering_violations(["1", "0002"])
    assert any("4-digit" in v for v in violations), violations


def test_empty_id_list_is_valid() -> None:
    assert find_numbering_violations([]) == []
