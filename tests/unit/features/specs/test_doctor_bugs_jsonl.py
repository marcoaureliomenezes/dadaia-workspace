"""Unit tests for SpecsDoctor SPEC-DOC-033/040/041 — the bug-ledger invariant.

Release v0.1.46 / T-46-04 (AC-1); rewritten v0.5.0 T-050-08 (FR2/A2.3/A2.7/A2.8, AR-1
ruling "the doctor's bug lane is a second hand-kept reader"). The legacy hourly-file
rotation reader is dead under canon v6 and is not carried forward — every case below
targets the ONE canonical ``specs/bugs/bugs.jsonl``. Covers: line validity (ERROR),
v5 event-stream coherence (demoted to WARNING, never a block), governance-completeness
gaps on a native v6 record (WARNING), the A2.7 immutable-core-drift detector, and the
A2.8 archive-overdue signal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.bugs import BugRecord
from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue
from dadaia_workspace.features.specs.doctor_governance import GovernanceValidator


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
    path = bugs / "bugs.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def _doc033(specs: Path) -> list[SpecsDoctorIssue]:
    return [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-033"]


def test_no_bugs_dir_is_a_noop(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    assert _doc033(specs) == []


def test_coherent_reported_then_resolved_is_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_ledger(_bugs_dir(specs), [_reported("bug-a"), _resolved("bug-a")])
    assert _doc033(specs) == []


def test_malformed_json_line_is_an_error(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    (bugs / "bugs.jsonl").write_text("{not json\n", encoding="utf-8")
    errors = _doc033(specs)
    assert len(errors) == 1
    assert "not valid JSON" in errors[0].description
    assert errors[0].severity is Severity.ERROR


def test_v5_event_missing_required_field_is_an_error(tmp_path: Path) -> None:
    """A line carrying an ``"event"`` key that fails ``BugEvent.from_dict`` (missing a
    required field) is an ERROR — the model's OWN parser is the validation, not a
    second hand-kept field check."""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_ledger(bugs, [{"bug_id": "b", "event": "reported", "reported_by": "se"}])  # no ts
    errors = _doc033(specs)
    assert len(errors) == 1
    assert "not a valid bug-event object" in errors[0].description
    assert errors[0].severity is Severity.ERROR


def test_native_v6_record_line_parses_clean(tmp_path: Path) -> None:
    """A freshly-registered (native v6) line — no ``"event"`` key — is read through
    ``BugRecord.from_dict`` directly, no v5 folding applied."""
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
# A2.3 — v5 event-stream coherence is now WARNING, never ERROR (D15).
# ---------------------------------------------------------------------------


def test_terminal_without_reported_is_a_warning_not_an_error(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_ledger(_bugs_dir(specs), [_resolved("orphan")])
    issues = _doc033(specs)
    assert len(issues) == 1
    assert "no prior 'reported'" in issues[0].description
    assert issues[0].severity is Severity.WARNING
    assert "never a block" in issues[0].description


def test_double_terminal_is_a_warning_not_an_error(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_ledger(
        _bugs_dir(specs),
        [_reported("bug-a"), _resolved("bug-a"), _resolved("bug-a", ts="2026-07-01T16:00:00Z")],
    )
    issues = _doc033(specs)
    assert len(issues) == 1
    assert "second terminal event" in issues[0].description
    assert issues[0].severity is Severity.WARNING


def test_later_reported_heals_the_violation_row(tmp_path: Path) -> None:
    """The FR2 healing rule survives the rewrite: a violation followed by a later
    ``reported`` for the same bug_id is healed — reported as nothing."""
    specs = tmp_path / "specs"
    _write_ledger(
        _bugs_dir(specs),
        [
            _reported("ghost"),
            _resolved("ghost", ts="2026-07-01T14:00:00Z"),
            _resolved("ghost", ts="2026-07-01T15:00:00Z"),  # double-terminal violation
            _reported("ghost", ts="2026-07-01T16:00:00Z"),  # compensation: heals it
        ],
    )
    assert _doc033(specs) == []


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
# A2.7 — SPEC-DOC-040 immutable-core drift detector (production no-op with no
# injected baseline; provably correct with one injected directly).
# ---------------------------------------------------------------------------


def test_immutable_core_drift_check_is_a_noop_with_no_baseline(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_ledger(_bugs_dir(specs), [_record("drifted-bug", title="hand-edited title")])
    issues = [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-040"]
    assert issues == []


def test_immutable_core_drift_check_fires_with_an_injected_baseline(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_ledger(bugs, [_record("drifted-bug", title="hand-edited title")])
    baseline = BugRecord.from_dict(_record("drifted-bug", title="original title"))
    validator = GovernanceValidator(specs, bug_first_add_baselines={"drifted-bug": baseline})

    issues = validator.check_bug_record_immutable_core()

    assert len(issues) == 1
    assert issues[0].code == "SPEC-DOC-040"
    assert issues[0].severity is Severity.WARNING
    assert "title" in issues[0].description


def test_immutable_core_drift_check_is_silent_when_nothing_drifted(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    row = _record("stable-bug")
    _write_ledger(bugs, [row])
    baseline = BugRecord.from_dict(row)
    validator = GovernanceValidator(specs, bug_first_add_baselines={"stable-bug": baseline})

    assert validator.check_bug_record_immutable_core() == []


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
