"""Every `dadaia bugs` verb writes one governance event (0.4.7 FR2, T-047-26).

Intent: CONTRACT — 0.4.7 FR2 (a fresh store holds one row per verb whose
`record_hash` equals the committed record; a store that cannot open never fails a verb).
Size: MEDIUM — the real CLI against a tmp_path specs tree and a tmp_path HOME, one
SQLite file; no network, no git.

Structural frame: a governance record changed by hand left no trace anywhere, which is
how an invalid archived release and an archived `[-]` task reached the tree unnoticed.
The event is the trace — observability, never a gate.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()

_EVIDENCE = [
    "--solution",
    "s",
    "--evidence-loop",
    "pytest -k governance_events",
    "--evidence-seam",
    "tests/integration/cli/test_bugs_governance_events.py",
    "--evidence-diff",
    "net-neutral: test only",
]


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DADAIA_CONTEXT", "dadaia-workspace")
    monkeypatch.setenv("DADAIA_SESSION_ID", "session-under-test")
    return tmp_path / "home"


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    target = tmp_path / "specs"
    (target / "bugs").mkdir(parents=True)
    return target


def _run(*args: str) -> None:
    result = _runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output


def _append(specs_dir: Path, bug_id: str) -> None:
    _run(
        "bugs", "append", "--specs-dir", str(specs_dir), "--bug-id", bug_id,
        "--title", bug_id, "--severity", "LOW", "--surface", "bugs",
        "--component", "c", "--context", "dadaia-workspace",
        "--symptom", "s", "--repro", "r", "--expected", "e",
    )  # fmt: skip


def _events(home_dir: Path) -> list[sqlite3.Row]:
    db = home_dir / ".dadaia" / "state" / "telemetry" / "telemetry.sqlite"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM governance_events ORDER BY ts, verb").fetchall()
    finally:
        conn.close()


def _hash_of(specs_dir: Path, bug_id: str, *, archived: bool = False) -> str:
    name = "_archive/bugs_histo.jsonl" if archived else "BUGS.jsonl"
    for line in (specs_dir / "bugs" / name).read_text(encoding="utf-8").split("\n"):
        if line.strip() and json.loads(line)["id"] == bug_id:
            return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()
    raise AssertionError(f"{bug_id} not found in {name}")


def test_the_seven_bugs_verbs_leave_seven_events_hashing_the_committed_record(
    home: Path, specs: Path
) -> None:
    """One verb, one event: the row names the ledger, the record and the verb, and its
    `record_hash` is the sha256 of the line the verb left on disk."""
    _append(specs, "b-resolve")
    _run(
        "bugs", "update", "b-resolve", "--set", "audited=20260913-window", "--specs-dir", str(specs)
    )
    _run("bugs", "resolve", "b-resolve", "--cause", "c", "--caused-by", "none",
         "--resolved-release", "0.4.7", *_EVIDENCE, "--specs-dir", str(specs))  # fmt: skip
    resolved_hash = _hash_of(specs, "b-resolve")

    _append(specs, "b-supersede")
    _run("bugs", "supersede", "b-supersede", "--by", "b-resolve", "--specs-dir", str(specs))
    _append(specs, "b-defer")
    _run("bugs", "defer", "b-defer", "--reason", "later", "--specs-dir", str(specs))
    _append(specs, "b-reject")
    _run("bugs", "reject", "b-reject", "--reason", "not a bug", "--specs-dir", str(specs))

    _run("bugs", "archive", "--now", "2027-01-01T00:00:00Z", "--specs-dir", str(specs))
    archived_hash = _hash_of(specs, "b-resolve", archived=True)

    rows = _events(home)
    verbs = [row["verb"] for row in rows]

    assert verbs.count("append") == 4
    for verb in ("update", "resolve", "supersede", "defer", "reject", "archive"):
        assert verbs.count(verb) >= 1, verbs
    assert {row["ledger"] for row in rows} == {"bugs"}
    assert {row["context"] for row in rows} == {"dadaia-workspace"}
    assert {row["session_id"] for row in rows} == {"session-under-test"}

    by_verb = {row["verb"]: row for row in rows}
    assert by_verb["resolve"]["record_id"] == "b-resolve"
    assert by_verb["resolve"]["record_hash"] == resolved_hash
    archive_rows = {row["record_id"]: row for row in rows if row["verb"] == "archive"}
    assert set(archive_rows) == {"b-resolve", "b-supersede", "b-defer", "b-reject"}
    assert archive_rows["b-resolve"]["record_hash"] == archived_hash
    assert len({row["event_id"] for row in rows}) == len(rows)


def test_a_verb_still_succeeds_when_the_event_store_cannot_be_opened(
    home: Path, specs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An event is observability, never a gate: with the store unopenable the record is
    written and the verb exits 0."""
    monkeypatch.setenv("HOME", "/proc/self/cannot-write-here")

    _append(specs, "b-degraded")

    assert '"id": "b-degraded"' in (specs / "bugs" / "BUGS.jsonl").read_text(encoding="utf-8")
