"""Unit tests for T-BCR-07 — bug surfacing in `dadaia specs hotfix open`.

Note: this file covers the legacy `.dadaia/bugs/reported.json` crash-reporter surfacing
(distinct from the v0.1.46 event-sourced `specs/bugs/*.jsonl` store).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from dadaia_workspace.infrastructure.bug_reporter import (
    load_open_bugs,
    mark_bugs_in_release,
)


def _write_bugs(workspace_root: Path, entries: list[dict[str, Any]]) -> None:
    bugs_dir = workspace_root / ".dadaia" / "bugs"
    bugs_dir.mkdir(parents=True, exist_ok=True)
    (bugs_dir / "reported.json").write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# load_open_bugs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "entries", "expected_ids"),
    [
        (
            "returns_only_open_entries",
            [
                {"id": "a1", "status": "open", "message": "bug one"},
                {"id": "a2", "status": "in_release", "message": "bug two"},
                {"id": "a3", "status": "resolved", "message": "bug three"},
                {"id": "a4", "status": "open", "message": "bug four"},
            ],
            ["a1", "a4"],
        ),
        (
            "returns_empty_when_no_open_entries",
            [{"id": "b1", "status": "resolved", "message": "done"}],
            [],
        ),
        ("returns_empty_when_file_missing", None, []),
        (
            "returns_all_when_all_open",
            [
                {"id": "c1", "status": "open", "message": "x"},
                {"id": "c2", "status": "open", "message": "y"},
            ],
            ["c1", "c2"],
        ),
    ],
)
def test_load_open_bugs_table(
    tmp_path: Path, name: str, entries: list[dict[str, Any]] | None, expected_ids: list[str]
) -> None:
    if entries is not None:
        _write_bugs(tmp_path, entries)
    result = load_open_bugs(tmp_path)
    assert [e["id"] for e in result] == expected_ids


# ---------------------------------------------------------------------------
# mark_bugs_in_release
# ---------------------------------------------------------------------------


def test_mark_bugs_in_release_table(tmp_path: Path) -> None:
    _write_bugs(
        tmp_path,
        [
            {"id": "d1", "status": "open", "message": "bug one"},
            {"id": "d2", "status": "open", "message": "bug two"},
            {"id": "d3", "status": "open", "message": "bug three"},
        ],
    )
    mark_bugs_in_release(tmp_path, ["d1", "d3"])
    bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
    statuses = {e["id"]: e["status"] for e in json.loads(bugs_path.read_text(encoding="utf-8"))}
    assert statuses == {"d1": "in_release", "d2": "open", "d3": "in_release"}

    # Non-matching entries (already resolved) stay unchanged.
    _write_bugs(
        tmp_path,
        [
            {"id": "e1", "status": "resolved", "message": "old"},
            {"id": "e2", "status": "open", "message": "new"},
        ],
    )
    mark_bugs_in_release(tmp_path, ["e2"])
    statuses2 = {e["id"]: e["status"] for e in json.loads(bugs_path.read_text(encoding="utf-8"))}
    assert statuses2 == {"e1": "resolved", "e2": "in_release"}

    # An empty ids list changes nothing.
    _write_bugs(tmp_path, [{"id": "f1", "status": "open", "message": "bug"}])
    mark_bugs_in_release(tmp_path, [])
    entries3 = json.loads(bugs_path.read_text(encoding="utf-8"))
    assert entries3[0]["status"] == "open"

    # Atomic write leaves no .tmp sidecar.
    tmp_file = bugs_path.with_suffix(".tmp")
    assert not tmp_file.exists()


# ---------------------------------------------------------------------------
# _prompt_open_bugs — on-disk state only (echo-content asserts dropped as help-text
# string checks; the load-bearing behavior is the on-disk status transition).
# ---------------------------------------------------------------------------


def _import_prompt() -> Callable[[Path], None]:
    from dadaia_workspace.cli.commands.specs import _prompt_open_bugs

    return _prompt_open_bugs


@pytest.mark.parametrize(
    ("confirm_return", "expected_status"),
    [
        pytest.param(True, "in_release", id="confirms-marks-all-in-release"),
        pytest.param(False, "open", id="declines-leaves-entries-unchanged"),
    ],
)
def test_operator_confirm_decline_matrix(
    tmp_path: Path, confirm_return: bool, expected_status: str
) -> None:
    _write_bugs(
        tmp_path,
        [
            {"id": "h1", "status": "open", "message": "a short bug message"},
            {"id": "h2", "status": "open", "message": "another bug"},
        ],
    )
    _prompt_open_bugs = _import_prompt()
    with patch("typer.echo"), patch("typer.confirm", return_value=confirm_return) as mock_confirm:
        _prompt_open_bugs(tmp_path)
    mock_confirm.assert_called_once()

    bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
    entries = json.loads(bugs_path.read_text(encoding="utf-8"))
    assert all(e["status"] == expected_status for e in entries)
