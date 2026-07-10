"""v0.1.73 FR1 — ``bugs-single-file`` migration (bug
``bugs-store-fragments-into-hourly-files``, HIGH). Operator contract: ONE append-only
``bugs.jsonl``; hourly fragments + 99 archived ``.md`` sources consolidate losslessly."""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.migrate.bugs_single_file import migrate_bugs_single_file


def _specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "bugs" / "_archive").mkdir(parents=True)
    return specs


def _line(bug_id: str, ts: str) -> str:
    return json.dumps({"bug_id": bug_id, "event": "reported", "ts": ts, "reported_by": "t"}) + "\n"


def test_consolidates_hourly_files_chronologically_before_canonical_tail(tmp_path: Path) -> None:
    """CRITICAL: v0.1.73 hourly→single-file consolidation losslessness — chronological
    ordering with the canonical tail file's own rows appended last."""
    specs = _specs(tmp_path)
    bugs = specs / "bugs"
    (bugs / "20260604T00Z-00.jsonl").write_text(_line("old-a", "2026-06-04T00:01:00Z"))
    (bugs / "20260709T14Z-00.jsonl").write_text(
        _line("mid-b", "2026-07-09T14:01:00Z") + _line("mid-c", "2026-07-09T14:02:00Z")
    )
    (bugs / "bugs.jsonl").write_text(_line("new-tail", "2026-07-09T21:00:00Z"))

    result = migrate_bugs_single_file(specs, dry_run=False)

    remaining = sorted(p.name for p in bugs.glob("*.jsonl"))
    assert remaining == ["bugs.jsonl"]
    ids = [json.loads(ln)["bug_id"] for ln in (bugs / "bugs.jsonl").read_text().splitlines()]
    assert ids == ["old-a", "mid-b", "mid-c", "new-tail"]  # chronological, tail last
    assert len(result.moved) == 2


def test_collapses_archive_md_into_single_jsonl_losslessly(tmp_path: Path) -> None:
    """CRITICAL: every archived .md source's verbatim content survives the collapse."""
    specs = _specs(tmp_path)
    archive = specs / "bugs" / "_archive"
    (archive / "old-bug-one.md").write_text("---\nstatus: Closed\n---\n\nBody one.\n")
    (archive / "old-bug-two.md").write_text("# Two\n\nBody two.\n")

    migrate_bugs_single_file(specs, dry_run=False)

    assert sorted(p.name for p in archive.iterdir()) == ["archive.jsonl"]
    rows = [json.loads(ln) for ln in (archive / "archive.jsonl").read_text().splitlines()]
    assert {r["file"] for r in rows} == {"old-bug-one.md", "old-bug-two.md"}
    assert any(r["content"].endswith("Body one.\n") for r in rows)  # verbatim content


def test_dry_run_plans_only_and_idempotent_second_run_is_noop(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    bugs = specs / "bugs"
    (bugs / "20260604T00Z-00.jsonl").write_text(_line("a", "2026-06-04T00:01:00Z"))
    (bugs / "_archive" / "x.md").write_text("body\n")

    dry_result = migrate_bugs_single_file(specs, dry_run=True)
    assert (bugs / "20260604T00Z-00.jsonl").exists()
    assert not (bugs / "bugs.jsonl").exists()
    assert (bugs / "_archive" / "x.md").exists()
    assert len(dry_result.moved) == 2  # planned

    migrate_bugs_single_file(specs, dry_run=False)
    before = (bugs / "bugs.jsonl").read_text()
    result = migrate_bugs_single_file(specs, dry_run=False)
    assert (bugs / "bugs.jsonl").read_text() == before
    assert result.moved == []
