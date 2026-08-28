"""SPEC-DOC-036/038 fold FINDINGS.jsonl instead of regexing audit prose (v0.5.0 FR15).

Intent: CONTRACT — SPEC v0.5.0 A15.1, A15.2, A15.3 (T-050-25).

FR15 deletes ``check_audit_disposition``'s former disposition-marker regex outright
(A15.1) and replaces both SPEC-DOC-036 (archived-audit disposition) and SPEC-DOC-038
(loose/live-audit visibility) with a fold of ``specs/audits/<slug>/FINDINGS.jsonl``:

* an ``open`` record inside an archived audit (``specs/audits/_archive/**``) is an
  ERROR (SPEC-DOC-036);
* a live audit whose records are ALL terminal (``fixed|superseded|deferred|rejected``)
  and each names a disposing ``release`` is an archive-due WARN (SPEC-DOC-038);
* an archived audit with no ``FINDINGS.jsonl`` at all predates the ``audit-canon-v1``
  schema (D5) and is folded into a single aggregate WARNING, never an ERROR.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs.doctor_closure_audit import ClosureAuditValidator


def _write_findings(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def _finding(
    finding_id: str,
    *,
    disposition: str,
    release: str | None = None,
) -> dict[str, object]:
    return {
        "id": finding_id,
        "pillar": "specs",
        "severity": "MEDIUM",
        "refs": ["some/path.py:1"],
        "claim": "a claim",
        "evidence": "git show <sha> --stat -- some/path.py -> 1 file changed",
        "disposition": disposition,
        "release": release,
        "reason": "a reason" if disposition != "open" else None,
    }


def _codes(specs: Path, code: str) -> list:  # type: ignore[type-arg]
    return [i for i in SpecsDoctor(specs).check() if i.code == code]


# ---------------------------------------------------------------------------
# A15.2 fixture 1 — an archived audit with one open record errors (SPEC-DOC-036).
# ---------------------------------------------------------------------------


def test_archived_audit_with_open_record_errors(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    audit_dir = specs / "audits" / "_archive" / "20261020-five-release-window"
    _write_findings(
        audit_dir / "FINDINGS.jsonl",
        [
            _finding("20261020-five-release-window-F001", disposition="fixed", release="0.5.0"),
            _finding("20261020-five-release-window-F002", disposition="open"),
        ],
    )

    errs = _codes(specs, "SPEC-DOC-036")
    assert len(errs) == 1, f"Expected exactly one open-record error, got: {errs}"
    assert errs[0].severity is Severity.ERROR
    assert "20261020-five-release-window-F002" in errs[0].description
    assert "open" in errs[0].description


def test_archived_audit_fully_terminal_is_clean(tmp_path: Path) -> None:
    """The companion clean case: every record terminal -> no SPEC-DOC-036 ERROR."""
    specs = tmp_path / "specs"
    audit_dir = specs / "audits" / "_archive" / "20261020-fully-closed"
    _write_findings(
        audit_dir / "FINDINGS.jsonl",
        [
            _finding("20261020-fully-closed-F001", disposition="fixed", release="0.5.0"),
            _finding("20261020-fully-closed-F002", disposition="rejected", release="0.5.0"),
        ],
    )

    assert _codes(specs, "SPEC-DOC-036") == []


# ---------------------------------------------------------------------------
# A15.2 fixture 2 — a live fully-terminal audit warns archive-due (SPEC-DOC-038).
# ---------------------------------------------------------------------------


def test_live_fully_terminal_audit_warns_archive_due(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    audit_dir = specs / "audits" / "20261020-five-release-window"
    _write_findings(
        audit_dir / "FINDINGS.jsonl",
        [
            _finding("20261020-five-release-window-F001", disposition="fixed", release="0.5.0"),
            _finding(
                "20261020-five-release-window-F002", disposition="superseded", release="0.5.0"
            ),
        ],
    )

    warns = _codes(specs, "SPEC-DOC-038")
    assert len(warns) == 1, f"Expected one archive-due WARN, got: {warns}"
    assert warns[0].severity is Severity.WARNING
    assert "archive due" in warns[0].description
    assert warns[0].path == str(audit_dir)


def test_live_audit_with_open_record_is_silent(tmp_path: Path) -> None:
    """A live audit still carrying an open finding is legitimately in flight -- no WARN."""
    specs = tmp_path / "specs"
    audit_dir = specs / "audits" / "20261020-still-open"
    _write_findings(
        audit_dir / "FINDINGS.jsonl",
        [
            _finding("20261020-still-open-F001", disposition="fixed", release="0.5.0"),
            _finding("20261020-still-open-F002", disposition="open"),
        ],
    )

    assert _codes(specs, "SPEC-DOC-038") == []


def test_live_audit_terminal_without_named_release_is_silent(tmp_path: Path) -> None:
    """Every record must ALSO name a disposing release -- terminal alone is not enough."""
    specs = tmp_path / "specs"
    audit_dir = specs / "audits" / "20261020-terminal-no-release"
    _write_findings(
        audit_dir / "FINDINGS.jsonl",
        [_finding("20261020-terminal-no-release-F001", disposition="fixed", release=None)],
    )

    assert _codes(specs, "SPEC-DOC-038") == []


def test_live_audit_with_no_findings_jsonl_is_silent(tmp_path: Path) -> None:
    """An in-flight audit with no FINDINGS.jsonl yet (or a pre-canon dir) never warns."""
    specs = tmp_path / "specs"
    audit_dir = specs / "audits" / "20261020-not-started-yet"
    audit_dir.mkdir(parents=True)
    (audit_dir / "AUDIT.md").write_text("# Audit\n\nIn progress.\n", encoding="utf-8")

    assert _codes(specs, "SPEC-DOC-038") == []


# ---------------------------------------------------------------------------
# Legacy archived audits (pre-canon, no FINDINGS.jsonl) -- single aggregate WARNING.
# ---------------------------------------------------------------------------


def test_legacy_archived_audits_fold_into_a_single_warning(tmp_path: Path) -> None:
    """Two legacy (pre-canon) archived audits collapse into ONE WARNING, never an
    ERROR -- N legacy directories must never become N false positives."""
    specs = tmp_path / "specs"
    archive = specs / "audits" / "_archive"
    for name in ("20260607T023738Z-782f775d", "20260608T035551Z-da1a1b2c"):
        d = archive / name
        d.mkdir(parents=True)
        (d / "DISPOSITION.md").write_text("**Disposition:** v0.1.46\n", encoding="utf-8")
    # A loose legacy .md file directly under _archive/ (pre-dir-canon shape) counts too.
    (archive / "2026-07-06-legacy-lane--dispositioned-v0.1.61.md").write_text(
        "# legacy\n", encoding="utf-8"
    )

    warns = _codes(specs, "SPEC-DOC-036")
    assert len(warns) == 1, f"Expected exactly one aggregate legacy WARNING, got: {warns}"
    assert warns[0].severity is Severity.WARNING
    for name in (
        "20260607T023738Z-782f775d",
        "20260608T035551Z-da1a1b2c",
        "2026-07-06-legacy-lane--dispositioned-v0.1.61.md",
    ):
        assert name in warns[0].description
    errs = _codes(specs, "SPEC-DOC-036")
    assert all(i.severity is not Severity.ERROR for i in errs)


def test_readme_is_never_a_legacy_entry(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    archive = specs / "audits" / "_archive"
    archive.mkdir(parents=True)
    (archive / "README.md").write_text("# Audits archive\n", encoding="utf-8")

    assert _codes(specs, "SPEC-DOC-036") == []


# ---------------------------------------------------------------------------
# Silent / absent-dir matrix.
# ---------------------------------------------------------------------------


def test_absent_audits_dir_is_silent_for_both_codes(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir(parents=True)
    assert _codes(specs, "SPEC-DOC-036") == []
    assert _codes(specs, "SPEC-DOC-038") == []


def test_absent_archive_subdir_is_silent_for_doc036(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "audits").mkdir(parents=True)
    assert _codes(specs, "SPEC-DOC-036") == []


# ---------------------------------------------------------------------------
# A15.1 -- the regex path is deleted, not merely bypassed.
# ---------------------------------------------------------------------------


def test_disposition_regex_helpers_are_gone() -> None:
    """A15.1: the deleted regex + its matcher method no longer exist on the module
    or the validator -- a bypass would keep the symbol; a deletion removes it."""
    import dadaia_workspace.features.specs.doctor_closure_audit as module

    assert not hasattr(module, "_AUDIT_DISPOSITION_RE")
    assert not hasattr(ClosureAuditValidator, "_audit_has_disposition")
