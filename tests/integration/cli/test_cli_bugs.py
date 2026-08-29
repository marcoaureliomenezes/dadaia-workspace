"""Integration tests for `dadaia bugs append|status|stats|update|resolve` (T-46-03;
rewritten v0.5.0 T-050-08 against the one-record-per-bug model; rewritten again v0.5.1
K5 — resolution is now `bugs resolve <id> ...`, never `update --set status=...`).

Intent: CONTRACT — v0.5.1 K5 (status transitions are the interface).

Merged per plan-integration.md (6 -> 2): (a) one seeded lifecycle fn (append ->
BUGS.jsonl name -> status open/resolved via `bugs resolve` -> stats aggregates);
(b) one parametrized rejection fn (missing payload, bad severity -> nothing written).
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
    """v0.5.1 K5: resolution is `bugs resolve`, never `update --set status=...`."""
    result = _runner.invoke(
        app,
        [
            "bugs",
            "resolve",
            bug_id,
            "--cause",
            "the gate reused a stale specs_dir",
            "--caused-by",
            "none-first-fix",
            "--resolved-release",
            "v0.1.46",
            "--solution",
            "reporter-artifact repro replayed; all named surfaces covered.",
            "--evidence-loop",
            "pytest -k test_seeded_lifecycle_append_status_and_stats",
            "--evidence-seam",
            "tests/integration/cli/test_cli_bugs.py::test_seeded_lifecycle_append_status_and_stats",
            "--evidence-diff",
            "net-neutral: test fixture only, no production change",
            "--diff-direction",
            "net-neutral",
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


def test_update_refuses_a_status_set_naming_the_transition_command(specs: Path) -> None:
    """v0.5.1 K5: `bugs update --set status=...` is refused — status is reachable only
    through `bugs resolve|supersede|defer|reject`, never a bare governance write."""
    _append_reported(specs, "e")

    result = _runner.invoke(
        app,
        ["bugs", "update", "e", "--set", "status=resolved", "--specs-dir", str(specs)],
    )

    assert result.exit_code == 1
    assert "resolve|supersede|defer|reject" in result.output
    # Refused before any write — the record is still open.
    status = _runner.invoke(app, ["bugs", "status", "--specs-dir", str(specs)])
    assert "e\topen" in status.output


def test_resolve_refuses_an_incomplete_call_and_writes_no_change(specs: Path) -> None:
    """v0.5.1 K5: `bugs resolve` with a missing required field is refused
    (IncompleteTransitionError), naming every missing field, record left untouched."""
    _append_reported(specs, "f")

    result = _runner.invoke(app, ["bugs", "resolve", "f", "--specs-dir", str(specs)])

    assert result.exit_code == 1
    assert "'cause' is required" in result.output
    assert "'evidence_diff' is required" in result.output
    status = _runner.invoke(app, ["bugs", "status", "--specs-dir", str(specs)])
    assert "f\topen" in status.output


def test_resolve_refuses_a_malformed_evidence_diff(specs: Path) -> None:
    """v0.5.1 K5: `evidence_diff` must match the schema pattern — a bare rationale with
    no leading net-negative/net-positive/net-neutral token is refused."""
    _append_reported(specs, "g")

    result = _runner.invoke(
        app,
        [
            "bugs",
            "resolve",
            "g",
            "--cause",
            "c",
            "--caused-by",
            "none",
            "--resolved-release",
            "v0.5.1",
            "--solution",
            "s",
            "--evidence-loop",
            "el",
            "--evidence-seam",
            "es",
            "--evidence-diff",
            "not-a-valid-direction: rationale",
            "--diff-direction",
            "net-neutral",
            "--specs-dir",
            str(specs),
        ],
    )

    assert result.exit_code == 1
    assert "evidence_diff" in result.output


def test_supersede_defer_reject_reach_their_terminal_status(specs: Path) -> None:
    """v0.5.1 K5: `bugs supersede --by`/`defer --reason`/`reject --reason` are the ONLY
    way a record reaches those terminal statuses."""
    _append_reported(specs, "h")
    _append_reported(specs, "i")
    _append_reported(specs, "j")

    superseded = _runner.invoke(
        app, ["bugs", "supersede", "h", "--by", "backlog-slug", "--specs-dir", str(specs)]
    )
    assert superseded.exit_code == 0, superseded.output

    deferred = _runner.invoke(
        app, ["bugs", "defer", "i", "--reason", "waiting on a release", "--specs-dir", str(specs)]
    )
    assert deferred.exit_code == 0, deferred.output

    rejected = _runner.invoke(
        app, ["bugs", "reject", "j", "--reason", "not a real bug", "--specs-dir", str(specs)]
    )
    assert rejected.exit_code == 0, rejected.output

    status_all = _runner.invoke(app, ["bugs", "status", "--all", "--specs-dir", str(specs)])
    assert "h\tsuperseded" in status_all.output
    assert "i\tdeferred" in status_all.output
    assert "j\trejected" in status_all.output

    # Missing --by/--reason is refused (IncompleteTransitionError), record untouched.
    _append_reported(specs, "k")
    missing_by = _runner.invoke(app, ["bugs", "supersede", "k", "--specs-dir", str(specs)])
    assert missing_by.exit_code == 1
    assert "'by' is required" in missing_by.output
