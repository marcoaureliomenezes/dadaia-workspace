"""Unit tests for SpecsDoctor taxonomy + disposition invariants (T-46-13, AC-4).

SPEC-DOC-034 — the three ``_archive`` dirs exist (WARN + auto-fix).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue


def _codes(specs: Path, code: str) -> list[SpecsDoctorIssue]:
    return [i for i in SpecsDoctor(specs).check() if i.code == code]


def _seed_archives(specs: Path) -> None:
    for parent in ("backlog", "audits", "bugs"):
        (specs / parent / "_archive").mkdir(parents=True)


# ---------------------------------------------------------------------------
# Sad-path + fix-behavior matrix (DOC-034 missing dir + auto-fix)
# ---------------------------------------------------------------------------


def _setup_doc034(specs) -> None:  # type: ignore[no-untyped-def]
    (specs / "backlog").mkdir(parents=True)
    (specs / "audits" / "_archive").mkdir(parents=True)
    (specs / "bugs" / "_archive").mkdir(parents=True)


@pytest.mark.parametrize(
    ("code", "setup", "expect_count", "expect_substring", "expect_severity"),
    [
        pytest.param(
            "SPEC-DOC-034",
            _setup_doc034,
            1,
            "backlog",
            Severity.WARNING,
            id="doc034-missing-archive-dir",
        ),
    ],
)
def test_sad_path_matrix(  # type: ignore[no-untyped-def]
    tmp_path: Path,
    code: str,
    setup,
    expect_count: int,
    expect_substring: str | None,
    expect_severity: Severity,
) -> None:
    specs = tmp_path / "specs"
    setup(specs)
    warns = _codes(specs, code)
    assert len(warns) == expect_count
    assert all(w.severity is expect_severity for w in warns)
    if expect_substring is not None:
        assert expect_substring in warns[0].description

    if code == "SPEC-DOC-034":
        # Auto-fix behavior: fixable, and fix() clears the residual issue.
        assert warns[0].fixable is True
        assert warns[0].path is not None
        assert Path(warns[0].path).parts[-2:] == ("backlog", "_archive")
        doctor = SpecsDoctor(specs)
        fixed = doctor.fix()
        assert any(i.code == "SPEC-DOC-034" for i in fixed)
        assert (specs / "backlog" / "_archive").is_dir()
        assert _codes(specs, "SPEC-DOC-034") == []


# ---------------------------------------------------------------------------
# Silent / exempt rows — 1 param (each invariant's clean and exempt fixtures)
# ---------------------------------------------------------------------------


def _silent_doc034_present(specs: Path) -> None:
    _seed_archives(specs)


def _silent_doc034_absent_parent(specs: Path) -> None:
    specs.mkdir()


@pytest.mark.parametrize(
    ("code", "setup"),
    [
        pytest.param(
            "SPEC-DOC-034", _silent_doc034_present, id="doc034-archive-dirs-present-clean"
        ),
        pytest.param(
            "SPEC-DOC-034",
            _silent_doc034_absent_parent,
            id="doc034-absent-parent-not-flagged-tree4-owns-it",
        ),
    ],
)
def test_silent_and_exempt_matrix(tmp_path: Path, code: str, setup) -> None:  # type: ignore[no-untyped-def]
    specs = tmp_path / "specs"
    setup(specs)
    assert _codes(specs, code) == []
