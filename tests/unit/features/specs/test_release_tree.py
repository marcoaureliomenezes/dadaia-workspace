"""Intent: CONTRACT — T-047-97: the doctor rule `RELEASE-TREE-MEMORY` turns a candidate PR
red until the closure's memory reconciliation actually happened. Size: SMALL.

The rule reads the state document and nothing else (P-02/P-03: no git, no subprocess in a
feature), so every case here is a `_RELEASE.json` on disk and an assertion about the issues
it produces.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.release_tree import release_memory_issues

pytestmark = pytest.mark.unit

_IMPLEMENTED = "2026-09-22T10:00:00Z"


def _entry(ts: str, **over: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "ts": ts,
        "agent": "release.py memory",
        "kind": "memory",
        "text": "Memory reconciled over the window.",
        "since": "0000001",
        "until": "0000003",
        "reviewed": ["panel"],
        "changed": ["workspace-doctor"],
    }
    entry.update(over)
    return entry


def _specs(tmp_path: Path, phase: str, log: list[dict[str, object]]) -> Path:
    specs = tmp_path / "specs"
    release_dir = specs / "releases" / "0.5.0"
    release_dir.mkdir(parents=True)
    (release_dir / "_RELEASE.json").write_text(
        json.dumps({
            "schema": "release-state-v1",
            "release": "0.5.0",
            "phase": phase,
            "defined": {"sha": "0000001", "ts": "2026-09-20T10:00:00Z"},
            "implemented": {"sha": "0000002", "ts": _IMPLEMENTED},
            "shipped": None,
            "log": log,
        }),
        encoding="utf-8",
    )  # fmt: skip
    return specs


def test_closure_without_any_memory_entry_is_an_error(tmp_path: Path) -> None:
    specs = _specs(tmp_path, "CLOSURE", [])

    issues = release_memory_issues(specs)

    assert [i.code for i in issues] == ["RELEASE-TREE-MEMORY"]
    assert issues[0].path == "releases/0.5.0/_RELEASE.json"
    assert "memory" in issues[0].description


def test_a_prose_only_memory_entry_is_an_error(tmp_path: Path) -> None:
    """The five historical free-prose entries are history, not a supported form: an entry
    without since/reviewed/changed dispositioned nothing."""
    prose = {"ts": "2026-09-22T11:00:00Z", "agent": "pm", "kind": "memory", "text": "done"}
    specs = _specs(tmp_path, "CLOSURE", [prose])

    issues = release_memory_issues(specs)

    assert [i.code for i in issues] == ["RELEASE-TREE-MEMORY"]
    assert "since" in issues[0].description


def test_an_entry_stamped_before_the_implemented_milestone_does_not_count(
    tmp_path: Path,
) -> None:
    """A reconciliation predating `implemented` reconciled a window that has since moved."""
    specs = _specs(tmp_path, "CLOSURE", [_entry("2026-09-21T10:00:00Z")])

    assert [i.code for i in release_memory_issues(specs)] == ["RELEASE-TREE-MEMORY"]


def test_a_complete_entry_after_the_milestone_is_clean(tmp_path: Path) -> None:
    specs = _specs(tmp_path, "CLOSURE", [_entry("2026-09-22T12:00:00Z")])

    assert release_memory_issues(specs) == []


def test_the_latest_memory_entry_is_the_one_judged(tmp_path: Path) -> None:
    """Append-only log: a complete entry followed by a prose one leaves the release
    non-conformant — the newest entry is the claim the closure stands on."""
    specs = _specs(
        tmp_path,
        "CLOSURE",
        [
            _entry("2026-09-22T12:00:00Z"),
            {"ts": "2026-09-22T13:00:00Z", "agent": "pm", "kind": "memory", "text": "more"},
        ],
    )

    assert [i.code for i in release_memory_issues(specs)] == ["RELEASE-TREE-MEMORY"]


@pytest.mark.parametrize("phase", ["DEFINITION", "IMPLEMENTATION"])
def test_a_release_before_closure_is_never_asked_for_the_entry(tmp_path: Path, phase: str) -> None:
    assert release_memory_issues(_specs(tmp_path, phase, [])) == []


def test_an_archived_release_is_history_not_a_live_candidate(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    archived = specs / "releases" / "_archive" / "0.4.0"
    archived.mkdir(parents=True)
    (archived / "_RELEASE.json").write_text(
        json.dumps({
            "schema": "release-state-v1",
            "release": "0.4.0",
            "phase": "CLOSURE",
            "defined": None,
            "implemented": {"sha": "0000002", "ts": _IMPLEMENTED},
            "shipped": None,
            "log": [],
        }),
        encoding="utf-8",
    )  # fmt: skip

    assert release_memory_issues(specs) == []


def test_a_since_other_than_the_ledger_derived_start_is_an_error(tmp_path: Path) -> None:
    """H1: the window is derived, never chosen — a `since` that is not `defined.sha` (no
    prior memory entry) names a window the caller picked."""
    specs = _specs(tmp_path, "CLOSURE", [_entry("2026-09-22T12:00:00Z", since="0000002")])

    issues = release_memory_issues(specs)

    assert [i.code for i in issues] == ["RELEASE-TREE-MEMORY"]
    assert "0000001" in issues[0].description


def test_a_later_entry_opens_where_the_previous_one_closed(tmp_path: Path) -> None:
    """The second reconciliation starts at the first one's `until`, not at defined.sha."""
    first = _entry("2026-09-22T12:00:00Z")
    fresh = _entry("2026-09-22T13:00:00Z", since="0000003", until="0000004")
    stale = _entry("2026-09-22T13:00:00Z", since="0000001", until="0000004")

    assert release_memory_issues(_specs(tmp_path / "a", "CLOSURE", [first, fresh])) == []
    assert release_memory_issues(_specs(tmp_path / "b", "CLOSURE", [first, stale])) != []
