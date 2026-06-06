"""Unit tests for T-PANEL-02: ReportsDoctor RPT-1 dangling-artifact-path invariant.

Acceptance criteria (TASKS.md T-PANEL-02):
  1. RPT-1 flags any .handoff.json whose artifact.path points at a non-HTML file
     or a missing file → [dangling-artifact-path] emitted.
  2. A sidecar-less HTML report does NOT trigger RPT-1.
  3. Three unit tests pass: test_invariant_clean_passes,
     test_dangling_artifact_path_flagged, test_missing_html_sidecar_not_flagged.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.panel.reports_doctor import ReportsDoctor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_handoff(
    workspace: Path,
    context: str,
    filename: str,
    artifact_path: str | None,
    *,
    agent: str = "qa-engineer",
    produced_at: str = "2026-06-05T12:00:00Z",
) -> Path:
    """Write a minimal .handoff.json under .dadaia/handoff/<context>/."""
    handoff_dir = workspace / ".dadaia" / "handoff" / context
    handoff_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = handoff_dir / filename

    doc: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": agent,
        "context": context,
        "produced_at": produced_at,
    }
    if artifact_path is not None:
        doc["artifact"] = {
            "type": "report",
            "path": artifact_path,
            "content_hash": "a" * 64,
        }

    handoff_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return handoff_path


def _write_report(workspace: Path, context: str, agent: str, filename: str) -> Path:
    """Write a minimal HTML report under .dadaia/reports/<context>/<agent>/."""
    report_dir = workspace / ".dadaia" / "reports" / context / agent
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / filename
    report_path.write_text("<html>report</html>", encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# AC-1: clean state — no issues emitted
# ---------------------------------------------------------------------------


def test_invariant_clean_passes(tmp_path: Path) -> None:
    """RPT-1 AC-1: handoff whose artifact.path resolves to an existing .html → no issue."""
    # Create an HTML report
    _write_report(tmp_path, "ctx", "qa-engineer", "2026-06-05T120000Z-qa-report.html")

    # Create a handoff pointing to that report
    _write_handoff(
        tmp_path,
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-qa-report.handoff.json",
        artifact_path=".dadaia/reports/ctx/qa-engineer/2026-06-05T120000Z-qa-report.html",
    )

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert result.ok, (
        f"Expected no issues for clean state, got: {[i.message for i in result.issues]}"
    )
    assert result.issues == []


def test_invariant_no_handoffs_passes(tmp_path: Path) -> None:
    """RPT-1: workspace with only an HTML report (no sidecar) is clean."""
    _write_report(tmp_path, "ctx", "software-engineer-python", "2026-06-05T120000Z-impl.html")
    # No handoff directory at all.

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert result.ok, f"Expected no issues, got: {[i.message for i in result.issues]}"


# ---------------------------------------------------------------------------
# AC-2: dangling artifact.path → [dangling-artifact-path] flagged
# ---------------------------------------------------------------------------


def test_dangling_artifact_path_flagged_missing_file(tmp_path: Path) -> None:
    """RPT-1 AC-2: artifact.path points to a missing HTML → flagged."""
    _write_handoff(
        tmp_path,
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-missing.handoff.json",
        # The HTML file does NOT exist
        artifact_path=".dadaia/reports/ctx/qa-engineer/2026-06-05T120000Z-missing.html",
    )

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert not result.ok
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == "RPT-1"
    assert "[dangling-artifact-path]" in issue.message


def test_dangling_artifact_path_flagged_wrong_type(tmp_path: Path) -> None:
    """RPT-1 AC-2: artifact.path points to a non-HTML file → flagged."""
    # Create a .json file where an .html is expected
    artifact_dir = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    non_html = artifact_dir / "2026-06-05T120000Z-qa.json"
    non_html.write_text("{}", encoding="utf-8")

    _write_handoff(
        tmp_path,
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-qa.handoff.json",
        artifact_path=".dadaia/reports/ctx/qa-engineer/2026-06-05T120000Z-qa.json",
    )

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert not result.ok
    issues = [i for i in result.issues if i.code == "RPT-1"]
    assert issues, f"Expected RPT-1 issue, got: {result.issues}"
    assert "[dangling-artifact-path]" in issues[0].message


def test_dangling_artifact_path_flagged_non_canonical_prefix(tmp_path: Path) -> None:
    """RPT-1 AC-2: artifact.path does not start with .dadaia/reports/ → flagged."""
    _write_handoff(
        tmp_path,
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-qa.handoff.json",
        artifact_path="some/other/path.html",  # non-canonical prefix
    )

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert not result.ok
    assert any(i.code == "RPT-1" for i in result.issues)
    assert any("[dangling-artifact-path]" in i.message for i in result.issues)


# Combined: this IS the named AC-2 test from the spec
def test_dangling_artifact_path_flagged(tmp_path: Path) -> None:
    """RPT-1 named AC-2: single handoff with missing-file artifact.path → issue emitted."""
    _write_handoff(
        tmp_path,
        context="dadaia-workspace",
        filename="2026-06-05T120000Z-software-engineer-python-report.handoff.json",
        artifact_path=".dadaia/reports/dadaia-workspace/software-engineer-python/does-not-exist.html",
    )

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert len(result.issues) == 1
    assert result.issues[0].code == "RPT-1"
    assert "[dangling-artifact-path]" in result.issues[0].message


# ---------------------------------------------------------------------------
# AC-3: sidecar-less HTML report does NOT trigger RPT-1
# ---------------------------------------------------------------------------


def test_missing_html_sidecar_not_flagged(tmp_path: Path) -> None:
    """RPT-1 AC-3: an HTML report with no handoff sidecar is valid — no issue emitted."""
    # Create the HTML report
    _write_report(tmp_path, "ctx", "code-reviewer", "2026-06-05T120000Z-code-review.html")
    # Deliberately create NO corresponding handoff file.

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert result.ok, (
        "RPT-1 must not flag an HTML report that has no sidecar. "
        f"Got issues: {[i.message for i in result.issues]}"
    )


# ---------------------------------------------------------------------------
# Edge cases: handoff without artifact.path (handoff-first emission)
# ---------------------------------------------------------------------------


def test_handoff_without_artifact_path_not_flagged(tmp_path: Path) -> None:
    """RPT-1: handoff-first sidecar with no artifact.path field → no issue."""
    _write_handoff(
        tmp_path,
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-handoff-first.handoff.json",
        artifact_path=None,  # omitted (handoff-first emission pattern)
    )

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert result.ok, f"Expected no issues for handoff-first sidecar, got: {result.issues}"


# ---------------------------------------------------------------------------
# Multiple sidecars: mix of clean and dangling
# ---------------------------------------------------------------------------


def test_only_dangling_sidecars_flagged(tmp_path: Path) -> None:
    """RPT-1: only the dangling sidecar is flagged when mix of clean and dangling exist."""
    # Clean sidecar — report exists
    _write_report(tmp_path, "ctx", "qa-engineer", "2026-06-05T120000Z-clean-report.html")
    _write_handoff(
        tmp_path,
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-clean.handoff.json",
        artifact_path=".dadaia/reports/ctx/qa-engineer/2026-06-05T120000Z-clean-report.html",
    )

    # Dangling sidecar — report missing
    _write_handoff(
        tmp_path,
        context="ctx",
        filename="2026-06-05T120001Z-qa-engineer-dangling.handoff.json",
        artifact_path=".dadaia/reports/ctx/qa-engineer/2026-06-05T120001Z-gone.html",
    )

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert len(result.issues) == 1
    assert result.issues[0].code == "RPT-1"
    assert "gone.html" in result.issues[0].message
