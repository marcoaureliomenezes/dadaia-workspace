"""``ReleaseValidator`` RELEASE.jsonl checks (v0.5.0 FR4): SPEC-DOC-043 (A4.2,
milestone immutability).

SPEC-DOC-042 (A4.1a, the expand-window ``ACTIVE.md`` <-> ``RELEASE.jsonl`` agreement
check) RETIRED at T-050-21A: it existed only to watch two authorities of one truth
agree during the expand window; ``ACTIVE.md`` is gone, there is nothing left to
compare against, and ``check_release_jsonl_agreement`` is deleted along with it (S1
FR23 firing review, `specs/releases/0.5.0/reviews/S1-FR23-firing.md` §2.2 finding
"SPEC-DOC-042 is a check whose only purpose is to watch two authorities of one truth
agree during a window ... admissible only because T-050-21A deletes it").

Intent: CONTRACT — SPEC v0.5.0 A4.2 (milestone immutability WARNING, D15 — never a
block). Size: SMALL — direct unit tests of ``ReleaseValidator`` (no full
``SpecsDoctor``/memory scaffold needed for this leaf check).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.doctor_release import ReleaseValidator
from dadaia_workspace.features.specs.doctor_types import Severity

pytestmark = pytest.mark.unit


def _write_jsonl(specs: Path, release: str, lines: list[str]) -> Path:
    rdir = specs / "releases" / release
    rdir.mkdir(parents=True, exist_ok=True)
    path = rdir / "RELEASE.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_milestone_immutability_warns_on_duplicate_and_stays_silent_otherwise(
    tmp_path: Path,
) -> None:
    """Two scenarios against the one surviving leaf check:

    1. A single ``defined`` record -> silent (no immutability violation).
    2. A second ``defined`` record for the same release -> SPEC-DOC-043 fires at
       WARNING severity ONLY (never ERROR — D15, the doctor's exit code must stay
       unaffected by this finding), naming the RELEASE.jsonl path.
    """
    specs = tmp_path / "specs"

    # --- Scenario 1: one milestone record -> silent --------------------------------
    validator = ReleaseValidator(specs)
    _write_jsonl(
        specs,
        "0.9.0",
        [
            '{"ts":"2026-08-01T00:00:00Z","event":"defined","agent":"product-engineer","data":{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","pr":1}}',
            '{"ts":"2026-08-02T00:00:00Z","event":"phase","agent":"software-engineer","data":{"phase":"IMPLEMENTATION"}}',
        ],
    )
    assert validator.check_release_jsonl_milestone_immutability() == []

    # --- Scenario 2: duplicate milestone fires SPEC-DOC-043, WARNING only ----------
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
