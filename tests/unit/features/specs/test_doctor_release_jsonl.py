"""``ReleaseValidator`` RELEASE.jsonl checks (v0.5.0 FR4, T-050-11): SPEC-DOC-042
(A4.1a, ACTIVE.md <-> RELEASE.jsonl agreement) and SPEC-DOC-043 (A4.2, milestone
immutability).

Intent: CONTRACT — SPEC v0.5.0 A4.1a ("both files live, read in parallel, agreeing —
a doctor WARN when they disagree, exit unchanged") and A4.2 (milestone immutability
WARNING, D15 — never a block). Size: SMALL — direct unit tests of ``ReleaseValidator``
(no full ``SpecsDoctor``/memory scaffold needed for these two leaf checks).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.doctor_release import ReleaseValidator
from dadaia_workspace.features.specs.doctor_types import Severity

pytestmark = pytest.mark.unit


def _write_active(specs: Path, release: str, phase: str) -> None:
    (specs / "releases").mkdir(parents=True, exist_ok=True)
    (specs / "releases" / "ACTIVE.md").write_text(
        f"release: {release}\nphase: {phase}\n", encoding="utf-8"
    )


def _write_jsonl(specs: Path, release: str, lines: list[str]) -> Path:
    rdir = specs / "releases" / release
    rdir.mkdir(parents=True, exist_ok=True)
    path = rdir / "RELEASE.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_agreement_and_immutability_checks_warn_never_error_and_stay_silent_when_agreeing(
    tmp_path: Path,
) -> None:
    """Four scenarios against the two new leaf checks, each independently checkable:

    1. Agreeing phases (ACTIVE.md == RELEASE.jsonl's folded phase) -> SPEC-DOC-042 silent.
    2. Disagreeing phases -> SPEC-DOC-042 fires, WARNING severity ONLY (never ERROR —
       D15, the doctor's exit code must stay unaffected by this finding).
    3. A release with no RELEASE.jsonl at all -> both checks stay silent (expand-phase
       tolerance: a release that predates T-050-11 is not a disagreement).
    4. A second `defined` milestone record for one release -> SPEC-DOC-043 fires at
       WARNING severity, naming the RELEASE.jsonl path, and does not also fire
       SPEC-DOC-042 (the phases in that fixture agree).
    """
    specs = tmp_path / "specs"

    # --- Scenario 1: agreement, no RELEASE.jsonl-absent release involved -----------
    _write_active(specs, "0.9.0", "IMPLEMENTATION")
    _write_jsonl(
        specs,
        "0.9.0",
        [
            '{"ts":"2026-08-01T00:00:00Z","event":"phase","agent":"product-engineer","data":{"phase":"DEFINITION"}}',
            '{"ts":"2026-08-02T00:00:00Z","event":"phase","agent":"software-engineer","data":{"phase":"IMPLEMENTATION"}}',
        ],
    )
    validator = ReleaseValidator(specs)
    assert validator.check_release_jsonl_agreement() == []
    assert validator.check_release_jsonl_milestone_immutability() == []

    # --- Scenario 2: disagreement fires SPEC-DOC-042, WARNING only -----------------
    _write_active(specs, "0.9.0", "CLOSURE")  # ACTIVE.md says CLOSURE
    agreement_issues = validator.check_release_jsonl_agreement()
    assert len(agreement_issues) == 1
    issue = agreement_issues[0]
    assert issue.code == "SPEC-DOC-042"
    assert issue.severity == Severity.WARNING
    assert "IMPLEMENTATION" in issue.description and "CLOSURE" in issue.description

    # --- Scenario 3: release with no RELEASE.jsonl at all -> silent ----------------
    _write_active(specs, "0.1.0-no-jsonl", "IMPLEMENTATION")
    (specs / "releases" / "0.1.0-no-jsonl").mkdir(parents=True)
    no_jsonl_validator = ReleaseValidator(specs)
    assert no_jsonl_validator.check_release_jsonl_agreement() == []

    # --- Scenario 4: duplicate milestone fires SPEC-DOC-043, WARNING only ----------
    _write_active(specs, "0.9.0", "IMPLEMENTATION")  # restore agreement for this release
    jsonl_path = _write_jsonl(
        specs,
        "0.9.0",
        [
            '{"ts":"2026-08-01T00:00:00Z","event":"defined","agent":"product-engineer","data":{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","pr":1}}',
            '{"ts":"2026-08-02T00:00:00Z","event":"phase","agent":"software-engineer","data":{"phase":"IMPLEMENTATION"}}',
            '{"ts":"2026-08-03T00:00:00Z","event":"defined","agent":"project-auditor","data":{"sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","pr":2}}',
        ],
    )
    immutability_issues = validator.check_release_jsonl_milestone_immutability()
    assert len(immutability_issues) == 1
    dup_issue = immutability_issues[0]
    assert dup_issue.code == "SPEC-DOC-043"
    assert dup_issue.severity == Severity.WARNING
    assert dup_issue.path == str(jsonl_path)
    assert validator.check_release_jsonl_agreement() == []  # phases agree in this fixture
