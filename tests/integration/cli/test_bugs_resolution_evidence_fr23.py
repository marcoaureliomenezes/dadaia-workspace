"""``dadaia bugs append --event resolved`` refuses evidence that cannot be checked
(v0.4.4 FR23, T-044-62).

Intent: CONTRACT — v0.4.4 A23.1, A23.5, A23.6. Supersedes the v0.1.73 FR3 blanket
``--resolution-evidence`` (>=20 chars) rule tested in ``test_bugs_resolution_evidence.py``:
that free-text floor let 132/438 on-disk ``resolved`` events through with zero
checkable evidence (70 more cleared it with one template string). FR23 requires three
INDEPENDENTLY checkable fields — ``--evidence-loop`` (the red-loop command),
``--evidence-seam`` (the test file/node that pins the fix) and ``--evidence-diff`` (the
diff direction on the touched feature) — each refused on its own so the message always
names exactly what is missing (A23.1). A ``net-positive:`` diff direction does not
hard-block the append; it routes to a ``software-architect`` review before the commit
(the CLI's half of that route is a printed advisory, never a second refusal).
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()

# A real command + a real test seam in THIS repo, so the well-formed cases below are not
# synthetic strings but an actual reproduction of what T-044-62 itself does (A23.6: the
# gate must be satisfiable on the first try for a real fix in this release).
_REAL_LOOP_CMD = (
    ".dadaia/.venv/bin/python -m pytest "
    "tests/integration/cli/test_bugs_resolution_evidence_fr23.py -q"
)
_REAL_SEAM = (
    "tests/integration/cli/test_bugs_resolution_evidence_fr23.py::"
    "test_well_formed_evidence_is_accepted_on_the_first_try"
)


def _specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "bugs").mkdir(parents=True)
    return specs


def _report(specs: Path, bug_id: str = "fr23-test") -> None:
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


def _resolve_args(
    specs: Path,
    *,
    bug_id: str = "fr23-test",
    evidence_loop: str | None = _REAL_LOOP_CMD,
    evidence_seam: str | None = _REAL_SEAM,
    evidence_diff: str | None = "net-negative: -18/+6 lines on bugs.py's evidence gate",
) -> list[str]:
    args = [
        "bugs",
        "append",
        "--bug-id",
        bug_id,
        "--event",
        "resolved",
        "--reported-by",
        "software-engineer",
        "--release",
        "v0.4.4",
        "--specs-dir",
        str(specs),
    ]
    if evidence_loop is not None:
        args += ["--evidence-loop", evidence_loop]
    if evidence_seam is not None:
        args += ["--evidence-seam", evidence_seam]
    if evidence_diff is not None:
        args += ["--evidence-diff", evidence_diff]
    return args


def test_missing_evidence_loop_is_refused_and_names_the_field(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(app, _resolve_args(specs, evidence_loop=None))

    assert result.exit_code != 0, result.output
    assert "--evidence-loop" in result.output
    text = "".join(p.read_text() for p in (specs / "bugs").glob("*.jsonl"))
    assert '"resolved"' not in text


def test_missing_evidence_seam_is_refused_and_names_the_field(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(app, _resolve_args(specs, evidence_seam=None))

    assert result.exit_code != 0, result.output
    assert "--evidence-seam" in result.output
    text = "".join(p.read_text() for p in (specs / "bugs").glob("*.jsonl"))
    assert '"resolved"' not in text


def test_missing_evidence_diff_is_refused_and_names_the_field(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(app, _resolve_args(specs, evidence_diff=None))

    assert result.exit_code != 0, result.output
    assert "--evidence-diff" in result.output
    text = "".join(p.read_text() for p in (specs / "bugs").glob("*.jsonl"))
    assert '"resolved"' not in text


def test_evidence_diff_without_direction_prefix_is_refused(tmp_path: Path) -> None:
    """A diff description with no direction token is not checkable — refused, same as
    an absent one (A23.1: 'evidence missing any one of the three fields is refused')."""
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(app, _resolve_args(specs, evidence_diff="removed the stray branch"))

    assert result.exit_code != 0, result.output
    assert "--evidence-diff" in result.output


def test_thin_free_text_evidence_alone_no_longer_satisfies_the_gate(tmp_path: Path) -> None:
    """The pre-FR23 acceptance this task closes: a >=20-char free-text
    ``--resolution-evidence`` used to be sufficient on its own (v0.1.73 FR3). It is not
    checkable by FR23's three fields, so it is refused."""
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--bug-id",
            "fr23-test",
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

    assert result.exit_code != 0, result.output
    text = "".join(p.read_text() for p in (specs / "bugs").glob("*.jsonl"))
    assert '"resolved"' not in text


def test_well_formed_evidence_is_accepted_on_the_first_try(tmp_path: Path) -> None:
    """A23.6/R-10: the gate is satisfiable at HEAD — a real fix's evidence succeeds on
    the FIRST invocation, no retry, in a tmp specs dir (never the live ledger)."""
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(app, _resolve_args(specs))

    assert result.exit_code == 0, result.output
    lines = [
        json.loads(ln)
        for p in (specs / "bugs").glob("*.jsonl")
        for ln in p.read_text().splitlines()
    ]
    resolved = next(e for e in lines if e["event"] == "resolved")
    assert resolved["evidence_loop"] == _REAL_LOOP_CMD
    assert resolved["evidence_seam"] == _REAL_SEAM
    assert resolved["evidence_diff"].startswith("net-negative:")


def test_net_negative_diff_prints_no_architect_notice(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(app, _resolve_args(specs))

    assert result.exit_code == 0, result.output
    assert "software-architect" not in result.output


def test_net_positive_diff_does_not_block_but_notices_the_architect_route(
    tmp_path: Path,
) -> None:
    """A net-positive diff routes, it does not hard-block (SPEC FR23): the append still
    succeeds, and the CLI prints the advisory naming ``software-architect`` and the
    'before the commit' moment (A23.3's CLI half)."""
    specs = _specs(tmp_path)
    _report(specs)

    result = _runner.invoke(
        app,
        _resolve_args(
            specs,
            evidence_diff="net-positive: +120/-4 lines added to bugs.py (grew the CLI)",
        ),
    )

    assert result.exit_code == 0, result.output
    assert "software-architect" in result.output
    assert "before the commit" in result.output
    lines = [
        json.loads(ln)
        for p in (specs / "bugs").glob("*.jsonl")
        for ln in p.read_text().splitlines()
    ]
    resolved = next(e for e in lines if e["event"] == "resolved")
    assert resolved["evidence_diff"].startswith("net-positive:")


def test_historical_resolved_event_without_fr23_fields_still_reads_via_status(
    tmp_path: Path,
) -> None:
    """A23.2: the ledger reader (``bugs status``) keeps accepting a historical
    ``resolved`` event that predates FR23 — hand-written, exactly the on-disk shape of
    132/438 pre-FR23 events, never rewritten by this change."""
    specs = _specs(tmp_path)
    ledger = specs / "bugs" / "bugs.jsonl"
    ledger.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "bug_id": "old-bug",
                        "event": "reported",
                        "ts": "2026-01-01T00:00:00Z",
                        "reported_by": "software-engineer",
                        "title": "t",
                        "severity": "LOW",
                        "surface": "s",
                        "component": "c",
                        "context": "ctx",
                        "tags": [],
                        "symptom": "s",
                        "repro": "r",
                        "expected": "e",
                        "notes": "n",
                    }
                ),
                json.dumps(
                    {
                        "bug_id": "old-bug",
                        "event": "resolved",
                        "ts": "2026-01-02T00:00:00Z",
                        "reported_by": "software-engineer",
                        "release": "v0.1.10",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = _runner.invoke(app, ["bugs", "status", "--all", "--specs-dir", str(specs)])

    assert result.exit_code == 0, result.output
    assert "old-bug" in result.output
    assert "resolved" in result.output
