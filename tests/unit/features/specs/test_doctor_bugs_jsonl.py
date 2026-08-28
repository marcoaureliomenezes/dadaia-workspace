"""Unit tests for SpecsDoctor SPEC-DOC-033/041 — the bug-ledger invariant.

Release v0.1.46 / T-46-04 (AC-1); rewritten v0.5.0 T-050-08 (FR2/A2.3/A2.8, AR-1
ruling "the doctor's bug lane is a second hand-kept reader"); the v5 event fold and
SPEC-DOC-040 deleted at the S1 FR23 firing (A3/A5,
`specs/releases/0.5.0/reviews/S1-FR23-firing.md`). The legacy hourly-file rotation
reader is dead under canon v6 and is not carried forward — every case below targets
the ONE canonical ``specs/bugs/BUGS.jsonl`` (T-050-10 rename). Covers: line validity
(ERROR), the v5-line-is-an-ERROR shape (A3 — no fold, no diagnosis), governance-
completeness gaps on a native v6 record (WARNING), and the A2.8 archive-overdue
signal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue
from dadaia_workspace.features.specs.doctor_governance import GovernanceValidator


def _bugs_dir(specs: Path) -> Path:
    d = specs / "bugs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _record(bug_id: str, **overrides: object) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": bug_id,
        "ts": "2026-08-27T10:00:00Z",
        "reported_by": "software-engineer",
        "title": f"title {bug_id}",
        "severity": "MEDIUM",
        "surface": "bugs",
        "component": "features/bugs/service.py",
        "context": "dadaia-workspace",
        "symptom": "sym",
        "repro": "repro",
        "expected": "exp",
        "status": "open",
        "cause": None,
        "caused_by": None,
        "lineage_source": None,
        "registration_commit": None,
        "registration_granularity": None,
        "resolved_commit": None,
        "resolution_granularity": None,
        "resolved_release": None,
        "audited": None,
    }
    base.update(overrides)
    return base


def _write_ledger(bugs: Path, rows: list[dict[str, Any]]) -> Path:
    path = bugs / "BUGS.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def _doc033(specs: Path) -> list[SpecsDoctorIssue]:
    return [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-033"]


def test_no_bugs_dir_is_a_noop(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    assert _doc033(specs) == []


def test_malformed_json_line_is_an_error(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    (bugs / "BUGS.jsonl").write_text("{not json\n", encoding="utf-8")
    errors = _doc033(specs)
    assert len(errors) == 1
    assert "not valid JSON" in errors[0].description
    assert errors[0].severity is Severity.ERROR


def test_native_v6_record_line_parses_clean(tmp_path: Path) -> None:
    """A freshly-registered (native v6) line — no ``"event"`` key — is read through
    ``BugRecord.from_dict`` directly."""
    specs = tmp_path / "specs"
    _write_ledger(_bugs_dir(specs), [_record("native-bug")])
    assert _doc033(specs) == []


def test_native_v6_record_missing_required_field_is_an_error(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bad = _record("native-bug")
    del bad["title"]
    _write_ledger(_bugs_dir(specs), [bad])
    errors = _doc033(specs)
    assert len(errors) == 1
    assert "not a valid bug-record object" in errors[0].description


# ---------------------------------------------------------------------------
# S1 FR23 firing A3 — a v5-shaped line ("event" key) is now ALWAYS a single ERROR,
# never folded, never diagnosed. The live ledger has zero v5 lines by construction
# (T-050-10 physically migrated every historical record) — a surviving one means a
# foreign/pre-migration write, and the doctor names it loudly rather than silently
# re-interpreting it.
# ---------------------------------------------------------------------------


def test_v5_shaped_line_is_a_single_error_never_folded(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    (bugs / "BUGS.jsonl").write_text(
        json.dumps(
            {
                "bug_id": "legacy-bug",
                "event": "reported",
                "ts": "2026-07-01T13:00:00Z",
                "reported_by": "software-engineer",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    errors = _doc033(specs)
    assert len(errors) == 1
    assert errors[0].severity is Severity.ERROR
    assert "v5 line in a v6 ledger" in errors[0].description
    assert "migrate" in errors[0].description


def test_two_v5_shaped_lines_are_two_independent_errors(tmp_path: Path) -> None:
    """No fold, no coherence diagnosis over the v5 portion anymore (A3) — a
    ``reported``+``resolved`` pair that the pre-A3 fold would have accepted as
    coherent (zero issues) is now TWO independent ERRORs, one per physical line."""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    rows = [
        {
            "bug_id": "legacy-bug",
            "event": "reported",
            "ts": "2026-07-01T13:00:00Z",
            "reported_by": "software-engineer",
        },
        {
            "bug_id": "legacy-bug",
            "event": "resolved",
            "ts": "2026-07-01T14:00:00Z",
            "reported_by": "software-engineer",
        },
    ]
    _write_ledger(bugs, rows)
    errors = _doc033(specs)
    assert len(errors) == 2
    assert all(e.severity is Severity.ERROR for e in errors)
    assert all("v5 line in a v6 ledger" in e.description for e in errors)


# ---------------------------------------------------------------------------
# A2.3 — governance-completeness gap on a native v6 record is WARNING.
# ---------------------------------------------------------------------------


def test_resolved_without_governance_fields_is_a_warning(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_ledger(_bugs_dir(specs), [_record("incomplete-resolve", status="resolved")])
    issues = _doc033(specs)
    assert len(issues) == 1
    assert issues[0].severity is Severity.WARNING
    assert "missing" in issues[0].description
    assert "cause" in issues[0].description


def test_resolved_with_all_governance_fields_is_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_ledger(
        _bugs_dir(specs),
        [
            _record(
                "complete-resolve",
                status="resolved",
                cause="a stale seam",
                caused_by="prior-bug",
                resolved_release="0.5.0",
                solution="fixed at the seam; regression test at file:line",
            )
        ],
    )
    assert _doc033(specs) == []


def test_superseded_without_superseded_by_is_a_warning(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_ledger(_bugs_dir(specs), [_record("superseded-bug", status="superseded")])
    issues = _doc033(specs)
    assert len(issues) == 1
    assert "superseded_by" in issues[0].description


# ---------------------------------------------------------------------------
# A2.8 — SPEC-DOC-041 archive-overdue signal, testable via the injected `now`.
# ---------------------------------------------------------------------------


def test_archive_overdue_warns_past_the_threshold(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_ledger(
        bugs,
        [_record("old-terminal", status="resolved", ts="2026-01-01T00:00:00Z")],
    )
    validator = GovernanceValidator(specs)

    issues = validator.check_bug_archive_overdue(now=datetime(2026, 8, 27, tzinfo=UTC))

    assert len(issues) == 1
    assert issues[0].code == "SPEC-DOC-041"
    assert issues[0].severity is Severity.WARNING
    assert "old-terminal" in issues[0].description


def test_archive_overdue_is_silent_for_a_recent_terminal_record(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_ledger(
        bugs,
        [_record("recent-terminal", status="resolved", ts="2026-08-20T00:00:00Z")],
    )
    validator = GovernanceValidator(specs)

    issues = validator.check_bug_archive_overdue(now=datetime(2026, 8, 27, tzinfo=UTC))

    assert issues == []


def test_archive_overdue_is_silent_for_an_open_record(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_ledger(bugs, [_record("still-open", status="open", ts="2026-01-01T00:00:00Z")])
    validator = GovernanceValidator(specs)

    issues = validator.check_bug_archive_overdue(now=datetime(2026, 8, 27, tzinfo=UTC))

    assert issues == []
