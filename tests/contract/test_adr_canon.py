"""Intent: CONTRACT — ADR canon: records validate ``decision-record-v1`` and ids run 0001..N, judged by the
doctor's LEDGER-ADR-SCHEMA rule (``features/specs/doctor_adr``), the one ADR authority. Size: SMALL.
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


def _ledger(tmp_path: Path, ids: list[str], **fields: object) -> Path:
    specs = tmp_path / "specs"
    (specs / "ADRs").mkdir(parents=True)
    lines = [json.dumps({**_VALID_RECORD, **fields, "id": i}) for i in ids]
    (specs / "ADRs" / "decisions.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return specs


def test_the_committed_ledger_is_clean_under_the_doctor_rule() -> None:
    assert adr_record_issues(_REPO_ROOT / "specs") == []


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


_ABSENT = object()
_RECORD_ROWS = [
    pytest.param({}, [], id="valid"),
    *(
        pytest.param({field: _ABSENT}, [f"'{field}' is a required property"], id=f"missing-{field}")
        for field in ("id", "ts", "title", "context", "decision", "consequences")
    ),
    pytest.param(
        {"status": "in-review"},
        ["'in-review' is not one of ['proposed', 'accepted', 'rejected', 'superseded']"],
        id="unknown-status",
    ),
    pytest.param(
        {"status": "accepted"},
        ["None is not of type 'string'"],
        id="sa-adr-measured-by-pattern-refuses-real-checks#B27-2-accepted-null",
    ),
    pytest.param(
        {"status": "accepted", "measured_by": ""},
        ["'' should be non-empty"],
        id="accepted-empty-measured-by",
    ),
    pytest.param(
        {"status": "accepted", "measured_by": "ruff check"}, [], id="accepted-with-measured-by"
    ),
    # The six records the 2026-09-12 audit found carried `"supersedes": []`.
    pytest.param(
        {"supersedes": []}, ["[] is not of type 'string', 'null'"], id="pre-wave0-supersedes-list"
    ),
    pytest.param({"supersedes": "0005,0006,0008"}, [], id="supersedes-several"),
    pytest.param(
        {"supersedes": "0005, 0006"},
        ["'0005, 0006' does not match '^\\\\d{4}(,\\\\d{4})*$'"],
        id="supersedes-spaced",
    ),
]


@pytest.mark.parametrize(("change", "expected"), _RECORD_ROWS)
def test_each_record_shape_is_judged_by_the_schema(
    change: dict[str, object], expected: list[str]
) -> None:
    """Each record shape is judged by decision-record-v1 exactly as the row states ."""
    record = {k: v for k, v in {**_VALID_RECORD, **change}.items() if v is not _ABSENT}
    assert schema_errors(record, "ADRs/decision-record-v1") == expected


@pytest.mark.parametrize(
    ("ids", "expected"),
    [
        (
            ["0001", "0003"],
            ["id '0003' breaks 0001..N: expected 0002 (ADRs/decisions.jsonl:2)"],
        ),
        (
            ["0002", "0003"],
            ["id '0002' breaks 0001..N: expected 0001 (ADRs/decisions.jsonl:1)"],
        ),
        (["0001", "0002"], []),
        ([], []),
    ],
)
def test_the_doctor_rule_flags_the_first_id_breaking_0001_to_n(
    tmp_path: Path, ids: list[str], expected: list[str]
) -> None:
    """sa-adr-measured-by-pattern-refuses-real-checks#B27-3: a gap or a start past 0001 is a LEDGER-ADR-SCHEMA finding."""
    issues = adr_record_issues(_ledger(tmp_path, ids))
    assert [i.message for i in issues] == expected


def test_doctor_admits_any_named_check_and_flags_a_duplicate_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-adr-measured-by-pattern-refuses-real-checks#B27-1 and #B27-3: doctor accepts `npx vitest run`, flags a duplicate 0049."""
    monkeypatch.chdir(tmp_path)
    ids = [f"{n:04d}" for n in range(1, 50)] + ["0049"]
    specs = _ledger(tmp_path, ids, status="accepted", measured_by="npx vitest run")

    run = CliRunner().invoke(app, ["doctor", "--json", "--specs-dir", str(specs)])

    assert "id '0049' breaks 0001..N: expected 0050" in run.output, run.output
    assert "vitest" not in run.output and run.output.count("breaks 0001..N") == 1


def test_the_projected_law_names_the_doctor_and_no_measured_by_pattern() -> None:
    """sa-adr-measured-by-pattern-refuses-real-checks#B27-4: the ADR law names the doctor rule, never a test or pattern."""
    law = (_REPO_ROOT / "dadaia_workspace/public/scaffold/ADRs/AGENTS.md").read_text("utf-8")
    assert (
        ".venv/bin/dadaia doctor` (`LEDGER-ADR-SCHEMA`) validates every record and the numbering"
        in law
    )
    assert "test_adr_canon" not in law and "SPEC-DOC-nnn" not in law


def test_every_superseded_record_is_named_by_some_successor() -> None:
    """Every committed `superseded` record is named by some successor's `supersedes`."""
    lines = (
        (_REPO_ROOT / "specs" / "ADRs" / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    )
    records = [json.loads(line) for line in lines if line.strip()]
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
