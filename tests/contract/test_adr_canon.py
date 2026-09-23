"""ADR canon contract — specs/ADRs/ (v0.5.0 specs-canon closure, operator ruling
2026-08-28).

Intent: CONTRACT — v0.5.0 specs-canon closure

Validates the specs/ADRs/ decision-record canon this task introduces: JSONL, one
record per line (dadaia_workspace.core.models.adr.AdrRecord), monotonic gap-free ids
over ``specs/ADRs/decisions.jsonl`` (0.4.7 FR8 retired the ``_superseded/`` lane: a
superseded decision is retired IN PLACE with ``status: superseded``, named by its
successor's ``supersedes`` — the second file shipped empty for the whole life of the
canon and split one inventory in two), the status enum {proposed, accepted, rejected,
superseded}, and the operator-only acceptance law (``accepted`` requires a RESOLVABLE
``measured_by`` — a decision nobody can run is not a principle, it is prose).

Every RED condition below is proven on an in-memory mutation fixture, never a real
file on disk. The committed file may legitimately be EMPTY (no real principle-level
decision has been authored yet under the JSONL canon — the 28 mechanical, auto-
generated markdown ADRs this repository shipped at authoring time were deleted as
non-canon; a decision record is now authored only when a real principle-level
decision needs one, never as a backfill) — every check below holds vacuously true
over an empty inventory.

The record SHAPE is no longer hand-rolled here (0.4.7 FR6, T-047-03): the
``find_field_violations``/``_record_violations`` copy of the required-field, status-enum
and acceptance-law checks is DELETED and every shape assertion now runs
``decision-record-v1.schema.json`` — the same schema the ``ledgers`` section of
``dadaia doctor`` runs over the committed file, so a schema change can no longer pass
here and fail there (the exact drift that let six pre-Wave-0 records violate their own
schema while every check was green). ``find_numbering_violations`` stays: monotonic
gap-free numbering is a property of the SET of records, which no per-record schema can
express.

No CLI verb and no doctor rule beyond that section is introduced by this file (item 4's own
scope) — a pytest-only contract over the files already on disk plus in-memory
fixtures. Supersedes the pre-v0.5.0-specs-canon-closure markdown-ADR contract
(``NNNN-<slug>.md``, one file per decision) entirely — that machinery is deleted with
this rewrite.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.schemas import schema_errors

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "specs" / "ADRs"
_DECISIONS_PATH = _ADR_DIR / "decisions.jsonl"


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
    """Every ``decision-record-v1`` violation for one record, as messages — the ONE
    validator, shared by the committed-file assertion and every mutation fixture."""
    return schema_errors(record, "ADRs/decision-record-v1")


def find_numbering_violations(ids: list[str]) -> list[str]:
    """Pure validator over a *list of id strings only* — numbering never needs the
    full record body."""
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
# The real, committed inventory — decisions.jsonl.
# ---------------------------------------------------------------------------------------


def test_committed_inventory_may_be_legitimately_empty() -> None:
    """Discovery itself must never raise regardless of population; every other check
    in this module holds vacuously true when the discovered set is empty."""
    assert isinstance(_read_jsonl_records(_DECISIONS_PATH), list)


def test_every_committed_record_carries_every_required_field_and_a_valid_status() -> None:
    for record in _read_jsonl_records(_DECISIONS_PATH):
        violations = find_field_violations(record)
        assert violations == [], violations


def test_committed_ids_are_monotonic_gap_free_and_duplicate_free() -> None:
    """decisions.jsonl's ids must be 1..N gap-free — a superseded record is retired in
    place, so the one file always holds one unbroken sequence."""
    ids = [str(record.get("id")) for record in _read_jsonl_records(_DECISIONS_PATH)]
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
    assert any("'in-review' is not one of" in v for v in violations), violations


def test_accepted_status_without_measured_by_is_red() -> None:
    mutated = {**_VALID_RECORD, "status": "accepted"}
    violations = find_field_violations(mutated)
    assert any("None is not of type 'string'" in v for v in violations), violations


def test_accepted_status_with_measured_by_is_green() -> None:
    mutated = {
        **_VALID_RECORD,
        "status": "accepted",
        "measured_by": "pytest tests/contract/test_x.py",
    }
    assert find_field_violations(mutated) == []


@pytest.mark.parametrize(
    "measured_by",
    [
        "pytest tests/contract/test_x.py",
        "pytest tests/unit/a.py tests/unit/b.py",
        "pytest tests/contract/test_test_suite_ratchets.py -k v31",
        "lint-imports --config setup.cfg --no-cache",
        "lint-imports --config setup.cfg --no-cache \u2014 contract features-no-subprocess",
        "lint-imports --config setup.cfg --no-cache \u2014 contracts core-no-upper-layers, x",
        "SPEC-DOC-045",
        "SPEC-DOC-046 \u2014 the live release's state document is named _RELEASE.json",
        "WS-dadaia-slop",
        "BL-SHAPE over BACKLOG.json",
        "RELEASE-TREE-PHASE over every committed release-state document",
        "LEDGER-ADR-SCHEMA over specs/ADRs/decisions.jsonl",
        "dadaia doctor \u2014 the ledgers section is 100 %",
        "dadaia bugs status \u2014 both records terminal `deferred`",
    ],
)
def test_resolvable_measured_by_is_green(measured_by: str) -> None:
    """Intent: CONTRACT — 0.4.7 FR8. Every form a real accepted record uses today
    resolves to a command, a doctor code or a ledger code someone can run."""
    mutated = {**_VALID_RECORD, "status": "accepted", "measured_by": measured_by}
    assert find_field_violations(mutated) == [], (measured_by, find_field_violations(mutated))


def test_accepted_status_with_prose_measured_by_is_red() -> None:
    """Intent: CONTRACT — 0.4.7 FR8. ADR 0005-0009 shipped `accepted` naming a
    sentence ('specs doctor release rules + dd-gitflow-default conformance in
    audits') that resolved to no runnable check; the acceptance law required only
    non-emptiness, so prose passed. `measured_by` now matches a resolvable pattern
    or the record is not acceptable."""
    mutated = {
        **_VALID_RECORD,
        "status": "accepted",
        "measured_by": "specs doctor release rules + dd-gitflow-default conformance in audits",
    }
    violations = find_field_violations(mutated)
    assert any("does not match" in v for v in violations), violations


def test_prose_measured_by_on_a_proposed_record_is_green() -> None:
    """Intent: CONTRACT — 0.4.7 FR8. The pattern is part of the ACCEPTANCE law: a
    `proposed` record is still a draft and may name its check in prose."""
    mutated = {**_VALID_RECORD, "measured_by": "some prose nobody can run"}
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


def test_the_pre_wave0_record_shape_is_red() -> None:
    """The six records the 2026-09-12 audit found violating their own schema carried
    `"supersedes": []` (`git show f915b3db^:specs/ADRs/decisions.jsonl`). The hand-rolled
    validator this file used to carry checked presence only, so it called them clean —
    the schema does not."""
    violations = find_field_violations({**_VALID_RECORD, "supersedes": []})
    assert any("[] is not of type" in v for v in violations), violations


def test_supersedes_admits_the_list_one_decision_retiring_several_needs() -> None:
    """A single-id `supersedes` left four retired records with no successor naming
    them: the decision that replaced all of them could only cite one. The ascending
    comma-separated list is what a reader follows from a dead record to the live one."""
    assert find_field_violations({**_VALID_RECORD, "supersedes": "0005,0006,0008"}) == []
    assert find_field_violations({**_VALID_RECORD, "supersedes": "0005, 0006"}) != []


def test_every_superseded_record_is_named_by_some_successor() -> None:
    """A `superseded` record whose successor nobody can find is a dead end for every
    reader the status was meant to redirect."""
    records = _read_jsonl_records(_DECISIONS_PATH)
    named = {
        adr_id
        for record in records
        for adr_id in (record.get("supersedes") or "").split(",")
        if adr_id
    }
    orphans = sorted(
        r["id"] for r in records if r["status"] == "superseded" and r["id"] not in named
    )
    assert orphans == [], f"superseded with no successor naming them: {orphans}"
