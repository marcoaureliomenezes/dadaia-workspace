"""Unit tests for SpecsDoctor SPEC-DOC-033 — event-sourced JSONL bug-telemetry invariant.

Release v0.1.46 / T-46-04 (AC-1). Covers per-line schema validity, the rotation ceiling,
and event coherence over the terminal set {resolved, superseded, deferred, rejected}.

Bug-stream coherence (SPEC-DOC-033) guards the event-sourced ledger — the cross-file
chronological-ordering test is kept as a named test (a reported in an earlier file makes
a terminal in a later file coherent, proving the check reads files in ts order, not
lexical file order).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue


def _bugs_dir(specs: Path) -> Path:
    d = specs / "bugs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _reported(
    bug_id: str, *, severity: str = "HIGH", ts: str = "2026-07-01T13:00:00Z"
) -> dict[str, Any]:
    return {
        "bug_id": bug_id,
        "event": "reported",
        "ts": ts,
        "reported_by": "software-engineer",
        "title": f"title {bug_id}",
        "severity": severity,
        "surface": "gate",
        "component": "spec_context",
        "context": "dadaia-workspace",
        "tags": ["gate"],
        "symptom": "sym",
        "repro": "repro",
        "expected": "exp",
        "notes": "n",
    }


def _resolved(bug_id: str, *, ts: str = "2026-07-01T14:00:00Z") -> dict[str, Any]:
    return {
        "bug_id": bug_id,
        "event": "resolved",
        "ts": ts,
        "reported_by": "software-engineer",
        "release": "v0.1.46",
    }


def _write_log(bugs: Path, name: str, events: list[dict[str, Any]]) -> Path:
    path = bugs / name
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def _doc033(specs: Path) -> list[SpecsDoctorIssue]:
    return [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-033"]


def test_coherence_spans_multiple_files_in_chronological_order(tmp_path: Path) -> None:
    """A reported in an earlier file makes a terminal in a later file coherent."""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(bugs, "20260701T13Z-00.jsonl", [_reported("bug-a")])
    _write_log(bugs, "20260701T14Z-00.jsonl", [_resolved("bug-a")])
    assert _doc033(specs) == []


# ---------------------------------------------------------------------------
# FR2 (v0.5.0 T-50-09) — the healing rule: a violation row is reported only while no
# LATER `reported` event exists for the same bug_id.
# ---------------------------------------------------------------------------


def test_later_reported_heals_the_violation_row(tmp_path: Path) -> None:
    """A violation row followed by a later `reported` for the same bug_id -> the doctor
    reports NOTHING for it."""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(
        bugs,
        "20260701T13Z-00.jsonl",
        [
            _reported("ghost"),
            _resolved("ghost", ts="2026-07-01T14:00:00Z"),
            _resolved("ghost", ts="2026-07-01T15:00:00Z"),  # double-terminal violation
            _reported("ghost", ts="2026-07-01T16:00:00Z"),  # compensation: heals it
        ],
    )
    assert _doc033(specs) == []


def test_uncompensated_violation_still_errors_with_todays_exact_message(
    tmp_path: Path,
) -> None:
    """No later `reported` anywhere -> the violation still ERRORs, and the message is
    byte-identical to the pre-FR2 format: `bugs/<name> line <n>: <clause> (SPEC-DOC-033,
    ERROR).`"""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(bugs, "20260701T13Z-00.jsonl", [_resolved("orphan")])
    errors = _doc033(specs)
    assert len(errors) == 1
    assert errors[0].description == (
        "bugs/20260701T13Z-00.jsonl line 1: terminal event 'resolved' for bug 'orphan' "
        "with no prior 'reported' event — every stream must open with 'reported' "
        "(SPEC-DOC-033, ERROR)."
    )
    assert errors[0].severity is Severity.ERROR


def test_healed_then_reviolated_stream_errors_only_on_the_new_row(tmp_path: Path) -> None:
    """A `reported` heals an earlier violation; a NEW second-terminal after that healing
    `reported` still ERRORs, citing the new row's own line number."""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(
        bugs,
        "20260701T13Z-00.jsonl",
        [
            _reported("bug-x", ts="2026-07-01T13:00:00Z"),
            _resolved("bug-x", ts="2026-07-01T14:00:00Z"),
            _resolved("bug-x", ts="2026-07-01T15:00:00Z"),  # V1: healed below
            _reported("bug-x", ts="2026-07-01T16:00:00Z"),  # heals V1 (reopen)
            _resolved("bug-x", ts="2026-07-01T17:00:00Z"),
            _resolved("bug-x", ts="2026-07-01T18:00:00Z"),  # V2: NEW, stays unhealed
        ],
    )
    errors = _doc033(specs)
    assert len(errors) == 1
    assert "line 6" in errors[0].description
    assert "second terminal event" in errors[0].description


def test_healing_reported_spans_files_in_glob_order(tmp_path: Path) -> None:
    """The healing `reported` may live in a LATER file — the whole-history fold spans
    every `*.jsonl` file, not just one."""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(
        bugs,
        "20260701T13Z-00.jsonl",
        [
            _reported("bug-y"),
            _resolved("bug-y", ts="2026-07-01T14:00:00Z"),
            _resolved("bug-y", ts="2026-07-01T15:00:00Z"),  # violation
        ],
    )
    _write_log(bugs, "20260701T16Z-00.jsonl", [_reported("bug-y", ts="2026-07-01T16:00:00Z")])
    assert _doc033(specs) == []


# ---------------------------------------------------------------------------
# Violation rows — terminal-without-reported, double-terminal, malformed,
# schema-fail (x2), over-ceiling — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("build", "expect_description_contains"),
    [
        pytest.param(
            lambda bugs: _write_log(bugs, "20260701T13Z-00.jsonl", [_resolved("orphan")]),
            "no prior 'reported'",
            id="terminal-without-prior-reported",
        ),
        pytest.param(
            lambda bugs: _write_log(
                bugs,
                "20260701T13Z-00.jsonl",
                [
                    _reported("bug-a"),
                    _resolved("bug-a"),
                    _resolved("bug-a", ts="2026-07-01T16:00:00Z"),
                ],
            ),
            "second terminal event",
            id="double-terminal",
        ),
        pytest.param(
            lambda bugs: (bugs / "20260701T13Z-00.jsonl").write_text(
                "{not json\n", encoding="utf-8"
            ),
            "not valid JSON",
            id="malformed-json-line",
        ),
        pytest.param(
            lambda bugs: _write_log(
                bugs,
                "20260701T13Z-00.jsonl",
                [
                    {
                        "bug_id": "b",
                        "event": "reported",
                        "ts": "2026-07-01T13:00:00Z",
                        "reported_by": "se",
                        "title": "only a title",
                    }
                ],
            ),
            "schema",
            id="reported-missing-required-payload-fails-schema",
        ),
        pytest.param(
            lambda bugs: _write_log(
                bugs,
                "20260701T13Z-00.jsonl",
                [
                    {
                        "bug_id": "b",
                        "event": "exploded",
                        "ts": "2026-07-01T13:00:00Z",
                        "reported_by": "se",
                    }
                ],
            ),
            "schema",
            id="bad-event-enum-fails-schema",
        ),
        pytest.param(
            lambda bugs: _write_log(
                bugs, "20260701T13Z-00.jsonl", [_reported(f"b{i}") for i in range(1001)]
            ),
            "rotation ceiling",
            id="over-ceiling-1001-rows",
        ),
    ],
)
def test_violation_matrix(tmp_path: Path, build, expect_description_contains: str) -> None:  # type: ignore[no-untyped-def]
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    build(bugs)
    errors = _doc033(specs)
    matching = [e for e in errors if expect_description_contains in e.description]
    assert matching, f"Expected an error containing {expect_description_contains!r}, got: {errors}"
    assert all(e.severity is Severity.ERROR for e in matching)


# ---------------------------------------------------------------------------
# Clean rows — noop/negative-control/archived-exempt/at-ceiling — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda specs: None, id="no-bugs-dir-noop"),
        pytest.param(
            lambda specs: _write_log(
                _bugs_dir(specs), "20260701T13Z-00.jsonl", [_reported("bug-a"), _resolved("bug-a")]
            ),
            id="coherent-reported-then-resolved-negative-control",
        ),
        pytest.param(
            lambda specs: _write_log(
                _bugs_dir(specs),
                "20260701T13Z-00.jsonl",
                [
                    _reported("bug-a"),
                    _resolved("bug-a"),
                    {
                        "bug_id": "bug-a",
                        "event": "archived",
                        "ts": "2026-07-01T15:00:00Z",
                        "reported_by": "project-auditor",
                    },
                ],
            ),
            id="archived-after-resolved-exempt",
        ),
        pytest.param(
            lambda specs: _write_log(
                _bugs_dir(specs), "20260701T13Z-00.jsonl", [_reported(f"b{i}") for i in range(1000)]
            ),
            id="exactly-at-ceiling-clean",
        ),
    ],
)
def test_clean_matrix(tmp_path: Path, build) -> None:  # type: ignore[no-untyped-def]
    specs = tmp_path / "specs"
    specs.mkdir(exist_ok=True)
    build(specs)
    assert _doc033(specs) == []
