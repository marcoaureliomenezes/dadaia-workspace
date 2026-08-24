"""RED CLI tests — ``dadaia bugs append`` refuses incoherent events with exit 1.

The executed path (bugs bugs-append-accepts-second-terminal-event /
bugs-append-allows-terminal-event-without-reported): the CLI wrote whatever validated
against the per-event schema, so a second terminal or an unopened stream landed in the
ledger and only the specs doctor flagged it afterwards. The CLI now routes through
``BugService.append_event`` — the enforced side of the core coherence authority.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def _append(specs_dir: Path, bug_id: str, event: str, *extra: str) -> tuple[int, str]:
    result = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            bug_id,
            "--event",
            event,
            "--specs-dir",
            str(specs_dir),
            *extra,
        ],
    )
    return result.exit_code, result.output + str(result.stderr or "")


def _report(specs_dir: Path, bug_id: str) -> None:
    code, out = _append(
        specs_dir,
        bug_id,
        "reported",
        "--title",
        "t",
        "--severity",
        "LOW",
        "--surface",
        "cli",
        "--component",
        "bugs",
        "--context",
        "test-ctx",
        "--symptom",
        "s",
        "--repro",
        "r",
        "--expected",
        "e",
        "--notes",
        "n",
    )
    assert code == 0, out


def test_append_refuses_second_terminal_with_exit_1(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    _report(specs, "b1")
    code, out = _append(
        specs,
        "b1",
        "resolved",
        "--release",
        "v0.5.0",
        "--resolution-evidence",
        "x" * 30,
        "--evidence-loop",
        "pytest tests/integration/cli/test_bugs_append_coherence.py -q",
        "--evidence-seam",
        "tests/integration/cli/test_bugs_append_coherence.py::"
        "test_append_refuses_second_terminal_with_exit_1",
        "--evidence-diff",
        "net-negative: -1/+0 lines on the coherence check",
    )
    assert code == 0, out
    code, out = _append(specs, "b1", "rejected", "--reason", "why")
    assert code == 1
    assert "at most one terminal" in out
    ledger = (specs / "bugs" / "bugs.jsonl").read_text(encoding="utf-8")
    assert ledger.count('"bug_id": "b1"') == 2  # the refused event was never written


def test_append_refuses_terminal_without_reported_with_exit_1(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    code, out = _append(specs, "never-opened", "rejected", "--reason", "why")
    assert code == 1
    assert "must open with 'reported'" in out
    assert not (specs / "bugs" / "bugs.jsonl").exists()
