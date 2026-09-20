"""`dadaia audit disposition|close` — an audit moves by verb (0.4.7 FR4, T-047-28).

Intent: CONTRACT — 0.4.7 FR4 (a finding's governance triple is rewritten by one verb; an
audit archives all-or-nothing: every finding terminal, one histo record appended LAST,
the directory gone; every refusal hands back one `fix:`).
Size: MEDIUM — the real CLI against a tmp_path specs tree and a tmp_path HOME.

Structural frame: `specs/audits/**` had no actor at all — dispositions, the histo record
and the directory deletion were three hand acts an agent had to remember in order, and a
half-done sweep left an audit that looked closed and was not.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.contract.test_every_block_carries_a_fix import assert_block_carries_a_runnable_fix

_runner = CliRunner()
_AUDIT = "20260101-lifecycle"
_SHA = "abc1234"


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DADAIA_CONTEXT", "dadaia-workspace")
    monkeypatch.setenv("DADAIA_SESSION_ID", "session-under-test")
    return tmp_path / "home"


def _finding(finding_id: str, pillar: str) -> dict[str, object]:
    return {
        "id": finding_id,
        "pillar": pillar,
        "severity": "LOW",
        "refs": ["specs/constitution.md"],
        "claim": "a claim",
        "evidence": "a command -> a redacted result",
        "disposition": "open",
        "release": None,
        "reason": None,
    }


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    target = tmp_path / "specs"
    audit = target / "audits" / _AUDIT
    audit.mkdir(parents=True)
    (target / "audits" / "_archive").mkdir(parents=True)
    (audit / "AUDIT.md").write_text("# Audit\n", encoding="utf-8")
    (audit / "FINDINGS.jsonl").write_text(
        "\n".join(
            json.dumps(record)
            for record in (
                _finding(f"{_AUDIT}-F001", "bugs"),
                _finding(f"{_AUDIT}-F002", "specs"),
                _finding(f"{_AUDIT}-F003", "memory"),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def _run(*args: str) -> str:
    result = _runner.invoke(app, [*args])
    assert result.exit_code == 0, result.output
    return result.output


def _refuse(*args: str) -> str:
    result = _runner.invoke(app, [*args])
    assert result.exit_code == 1, result.output
    return result.output


def _findings(specs_dir: Path) -> dict[str, dict[str, object]]:
    path = specs_dir / "audits" / _AUDIT / "FINDINGS.jsonl"
    records = [
        json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()
    ]
    return {record["id"]: record for record in records}


def _histo_lines(specs_dir: Path) -> list[str]:
    path = specs_dir / "audits" / "_archive" / "audits_histo.jsonl"
    if not path.is_file():
        return []
    return [line for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def _disposition(specs_dir: Path, finding_id: str, *args: str) -> str:
    return _run("audit", "disposition", _AUDIT, finding_id, "--specs-dir", str(specs_dir), *args)


def test_disposition_rewrites_only_the_governance_triple(home: Path, specs: Path) -> None:
    """The verb rewrites `disposition`/`release`/`reason` in place; the immutable core
    and every other finding are untouched."""
    before = _findings(specs)
    _disposition(specs, f"{_AUDIT}-F001", "--disposition", "resolved", "--release", "0.4.7")

    after = _findings(specs)
    assert after[f"{_AUDIT}-F001"]["disposition"] == "resolved"
    assert after[f"{_AUDIT}-F001"]["release"] == "0.4.7"
    assert after[f"{_AUDIT}-F001"]["claim"] == before[f"{_AUDIT}-F001"]["claim"]
    assert after[f"{_AUDIT}-F002"] == before[f"{_AUDIT}-F002"]


def _disposition_all(specs_dir: Path) -> None:
    _disposition(specs_dir, f"{_AUDIT}-F001", "--disposition", "resolved", "--release", "0.4.7")
    _disposition(specs_dir, f"{_AUDIT}-F002", "--disposition", "superseded", "--release", "0.4.7")
    _disposition(specs_dir, f"{_AUDIT}-F003", "--disposition", "deferred", "--reason", "backlogged")


def test_close_appends_one_histo_record_last_and_deletes_the_directory(
    home: Path, specs: Path
) -> None:
    """All-or-nothing: with every finding terminal, close leaves exactly one histo line
    carrying the window-end sha and the per-pillar counts, and the directory is gone."""
    _disposition_all(specs)
    _run("audit", "close", _AUDIT, "--sha", _SHA, "--specs-dir", str(specs))

    assert not (specs / "audits" / _AUDIT).exists()
    lines = _histo_lines(specs)
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["id"] == _AUDIT
    assert record["disposition"] == "resolved"
    assert record["release"] == "0.4.7"
    assert record["entry"]["sha"] == _SHA
    assert record["entry"]["pillars"] == {"bugs": 1, "specs": 1, "memory": 1}
    assert record["entry"]["dispositions"] == {"resolved": 1, "superseded": 1, "deferred": 1}
    assert "bugs 1" in (record["summary"] or "")


def test_close_refuses_while_one_finding_is_open_and_writes_nothing(
    home: Path, specs: Path
) -> None:
    """The refusal names the open finding and hands back the disposition verb."""
    _disposition(specs, f"{_AUDIT}-F001", "--disposition", "resolved", "--release", "0.4.7")
    output = _refuse("audit", "close", _AUDIT, "--sha", _SHA, "--specs-dir", str(specs))

    assert f"{_AUDIT}-F002" in output
    assert_block_carries_a_runnable_fix(output)
    assert (specs / "audits" / _AUDIT).is_dir()
    assert _histo_lines(specs) == []


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("deferred-without-reason", ["--disposition", "deferred"]),
        ("rejected-without-reason", ["--disposition", "rejected"]),
        ("resolved-without-release", ["--disposition", "resolved"]),
        ("unknown-disposition", ["--disposition", "fixed", "--release", "0.4.7"]),
    ],
)
def test_disposition_refuses_without_its_evidence(
    home: Path, specs: Path, name: str, args: list[str]
) -> None:
    """`fixed` is no longer a word: the one finding vocabulary is
    open|resolved|superseded|deferred|rejected."""
    before = _findings(specs)
    output = _refuse(
        "audit", "disposition", _AUDIT, f"{_AUDIT}-F001", "--specs-dir", str(specs), *args
    )
    assert_block_carries_a_runnable_fix(output)
    assert _findings(specs) == before


def test_an_unknown_finding_id_names_the_known_ids(home: Path, specs: Path) -> None:
    output = _refuse(
        "audit", "disposition", _AUDIT, "F999", "--disposition", "resolved",
        "--release", "0.4.7", "--specs-dir", str(specs),
    )  # fmt: skip
    assert f"{_AUDIT}-F001" in output
    assert_block_carries_a_runnable_fix(output)


def test_an_unknown_audit_dir_names_specs_audits(home: Path, specs: Path) -> None:
    output = _refuse("audit", "close", "20260101-nope", "--sha", _SHA, "--specs-dir", str(specs))
    assert "specs/audits/" in output
    assert_block_carries_a_runnable_fix(output)


@pytest.mark.parametrize("shape", ["traversal", "absolute", "nested-traversal"])
def test_an_audit_name_outside_specs_audits_is_refused_and_touches_nothing(
    tmp_path: Path, home: Path, specs: Path, shape: str
) -> None:
    """CWE-22: `audit close` DELETES the directory it resolves, so an `<audit>` argument
    that escapes `specs/audits/` would delete an operator tree. The name is confined to
    the audits directory before anything is read, resolved or removed."""
    # A VALID, fully dispositioned audit: `close` would succeed and DELETE it, so only
    # the confinement rule can save the operator's tree.
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "AUDIT.md").write_text("# Audit\n", encoding="utf-8")
    closed = dict(_finding("20260101-lifecycle-F001", "bugs"), disposition="resolved")
    closed["release"] = "0.4.7"
    (outside / "FINDINGS.jsonl").write_text(json.dumps(closed) + "\n", encoding="utf-8")
    (outside / "keep-me.txt").write_text("operator data", encoding="utf-8")

    names = {
        "traversal": "../../outside",
        "absolute": str(outside),
        "nested-traversal": f"{_AUDIT}/../../../outside",
    }
    output = _refuse("audit", "close", names[shape], "--sha", _SHA, "--specs-dir", str(specs))

    assert "specs/audits/" in output
    assert_block_carries_a_runnable_fix(output)
    assert (outside / "keep-me.txt").is_file()
    assert (specs / "audits" / _AUDIT / "FINDINGS.jsonl").is_file()


def test_the_refusal_names_the_verb_the_caller_actually_ran(home: Path, specs: Path) -> None:
    """`audit disposition` refusing an unknown directory must not hand back a
    `audit close` remedy — the fix line names the verb that failed."""
    output = _refuse(
        "audit", "disposition", "20260101-nope", f"{_AUDIT}-F001",
        "--disposition", "resolved", "--release", "0.4.7", "--specs-dir", str(specs),
    )  # fmt: skip

    assert "dadaia audit disposition" in output
    assert "dadaia audit close" not in output


def test_the_archived_record_counts_all_three_pillars_including_the_empty_ones(
    home: Path, specs: Path
) -> None:
    """One record shape whatever the window held: a pillar that found nothing is `0`,
    not absent, so a reader never has to distinguish "no findings" from "old record"."""
    for index, disposition_args in enumerate(
        (["--disposition", "resolved", "--release", "0.4.7"],) * 3
    ):
        _run(
            "audit", "disposition", _AUDIT, f"{_AUDIT}-F00{index + 1}",
            *disposition_args, "--specs-dir", str(specs),
        )  # fmt: skip
    _run("audit", "close", _AUDIT, "--sha", _SHA, "--specs-dir", str(specs))

    line = (specs / "audits" / "_archive" / "audits_histo.jsonl").read_text(encoding="utf-8")
    entry = json.loads(line.strip())["entry"]
    assert entry["pillars"] == {"bugs": 1, "specs": 1, "memory": 1}


def test_a_pillar_with_no_findings_is_reported_as_zero(
    tmp_path: Path, home: Path, specs: Path
) -> None:
    findings = specs / "audits" / _AUDIT / "FINDINGS.jsonl"
    only_bugs = dict(_finding(f"{_AUDIT}-F001", "bugs"), disposition="resolved")
    only_bugs["release"] = "0.4.7"
    findings.write_text(json.dumps(only_bugs) + "\n", encoding="utf-8")

    _run("audit", "close", _AUDIT, "--sha", _SHA, "--specs-dir", str(specs))

    line = (specs / "audits" / "_archive" / "audits_histo.jsonl").read_text(encoding="utf-8")
    entry = json.loads(line.strip())["entry"]
    assert entry["pillars"] == {"bugs": 1, "specs": 0, "memory": 0}
