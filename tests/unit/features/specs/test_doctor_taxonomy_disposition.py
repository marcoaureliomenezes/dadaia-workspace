"""Unit tests for SpecsDoctor taxonomy + disposition invariants (T-46-13, AC-4).

Four invariants:
  SPEC-DOC-034 — the three ``_archive`` dirs exist (WARN + auto-fix);
  SPEC-DOC-035 — the single-source invariant (re-targeted, SPEC v0.12.0 FR5/T-120-08): a
                 loose per-entry ``*.md`` directly under ``specs/backlog/`` — other than
                 ``BACKLOG.md``/``README.md`` — warns, regardless of any status it carries;
  SPEC-DOC-036 — audit-without-disposition (archived audit naming its release → clean) —
                 the audit-disposition law's own doctor invariant, kept as a named pair;
  SPEC-DOC-037 — constitution must not enumerate AgentRuntimeKind members;
  SPEC-DOC-038 — loose (unarchived) audit directories.
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


def _archived_audit(specs: Path, name: str, body: str) -> None:
    audit_dir = specs / "audits" / "_archive" / name
    audit_dir.mkdir(parents=True)
    (audit_dir / "audit.md").write_text(body, encoding="utf-8")


def _loose_audit(specs: Path, name: str) -> None:
    audit_dir = specs / "audits" / name
    audit_dir.mkdir(parents=True)
    (audit_dir / "report.md").write_text("# Audit\n\nFindings.\n", encoding="utf-8")


def _write_constitution(specs: Path, body: str) -> None:
    specs.mkdir(parents=True, exist_ok=True)
    (specs / "constitution.md").write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Sad-path + fix-behavior matrix (DOC-034 missing dir + auto-fix, DOC-035 loose
# terminal backlog, DOC-036 archived audit without disposition, DOC-038 loose
# audit dirs — single and multiple) — merged into one parametrized matrix
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


def _setup_doc036(specs) -> None:  # type: ignore[no-untyped-def]
    _seed_archives(specs)
    _archived_audit(
        specs,
        "20260612T001813Z-deadbeef",
        "# Audit\n\nOverall 4/10. Findings listed. No disposing release recorded.\n",
    )


def _setup_doc038_single(specs) -> None:  # type: ignore[no-untyped-def]
    _loose_audit(specs, "20260701T201136Z-0bcd6c19")


def _setup_doc038_multiple(specs) -> None:  # type: ignore[no-untyped-def]
    _loose_audit(specs, "20260701T201136Z-0bcd6c19")
    _loose_audit(specs, "20260612T001813Z-deadbeef")


@pytest.mark.parametrize(
    ("code", "setup", "expect_count", "expect_substring"),
    [
        pytest.param("SPEC-DOC-034", _setup_doc034, 1, "backlog", id="doc034-missing-archive-dir"),
        pytest.param(
            "SPEC-DOC-035", _setup_doc035, 1, "shipped-item.md", id="doc035-loose-per-entry-file"
        ),
        pytest.param(
            "SPEC-DOC-036",
            _setup_doc036,
            1,
            "20260612T001813Z-deadbeef",
            id="doc036-archived-audit-without-disposition",
        ),
        pytest.param(
            "SPEC-DOC-038",
            _setup_doc038_single,
            1,
            "20260701T201136Z-0bcd6c19",
            id="doc038-single-loose-audit",
        ),
        pytest.param(
            "SPEC-DOC-038", _setup_doc038_multiple, 2, None, id="doc038-multiple-loose-audits"
        ),
    ],
)
def test_sad_path_matrix(  # type: ignore[no-untyped-def]
    tmp_path: Path, code: str, setup, expect_count: int, expect_substring: str | None
) -> None:
    specs = tmp_path / "specs"
    setup(specs)
    warns = _codes(specs, code)
    assert len(warns) == expect_count
    assert all(w.severity is Severity.WARNING for w in warns)
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
        assert (specs / "backlog" / "_archive" / ".gitkeep").exists()
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
    """BACKLOG.md and README.md are the only two filenames the single-source invariant
    permits loose directly under specs/backlog/ (SPEC v0.12.0 FR5) — present together,
    the tree is clean regardless of BACKLOG.md's content."""
    _seed_archives(specs)
    (specs / "backlog" / "BACKLOG.md").write_text("## ACTIVE\n\n## LEDGER\n", encoding="utf-8")
    (specs / "backlog" / "README.md").write_text("# Backlog\n", encoding="utf-8")


def _silent_doc036_with_disposition(specs: Path) -> None:
    _seed_archives(specs)
    _archived_audit(
        specs,
        "20260701T135346Z-6145b869",
        "# Audit\n\n**Disposition:** v0.1.46\n\nAll findings fixed.\n",
    )


def _silent_doc036_empty_archive(specs: Path) -> None:
    _seed_archives(specs)
    (specs / "audits" / "_archive" / ".gitkeep").write_text("", encoding="utf-8")


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
        pytest.param(
            "SPEC-DOC-036",
            _silent_doc036_with_disposition,
            id="doc036-with-disposition-clean",
        ),
        pytest.param(
            "SPEC-DOC-036",
            _silent_doc036_empty_archive,
            id="doc036-empty-audit-archive-clean",
        ),
        pytest.param(
            "SPEC-DOC-038",
            lambda specs: _archived_audit(
                specs, "20260701T135346Z-6145b869", "# Audit\n\n**Disposition:** v0.1.47\n"
            ),
            id="doc038-archived-only-audits-clean",
        ),
        pytest.param(
            "SPEC-DOC-038",
            lambda specs: specs.mkdir(parents=True),
            id="doc038-absent-audits-dir-clean",
        ),
    ],
)
def test_silent_and_exempt_matrix(tmp_path: Path, code: str, setup) -> None:  # type: ignore[no-untyped-def]
    specs = tmp_path / "specs"
    setup(specs)
    assert _codes(specs, code) == []


# ---------------------------------------------------------------------------
# DOC-037: constitution must not enumerate AgentRuntimeKind members — trio merged
# ---------------------------------------------------------------------------


def test_doc037_constitution_enum_prohibition(tmp_path) -> None:  # type: ignore[no-untyped-def]
    specs_clean = tmp_path / "clean" / "specs"
    _write_constitution(
        specs_clean,
        "# Constitution\n\n"
        "Runtime kinds are the roster single-source in [[tech-stack]]; the constitution "
        "states only the invariant. Layer 1 = {claude, codex, pi}; Layer 2 = {pi, codex}.\n"
        "The word fake in lowercase prose is fine.\n",
    )
    assert _codes(specs_clean, "SPEC-DOC-037") == []

    specs_bad = tmp_path / "bad" / "specs"
    _write_constitution(
        specs_bad,
        "# Constitution\n\n"
        "§8: the AgentRuntimeKind enum members are FAKE, CODEX_EXEC, CLAUDE_SDK, "
        "PI_HEADLESS, OPENCODE_RUN.\n",
    )
    errs = _codes(specs_bad, "SPEC-DOC-037")
    assert len(errs) == 1
    assert errs[0].severity is Severity.ERROR
    for tok in ("FAKE", "CODEX_EXEC", "CLAUDE_SDK", "PI_HEADLESS", "OPENCODE_RUN"):
        assert tok in errs[0].description

    specs_single = tmp_path / "single" / "specs"
    _write_constitution(specs_single, "# Constitution\n\nWorkers default to CODEX_EXEC today.\n")
    errs_single = _codes(specs_single, "SPEC-DOC-037")
    assert len(errs_single) == 1 and errs_single[0].severity is Severity.ERROR

    specs_absent = tmp_path / "absent" / "specs"
    specs_absent.mkdir(parents=True)
    # No constitution.md — SPEC-DOC-001 owns absence; SPEC-DOC-037 stays silent.
    assert _codes(specs_absent, "SPEC-DOC-037") == []
