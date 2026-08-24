"""``dadaia bugs append --event picked`` — the CLI half of the reservation marker
(v0.4.3 T-043-18/FR14).

Intent: CONTRACT — v0.4.3 A14.1, A14.2 (CLI half). Mirrors the v0.1.73 FR3 resolution-
law precedent (``test_bugs_resolution_evidence.py``): ``picked`` requires ``--release``
at the append path, BLOCKING, before anything is written — schema and CLI both require
it in the SAME change because zero historical ``picked`` events exist (architect
ruling, 2026-08-17T16:15:00Z).
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


def _report(specs: Path, bug_id: str = "law-test") -> None:
    r = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            bug_id,
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


def test_picked_without_release_is_refused_and_writes_nothing(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            "law-test",
            "--event",
            "picked",
            "--reported-by",
            "software-engineer",
            "--specs-dir",
            str(specs),
        ],
    )

    assert result.exit_code != 0, result.output
    assert "--release" in result.output
    text = "".join(p.read_text() for p in (specs / "bugs").glob("*.jsonl"))
    assert '"picked"' not in text


def test_picked_with_release_succeeds_and_lands_in_the_ledger(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            "law-test",
            "--event",
            "picked",
            "--reported-by",
            "software-engineer",
            "--release",
            "v0.4.3",
            "--specs-dir",
            str(specs),
        ],
    )

    assert result.exit_code == 0, result.output
    lines = [
        json.loads(ln)
        for p in (specs / "bugs").glob("*.jsonl")
        for ln in p.read_text().splitlines()
    ]
    picked = next(e for e in lines if e["event"] == "picked")
    assert picked["reported_by"] == "software-engineer"
    assert picked["release"] == "v0.4.3"


def test_a_second_pick_on_the_same_open_stream_is_never_refused(tmp_path: Path) -> None:
    """NO-LOCKS: a repeated pick is the sanctioned race outcome, allowed and visible."""
    specs = _specs(tmp_path)
    _report(specs)

    for actor in ("agent-a", "agent-b"):
        result = _runner.invoke(
            app,
            [
                "bugs",
                "append",
                "--bug-id",
                "law-test",
                "--event",
                "picked",
                "--reported-by",
                actor,
                "--release",
                "v0.4.3",
                "--specs-dir",
                str(specs),
            ],
        )
        assert result.exit_code == 0, result.output

    lines = [
        json.loads(ln)
        for p in (specs / "bugs").glob("*.jsonl")
        for ln in p.read_text().splitlines()
    ]
    picked_events = [e for e in lines if e["event"] == "picked"]
    assert [e["reported_by"] for e in picked_events] == ["agent-a", "agent-b"]


def test_pick_after_a_terminal_event_is_refused(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)
    resolve = _runner.invoke(
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
            "v0.4.3",
            "--resolution-evidence",
            "reporter-artifact repro replayed; all named surfaces covered.",
            "--evidence-loop",
            "pytest tests/integration/cli/test_bugs_picked_event.py -q",
            "--evidence-seam",
            "tests/integration/cli/test_bugs_picked_event.py::test_pick_after_a_terminal_event_is_refused",
            "--evidence-diff",
            "net-negative: -2/+0 lines on the picked-after-terminal check",
            "--specs-dir",
            str(specs),
        ],
    )
    assert resolve.exit_code == 0, resolve.output

    picked = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            "law-test",
            "--event",
            "picked",
            "--reported-by",
            "software-engineer",
            "--release",
            "v0.4.3",
            "--specs-dir",
            str(specs),
        ],
    )
    assert picked.exit_code != 0, picked.output
    assert "incoherent" in picked.output


def test_bugs_status_prints_picked_by_when_non_empty(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs, bug_id="picked-bug")
    _report(specs, bug_id="unpicked-bug")
    pick = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            "picked-bug",
            "--event",
            "picked",
            "--reported-by",
            "software-engineer",
            "--release",
            "v0.4.3",
            "--specs-dir",
            str(specs),
        ],
    )
    assert pick.exit_code == 0, pick.output

    status = _runner.invoke(app, ["bugs", "status", "--specs-dir", str(specs)])
    assert status.exit_code == 0, status.output

    lines = status.output.splitlines()
    picked_line = next(ln for ln in lines if ln.startswith("picked-bug\t"))
    unpicked_line = next(ln for ln in lines if ln.startswith("unpicked-bug\t"))
    assert "software-engineer" in picked_line
    assert "software-engineer" not in unpicked_line
