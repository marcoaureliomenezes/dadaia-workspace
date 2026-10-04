"""ADR canon: records validate ``decision-record-v1`` and ids run 0001..N, judged by the
doctor's LEDGER-ADR-SCHEMA rule (``features/specs/doctor_adr``), the one ADR authority. Size: SMALL.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.specs.doctor_adr import adr_record_issues

pytestmark = pytest.mark.contract


def _ledger(tmp_path: Path, ids: list[str], **fields: object) -> Path:
    specs = tmp_path / "specs"
    (specs / "ADRs").mkdir(parents=True)
    lines = [json.dumps({**_VALID_RECORD, **fields, "id": i}) for i in ids]
    (specs / "ADRs" / "decisions.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return specs


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
_RULED = {
    "status": "accepted",
    "measured_by": "ruff check",
    "ruling": {"date": "2026-09-30", "words": "Aprovo"},
}
_RECORD_ROWS = [
    pytest.param({}, [], id="valid"),
    pytest.param(
        {"id": _ABSENT},
        ["record is missing required field 'id'", "id None breaks 0001..N: expected 0001"],
        id="missing-id",
    ),
    *(
        pytest.param(
            {field: _ABSENT}, [f"record is missing required field {field!r}"], id=f"missing-{field}"
        )
        for field in ("ts", "title", "context", "decision", "consequences")
    ),
    pytest.param(
        {"status": "in-review"},
        [
            "record.status must be one of ['accepted', 'proposed', 'rejected', 'superseded'], got 'in-review'"
        ],
        id="unknown-status",
    ),
    pytest.param(
        {"status": "accepted"},
        ["record is missing required field 'ruling'", "record.measured_by must be of type string"],
        id="sa-adr-measured-by-pattern-refuses-real-checks#B27-2-accepted-null",
    ),
    pytest.param(
        {"status": "accepted", "measured_by": ""},
        [
            "record is missing required field 'ruling'",
            "record.measured_by is shorter than its minLength of 1",
        ],
        id="accepted-empty-measured-by",
    ),
    pytest.param({**_RULED, "measured_by": "ruff check"}, [], id="accepted-with-a-ruling"),
    pytest.param(
        {"status": "accepted", "measured_by": "ruff check"},
        ["record is missing required field 'ruling'"],
        id="0151-M1-accepted-without-ruling",
    ),
    *(
        pytest.param(
            {**_RULED, "ruling": {"date": "2026-09-30", "words": words}},
            ["record.ruling.words must not match {'pattern': '(?i)delega|in session'}"],
            id=f"0151-M1-{words}",
        )
        for words in ("Delegated to the PM", "accepted in session", "delegado ao PM")
    ),
    pytest.param(
        {**_RULED, "ruling": {"date": "2026-09-30", "words": "Q6 A na sessão"}},
        [],
        id="0151-M1-operator-sessao",
    ),
    pytest.param(
        {**_RULED, "ruling": {"date": "2026-09-30", "words": " "}},
        ["record.ruling.words value ' ' does not match \\S"],
        id="0151-M1-blank-words",
    ),
    pytest.param(
        {**_RULED, "ruling": {"date": "30/09/2026", "words": "Aprovo"}},
        ["record.ruling.date value '30/09/2026' does not match ^\\d{4}-\\d{2}-\\d{2}$"],
        id="0151-M1-date-shape",
    ),
    # The six records the 2026-09-12 audit found carried `"supersedes": []`.
    pytest.param(
        {"supersedes": []},
        ["record.supersedes must be of type ['string', 'null']"],
        id="pre-wave0-supersedes-list",
    ),
    pytest.param({"supersedes": "0005,0006,0008"}, [], id="supersedes-several"),
    pytest.param(
        {"supersedes": "0005, 0006"},
        ["record.supersedes value '0005, 0006' does not match ^\\d{4}(,\\d{4})*$"],
        id="supersedes-spaced",
    ),
]


@pytest.mark.parametrize(("change", "expected"), _RECORD_ROWS)
def test_each_record_shape_is_judged_by_the_doctor(
    change: dict[str, object], expected: list[str], tmp_path: Path
) -> None:
    """Each record shape is judged through the doctor's LEDGER-ADR-SCHEMA exactly as the row
    states — `_ledger.validate` is the one engine (ADR 0018)."""
    record = {k: v for k, v in {**_VALID_RECORD, **change}.items() if v is not _ABSENT}
    (tmp_path / "ADRs").mkdir()
    (tmp_path / "ADRs" / "decisions.jsonl").write_text(json.dumps(record) + "\n", "utf-8")
    issues = adr_record_issues(tmp_path)
    assert [i.message.removesuffix(" (ADRs/decisions.jsonl:1)") for i in issues] == expected


def test_an_unreadable_line_is_its_own_finding_and_the_next_record_is_still_read(
    tmp_path: Path,
) -> None:
    """A malformed and a non-object line each name their line; the record after them is
    still judged (here: its id is the first, so 0001..N holds)."""
    specs = _ledger(tmp_path, ["0001"])
    ledger = specs / "ADRs" / "decisions.jsonl"
    ledger.write_text("{not json\n[1]\n" + ledger.read_text("utf-8"), "utf-8")
    assert [i.message for i in adr_record_issues(specs)] == [
        "line is not valid JSON (Expecting property name enclosed in double quotes) (ADRs/decisions.jsonl:1)",
        "line is not a JSON object (ADRs/decisions.jsonl:2)",
    ]


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


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"status": "proposed"}, ["changes accepted ['0001'] without a ruling"]),
        ({"status": "superseded"}, ["changes accepted ['0001'] without a ruling"]),
        ({"status": "accepted", "measured_by": "x"}, ["record is missing required field 'ruling'", "changes accepted ['0001'] without a ruling"]),
        (_RULED, []),
        ({"status": "rejected"}, []),
    ],
)  # fmt: skip
def test_only_a_ruled_record_changes_an_accepted_one(
    tmp_path: Path, change: dict[str, object], expected: list[str]
) -> None:
    """ADR 0151 M2: every non-rejected record (born-superseded too) amending an accepted one is itself accepted with a ruling."""
    specs = _ledger(tmp_path, ["0001"], **_RULED)
    ledger = specs / "ADRs" / "decisions.jsonl"
    successor = {**_VALID_RECORD, **change, "id": "0002", "amends": "0001"}
    ledger.write_text(ledger.read_text("utf-8") + json.dumps(successor) + "\n", "utf-8")
    assert [i.message.rsplit(" (", 1)[0] for i in adr_record_issues(specs)] == expected


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
