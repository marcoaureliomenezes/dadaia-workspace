"""Integration tests for `dadaia bugs append|status|stats` (T-46-03).

Asserts OBSERVABLE STDOUT (not exit-0 smoke): after seeded appends, ``status`` lists the
expected open ``bug_id``(s) and ``stats`` prints the expected per-severity/status aggregate
counts. Also covers schema-rejection (a ``reported`` event missing required payload writes
nothing and exits non-zero) and the ADDITIVE JSONL landing path.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    s = tmp_path / "specs"
    (s / "bugs").mkdir(parents=True)
    return s


def _append_reported(specs_dir: Path, bug_id: str, *, severity: str = "HIGH") -> None:
    result = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--specs-dir",
            str(specs_dir),
            "--bug-id",
            bug_id,
            "--event",
            "reported",
            "--title",
            f"title {bug_id}",
            "--severity",
            severity,
            "--surface",
            "gate",
            "--component",
            "spec_context",
            "--context",
            "dadaia-workspace",
            "--symptom",
            "sym",
            "--repro",
            "repro",
            "--expected",
            "exp",
            "--notes",
            "n",
        ],
    )
    assert result.exit_code == 0, result.output


def test_append_writes_jsonl_under_bugs_dir(specs: Path) -> None:
    _append_reported(specs, "gate-bug")
    logs = list((specs / "bugs").glob("*.jsonl"))
    assert len(logs) == 1
    # v0.1.73 FR1 (operator contract): the ONE canonical append-only ledger.
    assert logs[0].name == "bugs.jsonl"


def test_status_lists_open_bug_ids(specs: Path) -> None:
    _append_reported(specs, "open-alpha")
    _append_reported(specs, "open-beta")
    # Close one via a resolved event.
    closed = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--specs-dir",
            str(specs),
            "--bug-id",
            "open-beta",
            "--event",
            "resolved",
            "--resolution-evidence",
            "test: reporter-artifact repro replayed; all named surfaces covered.",
            "--release",
            "v0.1.46",
        ],
    )
    assert closed.exit_code == 0, closed.output

    result = _runner.invoke(app, ["bugs", "status", "--specs-dir", str(specs)])
    assert result.exit_code == 0, result.output
    assert "open-alpha" in result.output
    # open-beta was resolved → not in the open list.
    assert "open-beta" not in result.output
    assert "[ok] 1 open bug(s)." in result.output


def test_status_all_includes_closed(specs: Path) -> None:
    _append_reported(specs, "a")
    _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--specs-dir",
            str(specs),
            "--bug-id",
            "a",
            "--event",
            "resolved",
            "--resolution-evidence",
            "test: reporter-artifact repro replayed; all named surfaces covered.",
            "--release",
            "v0.1.46",
        ],
    )
    result = _runner.invoke(app, ["bugs", "status", "--all", "--specs-dir", str(specs)])
    assert result.exit_code == 0, result.output
    assert "a\tresolved" in result.output


def test_stats_aggregates_by_status_and_severity(specs: Path) -> None:
    _append_reported(specs, "a", severity="HIGH")
    _append_reported(specs, "b", severity="LOW")
    _append_reported(specs, "c", severity="HIGH")
    _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--specs-dir",
            str(specs),
            "--bug-id",
            "c",
            "--event",
            "resolved",
            "--resolution-evidence",
            "test: reporter-artifact repro replayed; all named surfaces covered.",
            "--release",
            "v0.1.46",
        ],
    )

    result = _runner.invoke(app, ["bugs", "stats", "--specs-dir", str(specs)])
    assert result.exit_code == 0, result.output
    assert "total\t3" in result.output
    assert "status:open\t2" in result.output
    assert "status:resolved\t1" in result.output
    assert "severity:HIGH\t2" in result.output
    assert "severity:LOW\t1" in result.output


def test_append_rejects_reported_missing_required_payload(specs: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--specs-dir",
            str(specs),
            "--bug-id",
            "incomplete",
            "--event",
            "reported",
            "--title",
            "only a title",
        ],
    )
    assert result.exit_code == 1
    assert "invalid" in result.output
    # Nothing was written — the schema check gates the store.
    assert list((specs / "bugs").glob("*.jsonl")) == []


def test_append_rejects_bad_severity_enum(specs: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--specs-dir",
            str(specs),
            "--bug-id",
            "b",
            "--event",
            "reported",
            "--title",
            "t",
            "--severity",
            "SEVERE",
            "--surface",
            "s",
            "--component",
            "c",
            "--context",
            "ctx",
            "--symptom",
            "sy",
            "--repro",
            "r",
            "--expected",
            "e",
            "--notes",
            "n",
        ],
    )
    assert result.exit_code == 1
    assert list((specs / "bugs").glob("*.jsonl")) == []
