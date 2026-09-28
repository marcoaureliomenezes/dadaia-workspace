"""Intent: CONTRACT — ADR canon: every ``decisions.jsonl`` record validates
``decision-record-v1`` and the ids run 0001..N, both judged by the doctor's
LEDGER-ADR-SCHEMA rule (``features/specs/doctor_adr``), the one ADR authority.
Size: SMALL — in-memory records and tmp_path ledgers; one CliRunner doctor run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.specs.doctor_adr import adr_record_issues
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
    return schema_errors(record, "ADRs/decision-record-v1")


def _ledger(tmp_path: Path, ids: list[str], **fields: object) -> Path:
    specs = tmp_path / "specs"
    (specs / "ADRs").mkdir(parents=True)
    lines = [json.dumps({**_VALID_RECORD, **fields, "id": i}) for i in ids]
    (specs / "ADRs" / "decisions.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return specs


def test_committed_inventory_may_be_legitimately_empty() -> None:
    """Discovery never raises regardless of population."""
    assert isinstance(_read_jsonl_records(_DECISIONS_PATH), list)


def test_the_committed_ledger_is_clean_under_the_doctor_rule() -> None:
    assert adr_record_issues(_REPO_ROOT / "specs") == []


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


@pytest.mark.parametrize(
    ("measured_by", "error"),
    [(None, "None is not of type 'string'"), ("", "'' should be non-empty")],
)
def test_accepted_status_without_measured_by_is_red(measured_by: object, error: str) -> None:
    """sa-adr-measured-by-pattern-refuses-real-checks#B27-2."""
    mutated = {**_VALID_RECORD, "status": "accepted", "measured_by": measured_by}
    assert find_field_violations(mutated) == [error]


def test_accepted_status_with_measured_by_is_green() -> None:
    mutated = {**_VALID_RECORD, "status": "accepted", "measured_by": "ruff check"}
    assert find_field_violations(mutated) == []


@pytest.mark.parametrize(
    ("ids", "expected"),
    [
        (
            ["0001", "0003"],
            ["ADRs/decisions.jsonl:2 id '0003' breaks 0001..N: expected 0002"],
        ),
        (
            ["0002", "0003"],
            ["ADRs/decisions.jsonl:1 id '0002' breaks 0001..N: expected 0001"],
        ),
        (["0001", "0002"], []),
        ([], []),
    ],
)
def test_the_doctor_rule_flags_the_first_id_breaking_0001_to_n(
    tmp_path: Path, ids: list[str], expected: list[str]
) -> None:
    """sa-adr-measured-by-pattern-refuses-real-checks#B27-3: a gap or a sequence not
    starting at 0001 is a LEDGER-ADR-SCHEMA finding of the consumer's own doctor."""
    issues = adr_record_issues(_ledger(tmp_path, ids))
    assert [f"{i.path} {i.description}" for i in issues] == expected


def test_doctor_admits_any_named_check_and_flags_a_duplicate_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-adr-measured-by-pattern-refuses-real-checks#B27-1 and #B27-3: `dadaia doctor
    --specs-dir` over a consumer tree accepts `measured_by: npx vitest run` and flags a
    duplicate 0049 — no library test involved."""
    monkeypatch.chdir(tmp_path)
    ids = [f"{n:04d}" for n in range(1, 50)] + ["0049"]
    specs = _ledger(tmp_path, ids, status="accepted", measured_by="npx vitest run")

    run = CliRunner().invoke(app, ["doctor", "--json", "--specs-dir", str(specs)])

    assert "id '0049' breaks 0001..N: expected 0050" in run.output, run.output
    assert "vitest" not in run.output and run.output.count("breaks 0001..N") == 1


def test_the_projected_law_names_the_doctor_and_no_measured_by_pattern() -> None:
    """sa-adr-measured-by-pattern-refuses-real-checks#B27-4."""
    law = (_REPO_ROOT / "dadaia_workspace/public/scaffold/ADRs/AGENTS.md").read_text("utf-8")
    assert (
        ".venv/bin/dadaia doctor` (`LEDGER-ADR-SCHEMA`) validates every record and the numbering"
        in law
    )
    assert "test_adr_canon" not in law and "SPEC-DOC-nnn" not in law


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
