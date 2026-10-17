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
from tests.helpers.oslib import read_text, write_text
from tests.helpers.oslib import run as os_run
from tests.helpers.oslib import write_text as os_write_text


def _ledger(tmp_path: Path, ids: list[str], **fields: object) -> Path:
    specs = tmp_path / "specs"
    (specs / "ADRs").mkdir(parents=True)
    lines = [json.dumps({**_VALID_RECORD, **fields, "id": i}) for i in ids]
    write_text(specs / "ADRs" / "decisions.jsonl", "\n".join(lines) + "\n")
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
    # An empty `supersedes` list is refused.
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
    states — `_ledger.validate` is the one engine."""
    record = {k: v for k, v in {**_VALID_RECORD, **change}.items() if v is not _ABSENT}
    (tmp_path / "ADRs").mkdir()
    os_write_text(tmp_path / "ADRs" / "decisions.jsonl", json.dumps(record) + "\n")
    issues = adr_record_issues(tmp_path)
    assert [i.message.removesuffix(" (ADRs/decisions.jsonl:1)") for i in issues] == expected


def test_an_unreadable_line_is_its_own_finding_and_the_next_record_is_still_read(
    tmp_path: Path,
) -> None:
    """A malformed and a non-object line each name their line; the record after them is
    still judged (here: its id is the first, so 0001..N holds)."""
    specs = _ledger(tmp_path, ["0001"])
    ledger = specs / "ADRs" / "decisions.jsonl"
    os_write_text(ledger, "{not json\n[1]\n" + read_text(ledger))
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
    """A gap or a start past 0001 is a LEDGER-ADR-SCHEMA finding."""
    issues = adr_record_issues(_ledger(tmp_path, ids))
    assert [i.message for i in issues] == expected


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"status": "proposed"}, ["changes accepted ['0001'] without a ruling"]),
        ({"status": "superseded"}, ["changes accepted ['0001'] without a ruling"]),
        ({"status": "accepted", "measured_by": "x"}, ["record is missing required field 'ruling'", "changes accepted ['0001'] without a ruling"]),
        (_RULED, []),
        ({**_RULED, "status": "superseded"}, []),  # a ruled record, superseded later
        ({"status": "rejected"}, []),
    ],
)  # fmt: skip
def test_only_a_ruled_record_changes_an_accepted_one(
    tmp_path: Path, change: dict[str, object], expected: list[str]
) -> None:
    """Every non-rejected record (born-superseded too) amending an accepted one is itself accepted
    with a ruling."""
    specs = _ledger(tmp_path, ["0001"], **_RULED)
    ledger = specs / "ADRs" / "decisions.jsonl"
    successor = {**_VALID_RECORD, **change, "id": "0002", "amends": "0001"}
    os_write_text(ledger, read_text(ledger) + json.dumps(successor) + "\n")
    assert [i.message.rsplit(" (", 1)[0] for i in adr_record_issues(specs)] == expected


@pytest.mark.medium
def test_doctor_admits_any_named_check_and_flags_a_duplicate_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Doctor accepts any named check (`npx vitest run`) and flags a duplicate record id."""
    monkeypatch.chdir(tmp_path)
    ids = [f"{n:04d}" for n in range(1, 50)] + ["0049"]
    specs = _ledger(tmp_path, ids, status="accepted", measured_by="npx vitest run")

    run = CliRunner().invoke(app, ["doctor", "--json", "--specs-dir", str(specs)])

    assert "id '0049' breaks 0001..N: expected 0050" in run.output, run.output
    assert "vitest" not in run.output and run.output.count("breaks 0001..N") == 1


def _options_ledger(tmp_path: Path, last: str, **fields: object) -> Path:
    """A gap-free ledger 0001..`last`; only the last record carries `fields`."""
    specs = _ledger(tmp_path, [f"{n:04d}" for n in range(1, int(last) + 1)])
    ledger = specs / "ADRs" / "decisions.jsonl"
    *head, _ = read_text(ledger).splitlines()
    tail = json.dumps({**_VALID_RECORD, **fields, "id": last})
    os_write_text(ledger, "\n".join([*head, tail]) + "\n")
    return specs


_OPTIONS = [
    {"name": "keep", "tradeoff": "no churn", "rejected_because": "leaves the bug"},
    {"name": "rebuild", "tradeoff": "one more diff", "rejected_because": "n/a"},
]


def test_a_record_above_0246_without_options_is_refused(tmp_path: Path) -> None:
    """A record numbered above 0246 must carry `options`."""
    issues = adr_record_issues(_options_ledger(tmp_path, "0247"))
    assert [(i.code, i.message) for i in issues] == [
        (
            "LEDGER-ADR-SCHEMA",
            "record is missing required field 'options' (ADRs/decisions.jsonl:247)",
        )
    ]


def test_a_record_above_0246_with_two_options_passes(tmp_path: Path) -> None:
    assert adr_record_issues(_options_ledger(tmp_path, "0247", options=_OPTIONS)) == []


def test_a_record_0246_and_below_needs_no_options(tmp_path: Path) -> None:
    """0246 was accepted without `options`; it still validates."""
    assert adr_record_issues(_options_ledger(tmp_path, "0246")) == []


@pytest.mark.parametrize(
    "options",
    [
        _OPTIONS[:1],
        [_OPTIONS[0], {"name": "rebuild", "tradeoff": "one more diff"}],
    ],
    ids=["one-option", "missing-rejected_because"],
)
def test_options_below_two_or_missing_a_field_are_refused(
    tmp_path: Path, options: list[dict]
) -> None:
    issues = adr_record_issues(_options_ledger(tmp_path, "0247", options=options))
    assert [i.code for i in issues] == ["LEDGER-ADR-SCHEMA"]


def _tracked_repo(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    """A real git repo tracking one test file, its specs ledger holding *records*."""
    os_run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "tests").mkdir()
    write_text(tmp_path / "tests" / "test_x.py", "def test_one():\n    pass\n")
    specs = tmp_path / "specs"
    (specs / "ADRs").mkdir(parents=True)
    write_text(
        specs / "ADRs" / "decisions.jsonl",
        "".join(json.dumps({**_VALID_RECORD, **r}) + "\n" for r in records),
    )
    os_run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    return specs


def test_an_accepted_measured_by_must_resolve_and_only_accepted_records_are_judged(
    tmp_path: Path,
) -> None:
    from dadaia_workspace.features.specs.doctor_adr import unresolved_measured_by

    missing = "tests/missing.py"
    specs = _tracked_repo(
        tmp_path,
        [
            {"id": "0001", "status": "accepted", "measured_by": missing},
            {"id": "0002", "status": "accepted", "measured_by": "tests/test_x.py::test_one"},
            {"id": "0003", "status": "accepted", "measured_by": "tests/test_x.py::test_gone"},
            {"id": "0004", "status": "superseded", "measured_by": missing},
            {"id": "0005", "status": "proposed", "measured_by": missing},
            {"id": "0006", "status": "rejected", "measured_by": missing},
        ],
    )
    assert unresolved_measured_by(specs) == [
        ("0001", missing),
        ("0003", "tests/test_x.py::test_gone"),
    ]


def test_a_job_resolves_only_as_a_workflow_node_id_and_a_code_only_if_the_doctor_owns_it(
    tmp_path: Path,
) -> None:
    from dadaia_workspace.features.specs.doctor_adr import unresolved_measured_by

    specs = _tracked_repo(
        tmp_path,
        [
            {"id": "0001", "status": "accepted", "measured_by": "the doctor flags it"},
            {"id": "0002", "status": "accepted", "measured_by": ".github/workflows/ci.yml::doctor"},
            {"id": "0003", "status": "accepted", "measured_by": "MEM-NARRATIVE-1"},
            {"id": "0004", "status": "accepted", "measured_by": "ZZ-GHOST"},
            {
                "id": "0005",
                "status": "accepted",
                "measured_by": "tests/test_y.py::TestFoo::test_bar",
            },
            {
                "id": "0006",
                "status": "accepted",
                "measured_by": "tests/test_y.py::TestFoo::test_no",
            },
        ],
    )
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    write_text(tmp_path / ".github" / "workflows" / "ci.yml", "jobs:\n  doctor:\n    runs-on: x\n")
    write_text(
        tmp_path / "tests" / "test_y.py",
        'CODE = "ZZ-GHOST"\n\n\nclass TestFoo:\n    def test_bar(self):\n        pass\n',
    )
    os_run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    assert unresolved_measured_by(specs) == [
        ("0001", "the doctor flags it"),
        ("0004", "ZZ-GHOST"),
        ("0006", "tests/test_y.py::TestFoo::test_no"),
    ]
