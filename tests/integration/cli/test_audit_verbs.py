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

import hashlib
import json
import sqlite3
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


def _events(home_dir: Path) -> list[sqlite3.Row]:
    db = home_dir / ".dadaia" / "state" / "telemetry" / "telemetry.sqlite"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM governance_events ORDER BY ts, verb").fetchall()
    finally:
        conn.close()


def _disposition(specs_dir: Path, finding_id: str, *args: str) -> str:
    return _run("audit", "disposition", _AUDIT, finding_id, "--specs-dir", str(specs_dir), *args)


def test_disposition_rewrites_only_the_governance_triple_and_writes_one_event(
    home: Path, specs: Path
) -> None:
    """The verb rewrites `disposition`/`release`/`reason` in place; the immutable core
    and every other finding are untouched; one event names the finding."""
    before = _findings(specs)
    _disposition(specs, f"{_AUDIT}-F001", "--disposition", "resolved", "--release", "0.4.7")

    after = _findings(specs)
    assert after[f"{_AUDIT}-F001"]["disposition"] == "resolved"
    assert after[f"{_AUDIT}-F001"]["release"] == "0.4.7"
    assert after[f"{_AUDIT}-F001"]["claim"] == before[f"{_AUDIT}-F001"]["claim"]
    assert after[f"{_AUDIT}-F002"] == before[f"{_AUDIT}-F002"]

    rows = [row for row in _events(home) if row["verb"] == "disposition"]
    assert len(rows) == 1
    assert rows[0]["ledger"] == "audits"
    assert rows[0]["record_id"] == f"{_AUDIT}-F001"


def _disposition_all(specs_dir: Path) -> None:
    _disposition(specs_dir, f"{_AUDIT}-F001", "--disposition", "resolved", "--release", "0.4.7")
    _disposition(specs_dir, f"{_AUDIT}-F002", "--disposition", "superseded", "--release", "0.4.7")
    _disposition(specs_dir, f"{_AUDIT}-F003", "--disposition", "deferred", "--reason", "backlogged")


def test_close_appends_one_histo_record_last_and_deletes_the_directory(
    home: Path, specs: Path
) -> None:
    """All-or-nothing: with every finding terminal, close leaves exactly one histo line
    carrying the window-end sha and the per-pillar counts, the directory is gone, and one
    event hashes that line."""
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

    rows = [row for row in _events(home) if row["verb"] == "close"]
    assert len(rows) == 1
    assert rows[0]["record_id"] == _AUDIT
    assert rows[0]["record_hash"] == hashlib.sha256(lines[0].encode("utf-8")).hexdigest()


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
