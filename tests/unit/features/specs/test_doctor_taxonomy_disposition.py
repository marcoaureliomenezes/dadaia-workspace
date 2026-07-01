"""Unit tests for SpecsDoctor taxonomy + disposition invariants (T-46-13, AC-4).

Three invariants, EACH with a passes-on-clean + fails-on-broken test PAIR:
  SPEC-DOC-034 — the three ``_archive`` dirs exist (WARN + auto-fix);
  SPEC-DOC-035 — consumed-but-unarchived backlog (terminal status still loose → warns);
  SPEC-DOC-036 — audit-without-disposition (archived audit naming its release → clean).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs import Severity, SpecsDoctor


def _codes(specs: Path, code: str) -> list:
    return [i for i in SpecsDoctor(specs).check() if i.code == code]


# --- SPEC-DOC-034: _archive dirs exist ------------------------------------------------


def _seed_archives(specs: Path) -> None:
    for parent in ("backlog", "audits", "bugs"):
        (specs / parent / "_archive").mkdir(parents=True)


def test_archive_dirs_present_is_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _seed_archives(specs)
    assert _codes(specs, "SPEC-DOC-034") == []


def test_missing_archive_dir_warns(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "audits" / "_archive").mkdir(parents=True)
    (specs / "bugs" / "_archive").mkdir(parents=True)
    warns = _codes(specs, "SPEC-DOC-034")
    assert len(warns) == 1
    assert warns[0].severity is Severity.WARNING
    assert warns[0].fixable is True
    assert Path(warns[0].path).parts[-2:] == ("backlog", "_archive")


def test_missing_archive_dir_auto_fix_creates_it(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "audits" / "_archive").mkdir(parents=True)
    (specs / "bugs" / "_archive").mkdir(parents=True)
    doctor = SpecsDoctor(specs)
    fixed = doctor.fix()
    assert any(i.code == "SPEC-DOC-034" for i in fixed)
    assert (specs / "backlog" / "_archive").is_dir()
    assert (specs / "backlog" / "_archive" / ".gitkeep").exists()
    assert _codes(specs, "SPEC-DOC-034") == []


def test_absent_parent_dir_is_not_flagged(tmp_path: Path) -> None:
    """A missing parent (e.g. no backlog/ at all) is TREE-4's concern, not SPEC-DOC-034."""
    specs = tmp_path / "specs"
    specs.mkdir()
    assert _codes(specs, "SPEC-DOC-034") == []


# --- SPEC-DOC-035: consumed-but-unarchived backlog ------------------------------------


def _backlog_entry(specs: Path, name: str, status: str, *, archived: bool = False) -> None:
    parent = specs / "backlog" / ("_archive" if archived else "")
    parent.mkdir(parents=True, exist_ok=True)
    (parent / name).write_text(f"# {name}\n\n**Status:** {status}\n", encoding="utf-8")


def test_terminal_backlog_under_archive_is_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _seed_archives(specs)
    _backlog_entry(specs, "shipped-item.md", "DELIVERED — v0.1.30", archived=True)
    assert _codes(specs, "SPEC-DOC-035") == []


def test_terminal_backlog_still_loose_warns(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _seed_archives(specs)
    _backlog_entry(specs, "shipped-item.md", "DELIVERED — v0.1.30")
    warns = _codes(specs, "SPEC-DOC-035")
    assert len(warns) == 1
    assert warns[0].severity is Severity.WARNING
    assert "shipped-item.md" in warns[0].description


def test_nonterminal_backlog_loose_is_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _seed_archives(specs)
    _backlog_entry(specs, "open-idea.md", "OPEN")
    assert _codes(specs, "SPEC-DOC-035") == []


# --- SPEC-DOC-036: audit-without-disposition ------------------------------------------


def _archived_audit(specs: Path, name: str, body: str) -> None:
    audit_dir = specs / "audits" / "_archive" / name
    audit_dir.mkdir(parents=True)
    (audit_dir / "audit.md").write_text(body, encoding="utf-8")


def test_archived_audit_with_disposition_is_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _seed_archives(specs)
    _archived_audit(
        specs,
        "20260701T135346Z-6145b869",
        "# Audit\n\n**Disposition:** v0.1.46\n\nAll findings fixed.\n",
    )
    assert _codes(specs, "SPEC-DOC-036") == []


def test_archived_audit_without_disposition_warns(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _seed_archives(specs)
    _archived_audit(
        specs,
        "20260612T001813Z-deadbeef",
        "# Audit\n\nOverall 4/10. Findings listed. No disposing release recorded.\n",
    )
    warns = _codes(specs, "SPEC-DOC-036")
    assert len(warns) == 1
    assert warns[0].severity is Severity.WARNING
    assert "20260612T001813Z-deadbeef" in warns[0].description


def test_empty_audit_archive_is_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _seed_archives(specs)
    (specs / "audits" / "_archive" / ".gitkeep").write_text("", encoding="utf-8")
    assert _codes(specs, "SPEC-DOC-036") == []
