"""Every `dadaia release` verb writes one governance event (0.4.7 FR2/FR5, T-047-29).

Intent: CONTRACT — 0.4.7 FR5 (`release new|phase|rc-archive|archive` each leave one
`releases` event hashing the `_RELEASE.json` they just wrote; `archive` succeeds on a
release closed by the verb, with no hand-set milestone anywhere).
Size: MEDIUM — the real CLI against a tmp_path specs tree and a tmp_path HOME.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()
_SHA = "a" * 40


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DADAIA_CONTEXT", "dadaia-workspace")
    monkeypatch.setenv("DADAIA_SESSION_ID", "session-under-test")
    return tmp_path / "home"


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    target = tmp_path / "specs"
    (target / "releases").mkdir(parents=True)
    (target / "bugs").mkdir()
    return target


def _run(specs_dir: Path, *args: str) -> str:
    result = _runner.invoke(app, ["release", *args, "--specs-dir", str(specs_dir)])
    assert result.exit_code == 0, result.output
    return result.output


def _approve(specs_dir: Path, release: str) -> None:
    rdir = specs_dir / "releases" / release
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        rdir.joinpath(name).write_text(
            f"# {name}\n\n**Status:** Aprovado\n\n- [x] T-1 done\n", encoding="utf-8"
        )


def _events(home_dir: Path) -> list[sqlite3.Row]:
    db = home_dir / ".dadaia" / "state" / "telemetry" / "telemetry.sqlite"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM governance_events ORDER BY ts").fetchall()
    finally:
        conn.close()


def test_the_four_release_verbs_each_leave_one_event(home: Path, specs: Path) -> None:
    """new -> phase IMPLEMENTATION -> phase CLOSURE -> rc-archive, then a second
    candidate through to archive: every state-document change is one event, and archive
    never refuses on `implemented` because the verb wrote it."""
    _run(specs, "new", "0.0.1")
    _approve(specs, "0.0.1")
    _run(specs, "phase", "IMPLEMENTATION", "--sha", _SHA)
    _run(specs, "phase", "CLOSURE", "--sha", _SHA)
    _run(specs, "rc-archive")

    _approve(specs, "0.0.1")
    _run(specs, "phase", "IMPLEMENTATION", "--sha", _SHA)
    _run(specs, "phase", "CLOSURE", "--sha", _SHA)
    _run(specs, "archive", "0.0.1", "--shipped", _SHA, "--pr", "1", "--next", "0.0.2")

    assert (specs / "releases" / "_archive" / "0.0.1").is_dir()
    assert (specs / "releases" / "0.0.2").is_dir()

    rows = [row for row in _events(home) if row["ledger"] == "releases"]
    verbs = [row["verb"] for row in rows]
    # One event per verb INVOCATION: `archive` births 0.0.2 as part of its own act, so
    # it leaves one `archive` event over the release it shipped, not a second `new`.
    assert verbs.count("new") == 1, verbs
    assert verbs.count("phase") == 4
    assert verbs.count("rc-archive") == 1
    assert verbs.count("archive") == 1
    assert {row["record_id"] for row in rows} == {"0.0.1"}
