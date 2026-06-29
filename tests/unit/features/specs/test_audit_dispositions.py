"""SPEC-DOC-033 audit disposition doctor checks."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs.doctor import Severity, SpecsDoctor


def _audit_disposition_issues(specs_dir: Path):
    return SpecsDoctor(specs_dir)._check_audit_dispositions()  # noqa: SLF001


def test_live_audit_finding_without_disposition_is_warning(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    audit = specs_dir / "audits" / "scan.md"
    audit.parent.mkdir(parents=True)
    audit.write_text("finding_id: F-001\nseverity: high\n", encoding="utf-8")

    issues = _audit_disposition_issues(specs_dir)

    assert [(issue.code, issue.severity) for issue in issues] == [
        ("SPEC-DOC-033", Severity.WARNING)
    ]


def test_archived_audit_finding_without_disposition_is_error(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    audit = specs_dir / "audits" / "_archive" / "scan.md"
    audit.parent.mkdir(parents=True)
    audit.write_text("finding_id: F-001\nseverity: high\n", encoding="utf-8")

    issues = _audit_disposition_issues(specs_dir)

    assert [(issue.code, issue.severity) for issue in issues] == [
        ("SPEC-DOC-033", Severity.ERROR)
    ]


def test_audit_finding_rejects_legacy_disposition_tokens(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    audit = specs_dir / "audits" / "scan.md"
    audit.parent.mkdir(parents=True)
    audit.write_text(
        "finding_id: F-001\nseverity: high\ndisposition: accepted-risk\n",
        encoding="utf-8",
    )

    issues = _audit_disposition_issues(specs_dir)

    assert [(issue.code, issue.severity) for issue in issues] == [
        ("SPEC-DOC-033", Severity.ERROR)
    ]
    assert "accepted-risk" in issues[0].description


def test_audit_finding_accepts_canonical_disposition_per_finding(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    audit = specs_dir / "audits" / "scan.md"
    audit.parent.mkdir(parents=True)
    audit.write_text(
        "\n".join(
            [
                "- finding_id: F-001",
                "  disposition: fixed",
                "  route: v0.1.40",
                "- finding_id: F-002",
                "  disposition: deferred",
                "  route: backlog/foo",
            ]
        ),
        encoding="utf-8",
    )

    assert _audit_disposition_issues(specs_dir) == []


def test_audit_finding_requires_disposition_for_each_finding(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    audit = specs_dir / "audits" / "scan.md"
    audit.parent.mkdir(parents=True)
    audit.write_text(
        "\n".join(
            [
                "- finding_id: F-001",
                "  disposition: fixed",
                "- finding_id: F-002",
                "  route: backlog/foo",
            ]
        ),
        encoding="utf-8",
    )

    issues = _audit_disposition_issues(specs_dir)

    assert [(issue.code, issue.severity) for issue in issues] == [
        ("SPEC-DOC-033", Severity.WARNING)
    ]
