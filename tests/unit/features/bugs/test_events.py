from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.bugs.events import (
    append_event,
    bug_stats,
    bug_status,
    make_event,
    migrate_markdown_bugs,
)


def _specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "bugs").mkdir(parents=True)
    return specs


def test_append_status_and_stats(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    append_event(
        specs,
        make_event(
            bug_id="sample-bug",
            event="reported",
            reported_by="tester",
            title="Sample bug",
            severity="HIGH",
            surface="cli",
            context="dadaia-workspace",
            symptom="broken",
        ),
    )
    append_event(
        specs,
        make_event(
            bug_id="sample-bug",
            event="resolved",
            reported_by="tester",
            release="v0.1.40",
        ),
    )

    assert bug_status(specs)["sample-bug"]["state"] == "resolved"
    assert bug_stats(specs) == {
        "events": 2,
        "bugs": 1,
        "open": 0,
        "terminal": 1,
        "by_event": {"reported": 1, "resolved": 1},
    }


def test_non_reported_event_requires_prior_report(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    event = make_event(
        bug_id="sample-bug",
        event="resolved",
        reported_by="tester",
        release="v0.1.40",
    )

    with pytest.raises(ValueError, match="requires a prior reported event"):
        append_event(specs, event)


def test_migrate_markdown_bugs_preview_and_apply(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    bug = specs / "bugs" / "legacy-bug.md"
    bug.write_text(
        "---\n"
        "name: legacy-bug\n"
        "status: Closed\n"
        "severity: MEDIUM\n"
        "surface: cli\n"
        "session_id: sess-test\n"
        "release: v0.1.39\n"
        "---\n\n"
        "# Legacy bug\n",
        encoding="utf-8",
    )

    preview = migrate_markdown_bugs(specs)
    assert preview == {"apply": False, "migrated": ["legacy-bug.md"], "count": 1}
    assert bug.exists()

    applied = migrate_markdown_bugs(specs, apply=True)
    assert applied["count"] == 1
    assert not bug.exists()
    assert (specs / "bugs" / "_archive" / "legacy-bug.md").is_file()
    assert bug_status(specs)["legacy-bug"]["state"] == "resolved"
