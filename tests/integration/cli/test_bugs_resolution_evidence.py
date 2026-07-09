"""v0.1.73 FR3 — the BLOCKING resolution law: `bugs append --event resolved` is refused
without `--resolution-evidence` (recurrence audit: ~40% of the v0.1.66-71 arc's
resolutions were need-unmet; evidence = reporter-artifact repro + all named surfaces)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def _specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "bugs").mkdir(parents=True)
    return specs


def _report(specs: Path) -> None:
    r = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            "law-test",
            "--event",
            "reported",
            "--reported-by",
            "t",
            "--title",
            "t",
            "--severity",
            "LOW",
            "--surface",
            "s",
            "--component",
            "c",
            "--context",
            "ctx",
            "--tag",
            "t",
            "--symptom",
            "s",
            "--repro",
            "r",
            "--expected",
            "e",
            "--notes",
            "n",
            "--specs-dir",
            str(specs),
        ],
    )
    assert r.exit_code == 0, r.output


def test_resolved_without_evidence_is_refused(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)
    r = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            "law-test",
            "--event",
            "resolved",
            "--reported-by",
            "t",
            "--release",
            "v9.9.9",
            "--specs-dir",
            str(specs),
        ],
    )
    assert r.exit_code != 0, r.output
    assert "resolution-evidence" in r.output
    # nothing written
    text = "".join(p.read_text() for p in (specs / "bugs").glob("*.jsonl"))
    assert '"resolved"' not in text


def test_resolved_with_evidence_lands_in_event(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)
    r = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            "law-test",
            "--event",
            "resolved",
            "--reported-by",
            "t",
            "--release",
            "v9.9.9",
            "--resolution-evidence",
            "Replayed the reporter's exact command on their tree; all named surfaces covered.",
            "--specs-dir",
            str(specs),
        ],
    )
    assert r.exit_code == 0, r.output
    lines = [
        json.loads(ln)
        for p in (specs / "bugs").glob("*.jsonl")
        for ln in p.read_text().splitlines()
    ]
    resolved = next(e for e in lines if e["event"] == "resolved")
    assert resolved["evidence"].startswith("Replayed the reporter's")


def test_short_evidence_is_refused(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)
    r = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            "law-test",
            "--event",
            "resolved",
            "--reported-by",
            "t",
            "--release",
            "v9.9.9",
            "--resolution-evidence",
            "fixed",
            "--specs-dir",
            str(specs),
        ],
    )
    assert r.exit_code != 0, r.output
