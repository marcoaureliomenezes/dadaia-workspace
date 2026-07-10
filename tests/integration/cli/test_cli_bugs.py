"""Integration tests for `dadaia bugs append|status|stats` (T-46-03).

Merged per plan-integration.md (6 -> 2): (a) one seeded lifecycle fn (append ->
bugs.jsonl name -> status open/resolved -> stats aggregates); (b) one parametrized
rejection fn (missing payload, bad severity -> nothing written).
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


def _resolve(specs_dir: Path, bug_id: str) -> None:
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
            "resolved",
            "--resolution-evidence",
            "test: reporter-artifact repro replayed; all named surfaces covered.",
            "--release",
            "v0.1.46",
        ],
    )
    assert result.exit_code == 0, result.output


def test_seeded_lifecycle_append_status_and_stats(specs: Path) -> None:
    """append writes the ONE canonical bugs.jsonl; status lists open/resolved
    correctly; stats aggregates by status and severity."""
    _append_reported(specs, "a", severity="HIGH")
    _append_reported(specs, "b", severity="LOW")
    _append_reported(specs, "c", severity="HIGH")

    logs = list((specs / "bugs").glob("*.jsonl"))
    assert len(logs) == 1
    # v0.1.73 FR1 (operator contract): the ONE canonical append-only ledger.
    assert logs[0].name == "bugs.jsonl"

    _resolve(specs, "c")

    status_open = _runner.invoke(app, ["bugs", "status", "--specs-dir", str(specs)])
    assert status_open.exit_code == 0, status_open.output
    assert "a" in status_open.output
    assert "b" in status_open.output
    # c was resolved -> not in the open list.
    assert "c\topen" not in status_open.output
    assert "[ok] 2 open bug(s)." in status_open.output

    status_all = _runner.invoke(app, ["bugs", "status", "--all", "--specs-dir", str(specs)])
    assert status_all.exit_code == 0, status_all.output
    assert "c\tresolved" in status_all.output

    stats_result = _runner.invoke(app, ["bugs", "stats", "--specs-dir", str(specs)])
    assert stats_result.exit_code == 0, stats_result.output
    assert "total\t3" in stats_result.output
    assert "status:open\t2" in stats_result.output
    assert "status:resolved\t1" in stats_result.output
    assert "severity:HIGH\t2" in stats_result.output
    assert "severity:LOW\t1" in stats_result.output


@pytest.mark.parametrize(
    ("bug_id", "extra_args"),
    [
        (
            "incomplete",
            ["--title", "only a title"],
        ),
        (
            "b",
            [
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
        ),
    ],
    ids=["missing-required-payload", "bad-severity-enum"],
)
def test_append_rejection_writes_nothing(specs: Path, bug_id: str, extra_args: list[str]) -> None:
    result = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--specs-dir",
            str(specs),
            "--bug-id",
            bug_id,
            "--event",
            "reported",
            *extra_args,
        ],
    )
    assert result.exit_code == 1
    assert list((specs / "bugs").glob("*.jsonl")) == []
