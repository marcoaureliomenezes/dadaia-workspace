"""Unit tests for dadaia_workspace/infrastructure/bug_reporter.py — T-BCR-06."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from dadaia_workspace.infrastructure.bug_reporter import (
    append_entry,
    report_doctor_finding,
    report_exception,
)

# ---------------------------------------------------------------------------
# report_exception
# ---------------------------------------------------------------------------


class TestReportException:
    def test_writes_to_reported_json(self, tmp_path: Path) -> None:
        """report_exception writes one entry to .dadaia/bugs/reported.json."""
        report_exception(tmp_path, "dadaia context deactivate foo", ValueError("test error"))

        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        assert bugs_path.exists(), "reported.json must be created"

        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        assert len(entries) == 1

        entry = entries[0]
        assert entry["source"] == "cli-exception"
        assert entry["exception_type"] == "ValueError"
        assert entry["message"] == "test error"
        assert entry["status"] == "open"
        assert entry["command"] == "dadaia context deactivate foo"
        assert "id" in entry
        assert "reported_at" in entry

    def test_entry_has_traceback_tail(self, tmp_path: Path) -> None:
        """report_exception captures traceback tail."""
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            report_exception(tmp_path, "dadaia doctor", exc)

        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        assert entries[0]["traceback_tail"] is not None
        assert "RuntimeError" in entries[0]["traceback_tail"]

    def test_appends_two_entries(self, tmp_path: Path) -> None:
        """Calling report_exception twice produces two entries (atomic append)."""
        report_exception(tmp_path, "dadaia cmd1", ValueError("err1"))
        report_exception(tmp_path, "dadaia cmd2", TypeError("err2"))

        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        assert len(entries) == 2
        assert entries[0]["exception_type"] == "ValueError"
        assert entries[1]["exception_type"] == "TypeError"

    def test_never_raises_on_write_error(self, tmp_path: Path) -> None:
        """report_exception must not raise even if the write location is inaccessible."""
        # Use a path inside a read-only directory to force a write failure.
        bugs_dir = tmp_path / ".dadaia" / "bugs"
        bugs_dir.mkdir(parents=True, exist_ok=True)
        # Create file first then make parent directory read-only.
        reported_json = bugs_dir / "reported.json"
        reported_json.write_text("[]", encoding="utf-8")
        # Make the bugs dir unwritable so os.replace on .tmp fails.
        os.chmod(bugs_dir, stat.S_IRUSR | stat.S_IXUSR)
        try:
            # Must not raise — crash reporter must never crash.
            report_exception(tmp_path, "dadaia x", ValueError("fail"))
        finally:
            # Restore so tmp_path cleanup succeeds.
            os.chmod(bugs_dir, stat.S_IRWXU)


# ---------------------------------------------------------------------------
# report_doctor_finding
# ---------------------------------------------------------------------------


class TestReportDoctorFinding:
    def test_writes_entry_with_message(self, tmp_path: Path) -> None:
        """report_doctor_finding writes entry with the provided finding message."""
        report_doctor_finding(tmp_path, "doctor-public", "[missing] stage:agents/foo.md")

        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        assert bugs_path.exists()

        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        assert len(entries) == 1

        entry = entries[0]
        assert entry["message"] == "[missing] stage:agents/foo.md"
        assert entry["source"] == "doctor-public"
        assert entry["status"] == "open"
        assert entry["exception_type"] is None
        assert entry["traceback_tail"] is None

    def test_appends_multiple_findings(self, tmp_path: Path) -> None:
        """Multiple doctor findings are appended to the same file."""
        report_doctor_finding(tmp_path, "doctor-public", "[drift] stage:rules/foo.md")
        report_doctor_finding(
            tmp_path, "doctor-public", "[warn] git-dirty: dadaia_workspace/public/agents/bar.md"
        )

        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        entries = json.loads(bugs_path.read_text(encoding="utf-8"))
        assert len(entries) == 2
        assert entries[0]["message"] == "[drift] stage:rules/foo.md"
        assert entries[1]["message"] == "[warn] git-dirty: dadaia_workspace/public/agents/bar.md"

    def test_command_derived_from_source(self, tmp_path: Path) -> None:
        """Command field is derived from the source string."""
        report_doctor_finding(tmp_path, "doctor-public", "[fail] something")
        bugs_path = tmp_path / ".dadaia" / "bugs" / "reported.json"
        entry = json.loads(bugs_path.read_text(encoding="utf-8"))[0]
        assert entry["command"] == "dadaia doctor public"

    def test_never_raises_on_write_error(self, tmp_path: Path) -> None:
        """report_doctor_finding must not raise even if write fails."""
        bugs_dir = tmp_path / ".dadaia" / "bugs"
        bugs_dir.mkdir(parents=True, exist_ok=True)
        reported_json = bugs_dir / "reported.json"
        reported_json.write_text("[]", encoding="utf-8")
        os.chmod(bugs_dir, stat.S_IRUSR | stat.S_IXUSR)
        try:
            report_doctor_finding(tmp_path, "doctor-public", "[missing] x")
        finally:
            os.chmod(bugs_dir, stat.S_IRWXU)


# ---------------------------------------------------------------------------
# append_entry
# ---------------------------------------------------------------------------


class TestAppendEntry:
    def test_creates_file_if_missing(self, tmp_path: Path) -> None:
        """append_entry creates reported.json if it does not exist."""
        from dadaia_workspace.infrastructure.bug_reporter import _bugs_path

        path = _bugs_path(tmp_path)
        assert not path.exists()
        append_entry(tmp_path, {"foo": "bar"})
        assert path.exists()
        entries = json.loads(path.read_text(encoding="utf-8"))
        assert entries == [{"foo": "bar"}]

    def test_appends_to_existing(self, tmp_path: Path) -> None:
        """append_entry appends without overwriting prior entries."""
        append_entry(tmp_path, {"n": 1})
        append_entry(tmp_path, {"n": 2})
        from dadaia_workspace.infrastructure.bug_reporter import _bugs_path

        entries = json.loads(_bugs_path(tmp_path).read_text(encoding="utf-8"))
        assert entries == [{"n": 1}, {"n": 2}]

    def test_atomic_write_no_tmp_left(self, tmp_path: Path) -> None:
        """After append_entry the .tmp file must not remain on disk."""
        from dadaia_workspace.infrastructure.bug_reporter import _bugs_path

        append_entry(tmp_path, {"x": 1})
        tmp_file = _bugs_path(tmp_path).with_suffix(".tmp")
        assert not tmp_file.exists(), ".tmp sidecar must not remain after atomic write"
