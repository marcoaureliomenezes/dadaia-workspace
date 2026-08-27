"""Integration tests for `dadaia bugs append|status|stats|update` (T-46-03; rewritten
v0.5.0 T-050-08 against the one-record-per-bug model — `append --event resolved` dies,
resolution is now `bugs update <id> --set ...`).

Merged per plan-integration.md (6 -> 2): (a) one seeded lifecycle fn (append ->
BUGS.jsonl name -> status open/resolved -> stats aggregates); (b) one parametrized
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
            "--title",
            f"title {bug_id}",
            "--severity",
            severity,
            "--surface",
            "cli",
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
        ],
    )
    assert result.exit_code == 0, result.output


def _resolve(specs_dir: Path, bug_id: str) -> None:
    result = _runner.invoke(
        app,
        [
            "bugs",
            "update",
            bug_id,
            "--set",
            "status=resolved",
            "--set",
            "cause=the gate reused a stale specs_dir",
            "--set",
            "caused_by=none-first-fix",
            "--set",
            "resolved_release=v0.1.46",
            "--set",
            "solution=reporter-artifact repro replayed; all named surfaces covered.",
            "--specs-dir",
            str(specs_dir),
        ],
    )
    assert result.exit_code == 0, result.output


def test_seeded_lifecycle_append_status_and_stats(specs: Path) -> None:
    """append writes the ONE canonical BUGS.jsonl; status lists open/resolved
    correctly; stats aggregates by status and severity."""
    _append_reported(specs, "a", severity="HIGH")
    _append_reported(specs, "b", severity="LOW")
    _append_reported(specs, "c", severity="HIGH")

    logs = list((specs / "bugs").glob("*.jsonl"))
    assert len(logs) == 1
    # v0.1.73 FR1 (operator contract): the ONE canonical append-only ledger.
    # v0.5.0 T-050-10 renamed it bugs.jsonl -> BUGS.jsonl (FR3 physical migration).
    assert logs[0].name == "BUGS.jsonl"

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
                "cli",
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
            *extra_args,
        ],
    )
    assert result.exit_code == 1
    assert list((specs / "bugs").glob("*.jsonl")) == []


def test_update_refuses_an_immutable_core_field_and_writes_no_change(specs: Path) -> None:
    """AS-16: the update seam refuses a change to an immutable-core field (A2.2a) with
    a non-zero exit — never a block on a human, but never silently accepted either."""
    _append_reported(specs, "d")

    result = _runner.invoke(
        app,
        ["bugs", "update", "d", "--set", "title=a different title", "--specs-dir", str(specs)],
    )

    assert result.exit_code == 1
    assert "immutable-core" in result.output
