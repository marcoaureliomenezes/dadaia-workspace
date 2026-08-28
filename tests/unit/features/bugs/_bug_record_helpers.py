"""Shared test-only helper: build a real ``JsonlRecordStore[BugRecord]`` rooted at a
``tmp_path``'s ``bugs/BUGS.jsonl`` — the exact composition ``container.build_bug_record_store``
performs at the CLI seam, without depending on ``container``/CLI wiring at all (v0.5.0
T-050-08). Not a test module itself (no ``test_`` prefix, not collected).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.bugs import BugRecord
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

__all__ = ["bug_archive_store", "bug_record_store"]


def bug_record_store(tmp_path: Path) -> JsonlRecordStore[BugRecord]:
    return JsonlRecordStore(
        tmp_path / "bugs" / "BUGS.jsonl",
        to_dict=BugRecord.to_dict,
        from_dict=BugRecord.from_dict,
    )


def bug_archive_store(tmp_path: Path) -> JsonlRecordStore[BugRecord]:
    return JsonlRecordStore(
        tmp_path / "bugs" / "_archive" / "bugs_histo.jsonl",
        to_dict=BugRecord.to_dict,
        from_dict=BugRecord.from_dict,
    )
