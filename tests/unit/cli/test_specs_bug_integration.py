"""Unit tests for T-BCR-07 — bug surfacing in `dadaia specs hotfix open`."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from dadaia_workspace.infrastructure.bug_reporter import (
    load_open_bugs,
    mark_bugs_in_release,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_bugs(workspace_root: Path, entries: list[dict]) -> None:
    bugs_dir = workspace_root / ".dadaia" / "bugs"
    bugs_dir.mkdir(parents=True, exist_ok=True)
    (bugs_dir / "reported.json").write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# load_open_bugs
# ---------------------------------------------------------------------------


class TestLoadOpenBugs:
    def test_returns_only_open_entries(self, tmp_path: Path) -> None:
        """load_open_bugs returns only entries with status='open'."""
        _write_bugs(
            tmp_path,
            [
                {"id": "a1", "status": "open", "message": "bug one"},
                {"id": "a2", "status": "in_release", "message": "bug two"},
                {"id": "a3", "status": "resolved", "message": "bug three"},
                {"id": "a4", "status": "open", "message": "bug four"},
            ],
        )
        result = load_open_bugs(tmp_path)
        assert len(result) == 2
        assert result[0]["id"] == "a1"
        assert result[1]["id"] == "a4"

    def test_returns_empty_when_no_open_entries(self, tmp_path: Path) -> None:
        """load_open_bugs returns [] when no entry has status='open'."""
        _write_bugs(
            tmp_path,
            [
                {"id": "b1", "status": "resolved", "message": "done"},
            ],
        )
        assert load_open_bugs(tmp_path) == []

    def test_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        """load_open_bugs returns [] silently when reported.json does not exist."""
        assert load_open_bugs(tmp_path) == []

    def test_returns_all_when_all_open(self, tmp_path: Path) -> None:
        """load_open_bugs returns all entries when all are 'open'."""
        _write_bugs(
            tmp_path,
            [
                {"id": "c1", "status": "open", "message": "x"},
                {"id": "c2", "status": "open", "message": "y"},
            ],
        )
        result = load_open_bugs(tmp_path)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# mark_bugs_in_release
# ---------------------------------------------------------------------------


class TestMarkBugsInRelease:
    def test_marks_specified_ids_as_in_release(self, tmp_path: Path) -> None:
        """mark_bugs_in_release updates only the listed IDs."""
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
        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        statuses = {e["id"]: e["status"] for e in entries}
        assert statuses["d1"] == "in_release"
        assert statuses["d2"] == "open"  # unchanged
        assert statuses["d3"] == "in_release"

    def test_leaves_resolved_entries_unchanged(self, tmp_path: Path) -> None:
        """mark_bugs_in_release does not alter non-matching entries."""
        _write_bugs(
            tmp_path,
            [
                {"id": "e1", "status": "resolved", "message": "old"},
                {"id": "e2", "status": "open", "message": "new"},
            ],
        )
        mark_bugs_in_release(tmp_path, ["e2"])

        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        statuses = {e["id"]: e["status"] for e in entries}
        assert statuses["e1"] == "resolved"
        assert statuses["e2"] == "in_release"

    def test_empty_ids_list_changes_nothing(self, tmp_path: Path) -> None:
        """mark_bugs_in_release with empty list leaves all entries unchanged."""
        _write_bugs(
            tmp_path,
            [
                {"id": "f1", "status": "open", "message": "bug"},
            ],
        )
        mark_bugs_in_release(tmp_path, [])

        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        assert entries[0]["status"] == "open"

    def test_atomic_write_no_tmp_left(self, tmp_path: Path) -> None:
        """mark_bugs_in_release must not leave a .tmp file on disk."""
        _write_bugs(tmp_path, [{"id": "g1", "status": "open", "message": "x"}])
        mark_bugs_in_release(tmp_path, ["g1"])

        tmp_file = (tmp_path / ".dadaia" / "bugs" / "reported.json").with_suffix(".tmp")
        assert not tmp_file.exists()


# ---------------------------------------------------------------------------
# _prompt_open_bugs — integration with typer.confirm and typer.echo
# ---------------------------------------------------------------------------


class TestPromptOpenBugs:
    """Tests for specs._prompt_open_bugs helper."""

    def _import_prompt(self):
        from dadaia_workspace.cli.commands.specs import _prompt_open_bugs

        return _prompt_open_bugs

    def test_no_bugs_no_output_no_confirm(self, tmp_path: Path) -> None:
        """When no open bugs exist, _prompt_open_bugs must be silent."""
        _prompt_open_bugs = self._import_prompt()

        with (
            patch("typer.echo") as mock_echo,
            patch("typer.confirm") as mock_confirm,
        ):
            _prompt_open_bugs(tmp_path)

        mock_echo.assert_not_called()
        mock_confirm.assert_not_called()

    def test_missing_file_no_output(self, tmp_path: Path) -> None:
        """When reported.json is absent, _prompt_open_bugs must be silent."""
        _prompt_open_bugs = self._import_prompt()

        with (
            patch("typer.echo") as mock_echo,
            patch("typer.confirm") as mock_confirm,
        ):
            _prompt_open_bugs(tmp_path)

        mock_echo.assert_not_called()
        mock_confirm.assert_not_called()

    def test_bugs_exist_operator_confirms_marks_in_release(self, tmp_path: Path) -> None:
        """When bugs exist and operator confirms, all are marked in_release."""
        _write_bugs(
            tmp_path,
            [
                {"id": "h1", "status": "open", "message": "a short bug message"},
                {"id": "h2", "status": "open", "message": "another bug"},
            ],
        )
        _prompt_open_bugs = self._import_prompt()

        with (
            patch("typer.echo") as mock_echo,
            patch("typer.confirm", return_value=True) as mock_confirm,
        ):
            _prompt_open_bugs(tmp_path)

        mock_confirm.assert_called_once()

        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        for entry in entries:
            assert entry["status"] == "in_release"

        # Should have printed header + per-bug lines + success line
        echo_calls = [str(c.args[0]) for c in mock_echo.call_args_list]
        assert any("h1" in c or "2 known bug" in c or "bug(s)" in c for c in echo_calls)

    def test_bugs_exist_operator_declines_entries_unchanged(self, tmp_path: Path) -> None:
        """When bugs exist and operator declines, entries stay 'open'."""
        _write_bugs(
            tmp_path,
            [
                {"id": "i1", "status": "open", "message": "some bug"},
            ],
        )
        _prompt_open_bugs = self._import_prompt()

        with (
            patch("typer.echo") as mock_echo,
            patch("typer.confirm", return_value=False),
        ):
            _prompt_open_bugs(tmp_path)

        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        assert entries[0]["status"] == "open"

        # Operator should see a message about leaving bugs as open
        echo_calls = [str(c.args[0]) for c in mock_echo.call_args_list]
        assert any("open" in c.lower() for c in echo_calls)

    def test_header_includes_count(self, tmp_path: Path) -> None:
        """Header printed when bugs exist must include the count."""
        _write_bugs(
            tmp_path,
            [
                {"id": "j1", "status": "open", "message": "msg1"},
                {"id": "j2", "status": "open", "message": "msg2"},
                {"id": "j3", "status": "open", "message": "msg3"},
            ],
        )
        _prompt_open_bugs = self._import_prompt()

        with (
            patch("typer.echo") as mock_echo,
            patch("typer.confirm", return_value=False),
        ):
            _prompt_open_bugs(tmp_path)

        echo_calls = [str(c.args[0]) for c in mock_echo.call_args_list]
        header = echo_calls[0]
        assert "3" in header

    def test_per_bug_line_truncates_message_at_120(self, tmp_path: Path) -> None:
        """Each bug line must truncate its message at 120 characters."""
        long_message = "x" * 200
        _write_bugs(
            tmp_path,
            [
                {
                    "id": "k1",
                    "status": "open",
                    "source": "cli-exception",
                    "message": long_message,
                }
            ],
        )
        _prompt_open_bugs = self._import_prompt()

        with (
            patch("typer.echo") as mock_echo,
            patch("typer.confirm", return_value=False),
        ):
            _prompt_open_bugs(tmp_path)

        # Find the line that contains the bug message (second echo after header)
        echo_calls = [str(c.args[0]) for c in mock_echo.call_args_list]
        bug_line = echo_calls[1]  # first is header
        # The message portion should be at most 120 chars; the full long_message is 200
        assert long_message not in bug_line
        assert "x" * 120 in bug_line or "x" * 119 in bug_line
