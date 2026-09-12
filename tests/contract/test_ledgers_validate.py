"""Every committed governance record validates (0.4.7 FR6/FR7, T-047-03).

Intent: CONTRACT — T-047-03 (SPEC 0.4.7 FR6): the `ledgers` section of `dadaia
doctor` validates every committed governance record against its ONE public schema —
`decisions.jsonl`, `BACKLOG.json`, `BUGS.jsonl`, every audit `FINDINGS.jsonl` and the
three `_histo.jsonl` histories — emitting one `LEDGER-<NAME>-SCHEMA` ERROR per invalid
record, located `path:line` (relative, POSIX).
Size: SMALL — fixture trees under tmp_path plus one in-process read of this repo's
own specs/; no subprocess, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.ledgers import build_ledgers_context, ledger_issues

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]

_VALID_ADR = {
    "id": "0001",
    "ts": "2026-08-28T12:00:00Z",
    "title": "A fixture decision",
    "status": "proposed",
    "context": "Fixture context.",
    "decision": "We will do the fixture thing.",
    "consequences": "+ benefit\n- cost",
    "measured_by": None,
    "supersedes": None,
    "amends": None,
}
_VALID_BACKLOG = {
    "schema": "backlog-v1",
    "active": [
        {
            "id": "a-fixture-item",
            "title": "A fixture item",
            "opened": "2026-09-12",
            "status": "candidate",
            "description": "Fixture description.",
            "provenance": "fixture",
        }
    ],
}
_VALID_BUG = {
    "id": "a-fixture-bug",
    "ts": "2026-09-12T00:00:00Z",
    "reported_by": "software-engineer",
    "title": "a-fixture-bug",
    "severity": "LOW",
    "surface": "specs",
    "component": "fixture",
    "context": "fixture",
    "symptom": "fixture",
    "repro": "fixture",
    "expected": "fixture",
    "status": "open",
    "cause": None,
    "caused_by": None,
    "lineage_source": None,
    "registration_commit": None,
    "registration_granularity": None,
    "resolved_commit": None,
    "resolution_granularity": None,
    "resolved_release": None,
    "audited": None,
}
_VALID_FINDING = {
    "id": "fixture-F001",
    "pillar": "specs",
    "severity": "LOW",
    "refs": ["specs/AGENTS.md"],
    "claim": "fixture claim",
    "evidence": "fixture evidence",
    "disposition": "open",
    "release": None,
    "reason": None,
}


def _valid_histo(disposition: str) -> dict[str, object]:
    return {
        "id": "a-fixture-slug",
        "ts": "2026-09-12T00:00:00Z",
        "disposition": disposition,
        "release": "0.4.7",
        "reason": None,
        "summary": "fixture",
        "entry": None,
    }


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, list):
        path.write_text("".join(json.dumps(record) + "\n" for record in payload), encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_tree(root: Path, *, valid: bool) -> Path:
    specs = root / "specs"
    adr = dict(_VALID_ADR) if valid else {**_VALID_ADR, "supersedes": []}
    backlog = _VALID_BACKLOG if valid else {**_VALID_BACKLOG, "schema": "backlog-v0"}
    bug = dict(_VALID_BUG) if valid else {**_VALID_BUG, "severity": "BLOCKER"}
    finding = dict(_VALID_FINDING) if valid else {**_VALID_FINDING, "disposition": "done"}
    histo = _valid_histo("delivered")
    legacy = {
        "by": "migration",
        "disposition": "DELIVERED",
        "entry_md": None,
        "id": "x",
        "reason": None,
        "release": "v0.9.0",
        "ts": "2026-08-14",
    }

    _write(specs / "ADRs" / "decisions.jsonl", [adr])
    _write(specs / "backlog" / "BACKLOG.json", backlog)
    _write(specs / "bugs" / "BUGS.jsonl", [bug])
    _write(specs / "audits" / "20260912-fixture" / "FINDINGS.jsonl", [finding])
    _write(
        specs / "backlog" / "_archive" / "backlog_histo.jsonl",
        [histo if valid else legacy],
    )
    _write(
        specs / "audits" / "_archive" / "audits_histo.jsonl",
        [_valid_histo("resolved") if valid else {"ts": "x", "event": "archived", "data": {}}],
    )
    _write(
        specs / "releases" / "_archive" / "releases_histo.jsonl",
        [_valid_histo("delivered") if valid else {"ts": "x", "event": "note", "data": {}}],
    )
    return specs


_EXPECTED_CODES = (
    "LEDGER-ADR-SCHEMA",
    "LEDGER-BACKLOG-SCHEMA",
    "LEDGER-BUGS-SCHEMA",
    "LEDGER-FINDINGS-SCHEMA",
    "LEDGER-BACKLOG-HISTO-SCHEMA",
    "LEDGER-AUDITS-HISTO-SCHEMA",
    "LEDGER-RELEASES-HISTO-SCHEMA",
)


def test_one_invalid_record_per_ledger_is_one_located_error_each(tmp_path: Path) -> None:
    """(a) a fixture tree with one invalid record per ledger: every ledger reports its
    own LEDGER-*-SCHEMA error, each located `path:line` relative to specs/."""
    specs = _build_tree(tmp_path, valid=False)
    issues = ledger_issues(specs)

    by_code = {issue.code: issue for issue in issues}
    assert set(_EXPECTED_CODES) <= set(by_code), sorted(by_code)
    for code in _EXPECTED_CODES:
        issue = by_code[code]
        assert not Path(issue.path).is_absolute(), issue
        assert "\\" not in issue.path, issue
        assert issue.unit.startswith(issue.path + ":"), issue
        assert issue.unit.rsplit(":", 1)[1].isdigit(), issue


def test_a_valid_fixture_tree_disqualifies_no_record(tmp_path: Path) -> None:
    """(b) every record valid ⇒ zero issues and a non-zero denominator."""
    specs = _build_tree(tmp_path, valid=True)
    assert ledger_issues(specs) == []
    assert build_ledgers_context(specs).total_records == 7


def test_a_histo_disposition_outside_the_ledgers_subset_is_an_error(tmp_path: Path) -> None:
    """The per-ledger subset is the validator's parameter, not a third schema file:
    `releases_histo` accepts `delivered` only."""
    specs = _build_tree(tmp_path, valid=True)
    _write(specs / "releases" / "_archive" / "releases_histo.jsonl", [_valid_histo("rejected")])
    codes = [issue.code for issue in ledger_issues(specs)]
    assert codes == ["LEDGER-RELEASES-HISTO-SCHEMA"], codes


def test_the_real_tree_has_no_invalid_governance_record() -> None:
    """(c) this repo's own specs/: the ADR, backlog and audit-finding ledgers validate
    today (Wave 0 repaired those records).

    The three `_histo.jsonl` histories are included since T-047-04 migrated them to
    `histo-record-v1` (136/23/103 records). One code family is EXCLUDED, with its own
    repair task:

    * `LEDGER-BUGS-SCHEMA` — this reader's FIRST pass over the committed bug ledger
      found 15 records that never validated `bug-record-v1`: four `surface` values
      outside the enum (`reports`, `tmp_gc`, `spec_artifacts`) and eleven
      `evidence_diff` strings written without the `net-negative|net-neutral|
      net-positive:` prefix the schema requires. They are DATA, not a rule defect
      (nothing had ever read them), and their repair rides T-047-08, which already
      owns `specs/bugs/BUGS.jsonl` and the bug schema. The count below is a ratchet:
      it may only go down.
    """
    issues = ledger_issues(_REPO_ROOT / "specs")
    bugs = [i for i in issues if i.code == "LEDGER-BUGS-SCHEMA"]
    others = [i for i in issues if i.code != "LEDGER-BUGS-SCHEMA"]

    assert others == [], [f"{i.code} {i.unit} {i.message}" for i in others]
    assert len(bugs) <= 15, [f"{i.unit} {i.message}" for i in bugs]


def test_the_doctor_ledgers_section_carries_the_schema_findings(tmp_path: Path) -> None:
    """The rules are contributed to the ONE doctor: an invalid record surfaces in the
    `ledgers` section of `dadaia doctor --json`, scored against the same `records`
    unit as the backlog rules."""
    from typer.testing import CliRunner

    from dadaia_workspace.cli.main import app

    specs = _build_tree(tmp_path, valid=False)
    result = CliRunner().invoke(
        app, ["doctor", "--specs-dir", str(specs), "--source-root", str(_REPO_ROOT), "--json"]
    )
    section = json.loads(result.stdout)["sections"]["ledgers"]
    codes = {finding["code"] for finding in section["findings"]}

    assert set(_EXPECTED_CODES) <= codes, sorted(codes)
    assert section["compliance"]["percent"] < 100
    assert result.exit_code == 1
