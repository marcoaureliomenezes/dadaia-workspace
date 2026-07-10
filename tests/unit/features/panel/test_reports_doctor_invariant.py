"""Unit tests for T-PANEL-02: ReportsDoctor RPT-1 dangling-artifact-path invariant.

Two survivors:
  1. RPT-1 dangling param (missing file / wrong type / non-canonical prefix /
     named AC-2) — one issue emitted, code RPT-1, message tagged
     [dangling-artifact-path].
  2. Clean states param (clean, no-handoffs, sidecar-less, no-artifact-path,
     mixed-flags-only-dangling) — no false positives, and a mix only flags the
     actually-dangling sidecar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.panel.reports_doctor import ReportsDoctor

pytestmark = pytest.mark.unit


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
        doc["artifact"] = {"type": "report", "path": artifact_path, "content_hash": "a" * 64}

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
# 1. RPT-1 dangling param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "artifact_path",
    [
        pytest.param(
            ".dadaia/reports/ctx/qa-engineer/2026-06-05T120000Z-missing.html",
            id="missing-file",
        ),
        pytest.param("some/other/path.html", id="non-canonical-prefix"),
        pytest.param(
            ".dadaia/reports/dadaia-workspace/software-engineer-python/does-not-exist.html",
            id="named-ac-2",
        ),
        pytest.param(
            ".dadaia/reports/ctx/qa-engineer/2026-06-05T120000Z-qa.json",
            id="wrong-type-non-html",
        ),
    ],
)
def test_dangling_artifact_path_flagged(tmp_path: Path, artifact_path: str) -> None:
    if artifact_path.endswith(".json"):
        # The wrong-type row needs the non-HTML file to actually exist on disk
        # so the invariant fires on "not .html", not on "missing file".
        artifact_dir = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "2026-06-05T120000Z-qa.json").write_text("{}", encoding="utf-8")

    _write_handoff(
        tmp_path,
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-dangling.handoff.json",
        artifact_path=artifact_path,
    )

    doctor = ReportsDoctor(tmp_path)
    result = doctor.check()

    assert not result.ok
    assert len(result.issues) == 1
    assert result.issues[0].code == "RPT-1"
    assert "[dangling-artifact-path]" in result.issues[0].message


# ---------------------------------------------------------------------------
# 2. Clean states param — no false positives + only the dangling one flags
# ---------------------------------------------------------------------------


def test_clean_states_yield_no_issues(tmp_path: Path) -> None:
    # (a) Clean: artifact.path resolves to an existing .html.
    _write_report(tmp_path / "a", "ctx", "qa-engineer", "2026-06-05T120000Z-qa-report.html")
    _write_handoff(
        tmp_path / "a",
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-qa-report.handoff.json",
        artifact_path=".dadaia/reports/ctx/qa-engineer/2026-06-05T120000Z-qa-report.html",
    )
    result_a = ReportsDoctor(tmp_path / "a").check()
    assert result_a.ok and result_a.issues == []

    # (b) No handoffs at all — only an HTML report.
    _write_report(tmp_path / "b", "ctx", "software-engineer-python", "2026-06-05T120000Z-impl.html")
    result_b = ReportsDoctor(tmp_path / "b").check()
    assert result_b.ok

    # (c) Sidecar-less HTML report — no corresponding handoff.
    _write_report(tmp_path / "c", "ctx", "code-reviewer", "2026-06-05T120000Z-code-review.html")
    result_c = ReportsDoctor(tmp_path / "c").check()
    assert result_c.ok

    # (d) Handoff-first sidecar with no artifact.path field (omitted).
    _write_handoff(
        tmp_path / "d",
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-handoff-first.handoff.json",
        artifact_path=None,
    )
    result_d = ReportsDoctor(tmp_path / "d").check()
    assert result_d.ok

    # (e) Mixed: one clean sidecar + one dangling sidecar -> only the dangling
    # one is flagged.
    _write_report(tmp_path / "e", "ctx", "qa-engineer", "2026-06-05T120000Z-clean-report.html")
    _write_handoff(
        tmp_path / "e",
        context="ctx",
        filename="2026-06-05T120000Z-qa-engineer-clean.handoff.json",
        artifact_path=".dadaia/reports/ctx/qa-engineer/2026-06-05T120000Z-clean-report.html",
    )
    _write_handoff(
        tmp_path / "e",
        context="ctx",
        filename="2026-06-05T120001Z-qa-engineer-dangling.handoff.json",
        artifact_path=".dadaia/reports/ctx/qa-engineer/2026-06-05T120001Z-gone.html",
    )
    result_e = ReportsDoctor(tmp_path / "e").check()
    assert len(result_e.issues) == 1
    assert result_e.issues[0].code == "RPT-1"
    assert "gone.html" in result_e.issues[0].message
