"""Unit tests for SpecsDoctor SPEC-DOC-033/041 — the bug-ledger invariant.

Intent: CONTRACT — SPEC-DOC-033/041.

The doctor reads ``specs/bugs/BUGS.jsonl`` through the ONE injected
``bug_store_factory`` (D1) — every case below wires
``container.build_bug_record_store`` explicitly, the SAME factory the production CLI
wires (``cli/commands/specs.py``). Covers: line validity (ERROR, the ONE
malformed-line diagnosis — not valid JSON, not an object, or ``BugRecord.from_dict``
refusing it, v5-shaped lines included) and the archive-overdue signal.
Governance-completeness (the former WARNING branch) is deleted — it is enforced
prospectively at the write seam
(``core.models.bugs.BugRecord.resolve``/``supersede``/``defer``/``reject``,
``tests/unit/core/models/test_bug_record.py``), never re-diagnosed by the doctor
against history.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dadaia_workspace import container
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
    return [
        i
        for i in SpecsDoctor(specs, bug_store_factory=container.build_bug_record_store).check()
        if i.code == "SPEC-DOC-033"
    ]


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
    assert "missing required string field 'title'" in errors[0].description


def test_native_v6_record_invalid_status_enum_is_an_error(tmp_path: Path) -> None:
    """v0.5.1 K5: ``BugRecord.from_dict`` now validates the ``status`` closed enum
    itself — a value outside {open, resolved, superseded, deferred, rejected} is the
    SAME malformed-line diagnosis as any other structurally invalid record, never a
    second, separately-maintained enum check."""
    specs = tmp_path / "specs"
    _write_ledger(_bugs_dir(specs), [_record("bad-status-bug", status="fixed")])
    errors = _doc033(specs)
    assert len(errors) == 1
    assert "status" in errors[0].description
    assert "fixed" in errors[0].description


# ---------------------------------------------------------------------------
# S1 FR23 firing A3 — a v5-shaped line ("event" key) is now ALWAYS a single ERROR,
# never folded, never diagnosed. The live ledger has zero v5 lines by construction
# (T-050-10 physically migrated every historical record) — a surviving one means a
# foreign/pre-migration write, and the doctor names it loudly rather than silently
# re-interpreting it. v0.5.1 K5: there is no dedicated "is this v5?" classification
# any more — a v5-shaped line lacks the v6 required field set (``status`` above
# all — a v5 line names its lifecycle stage ``event``, not ``status``) and fails
# ``BugRecord.from_dict`` for that reason, the SAME malformed-line diagnosis every
# other structurally invalid line gets — one classification, not a special case
# for "v5".
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
    assert "missing required string field 'status'" in errors[0].description


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
    assert all("missing required string field 'status'" in e.description for e in errors)


# ---------------------------------------------------------------------------
# v0.5.1 K5 — governance-completeness is NO LONGER diagnosed by the doctor at all;
# a well-formed record (however incomplete for its own status) is doctor-clean, no
# matter its status. Completeness is enforced prospectively at the transition write
# seam instead — see tests/unit/core/models/test_bug_record.py.
# ---------------------------------------------------------------------------


def test_resolved_without_governance_fields_is_doctor_clean(tmp_path: Path) -> None:
    """The exact record shape that used to trigger SPEC-DOC-033's WARNING branch
    (the "488 live warnings nobody acts on" the K5 card names) is silent now — the
    doctor never re-diagnoses governance completeness against history."""
    specs = tmp_path / "specs"
    _write_ledger(_bugs_dir(specs), [_record("incomplete-resolve", status="resolved")])
    assert _doc033(specs) == []


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


def test_superseded_without_superseded_by_is_doctor_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_ledger(_bugs_dir(specs), [_record("superseded-bug", status="superseded")])
    assert _doc033(specs) == []


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
    validator = GovernanceValidator(specs, bug_store_factory=container.build_bug_record_store)

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
    validator = GovernanceValidator(specs, bug_store_factory=container.build_bug_record_store)

    issues = validator.check_bug_archive_overdue(now=datetime(2026, 8, 27, tzinfo=UTC))

    assert issues == []


def test_archive_overdue_is_silent_for_an_open_record(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_ledger(bugs, [_record("still-open", status="open", ts="2026-01-01T00:00:00Z")])
    validator = GovernanceValidator(specs, bug_store_factory=container.build_bug_record_store)

    issues = validator.check_bug_archive_overdue(now=datetime(2026, 8, 27, tzinfo=UTC))

    assert issues == []
