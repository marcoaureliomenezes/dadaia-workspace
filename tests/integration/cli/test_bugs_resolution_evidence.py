"""v0.1.73 FR3 — the BLOCKING resolution law: `bugs append --event resolved` is refused
without `--resolution-evidence` (recurrence audit: ~40% of the v0.1.66-71 arc's
resolutions were need-unmet; evidence = reporter-artifact repro + all named surfaces).

Intent: CONTRACT — historical precedent, superseded as the CLI's ENFORCEMENT point by
v0.4.4 FR23 (`test_bugs_resolution_evidence_fr23.py`): `--resolution-evidence` is now
optional legacy free text, and a `resolved` event is refused unless it carries FR23's
three independently checkable fields (`--evidence-loop`/`--evidence-seam`/
`--evidence-diff`) instead of a bare >=20-char string. The no-evidence and short-evidence
refusal cases below still hold unchanged (refused for the new reason too); the
"valid evidence" case is updated to also carry the three new required fields.
"""

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


def test_resolution_evidence_gate(tmp_path: Path) -> None:
    """One parametrized fn: no-evidence -> refused + nothing written; short evidence ->
    refused; valid evidence -> lands in the event. Shares one ``_report`` setup."""
    specs = _specs(tmp_path)
    _report(specs)

    # No evidence: refused, nothing written.
    no_evidence = _runner.invoke(
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
    assert no_evidence.exit_code != 0, no_evidence.output
    # FR23 (v0.4.4) message names the three checkable fields, not the legacy flag.
    assert "--evidence-loop" in no_evidence.output
    text = "".join(p.read_text() for p in (specs / "bugs").glob("*.jsonl"))
    assert '"resolved"' not in text

    # Short evidence: refused.
    short_evidence = _runner.invoke(
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
    assert short_evidence.exit_code != 0, short_evidence.output

    # Valid evidence: lands in the event. FR23 (v0.4.4) also requires the three
    # checkable fields now — the free-text `--resolution-evidence` alone no longer
    # satisfies the gate (see `test_bugs_resolution_evidence_fr23.py`).
    valid_evidence = _runner.invoke(
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
            "--evidence-loop",
            "pytest tests/integration/cli/test_bugs_resolution_evidence.py -q",
            "--evidence-seam",
            "tests/integration/cli/test_bugs_resolution_evidence.py::test_resolution_evidence_gate",
            "--evidence-diff",
            "net-negative: -3/+1 lines on the resolution-evidence check",
            "--specs-dir",
            str(specs),
        ],
    )
    assert valid_evidence.exit_code == 0, valid_evidence.output
    lines = [
        json.loads(ln)
        for p in (specs / "bugs").glob("*.jsonl")
        for ln in p.read_text().splitlines()
    ]
    resolved = next(e for e in lines if e["event"] == "resolved")
    assert resolved["evidence"].startswith("Replayed the reporter's")
