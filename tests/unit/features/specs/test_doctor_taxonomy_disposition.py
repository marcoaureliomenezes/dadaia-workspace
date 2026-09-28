"""Unit tests for SpecsDoctor taxonomy + disposition invariants (T-46-13, AC-4).

Two invariants:
  SPEC-DOC-034 — the three ``_archive`` dirs exist (WARN + auto-fix);
  SPEC-DOC-035 — the single-source invariant (re-targeted, SPEC v0.12.0 FR5/T-120-08): a
                 loose per-entry ``*.md`` directly under ``specs/backlog/`` — other than
                 ``BACKLOG.md``/``README.md`` — warns, regardless of any status it carries;
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


def _backlog_entry(specs: Path, name: str, status: str, *, archived: bool = False) -> None:
    parent = specs / "backlog" / ("_archive" if archived else "")
    parent.mkdir(parents=True, exist_ok=True)
    (parent / name).write_text(f"# {name}\n\n**Status:** {status}\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Sad-path + fix-behavior matrix (DOC-034 missing dir + auto-fix, DOC-035 loose
# terminal backlog) — merged into one parametrized matrix
# ---------------------------------------------------------------------------


def _setup_doc034(specs) -> None:  # type: ignore[no-untyped-def]
    (specs / "backlog").mkdir(parents=True)
    (specs / "audits" / "_archive").mkdir(parents=True)
    (specs / "bugs" / "_archive").mkdir(parents=True)


def _setup_doc035(specs) -> None:  # type: ignore[no-untyped-def]
    """A loose per-entry file directly under specs/backlog/ is drift under the
    single-source model (SPEC v0.12.0 FR5/T-120-08), regardless of its Status content."""
    _seed_archives(specs)
    _backlog_entry(specs, "shipped-item.md", "DELIVERED — v0.1.30")


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
        pytest.param(
            "SPEC-DOC-035",
            _setup_doc035,
            1,
            "shipped-item.md",
            Severity.WARNING,
            id="doc035-loose-per-entry-file",
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


def _silent_doc035_archived(specs: Path) -> None:
    """A superseded per-entry file already under _archive/ is clean — the check is a
    non-recursive glob of specs/backlog/ itself; it never scans _archive/."""
    _seed_archives(specs)
    _backlog_entry(specs, "shipped-item.md", "DELIVERED — v0.1.30", archived=True)


def _silent_doc035_only_single_source_files(specs: Path) -> None:
    """BACKLOG.json and AGENTS.md are the only two filenames the single-source invariant
    permits loose directly under specs/backlog/ — present together, the tree is clean."""
    _seed_archives(specs)
    (specs / "backlog" / "BACKLOG.json").write_text(
        '{"schema": "backlog-v1", "active": []}\n', encoding="utf-8"
    )
    (specs / "backlog" / "AGENTS.md").write_text("# Backlog\n", encoding="utf-8")


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
        pytest.param(
            "SPEC-DOC-035",
            _silent_doc035_archived,
            id="doc035-under-archive-not-scanned-clean",
        ),
        pytest.param(
            "SPEC-DOC-035",
            _silent_doc035_only_single_source_files,
            id="doc035-backlog-and-readme-only-clean",
        ),
    ],
)
def test_silent_and_exempt_matrix(tmp_path: Path, code: str, setup) -> None:  # type: ignore[no-untyped-def]
    specs = tmp_path / "specs"
    setup(specs)
    assert _codes(specs, code) == []
