"""Unit tests for dadaia_workspace/infrastructure/bug_reporter.py — T-BCR-06."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure import bug_reporter
from dadaia_workspace.infrastructure.bug_reporter import (
    _bugs_path,
    append_entry,
    report_doctor_finding,
    report_exception,
)


@pytest.fixture(autouse=True)
def _skip_git_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bug_reporter, "_git_context", lambda *_args, **_kwargs: "")


def test_report_exception_and_doctor_finding_entry_fields_traceback_and_appends(
    tmp_path: Path,
) -> None:
    """report_exception writes one entry per call with the expected fields, captures a
    traceback tail, and multiple calls append (atomic append, never overwrite).
    report_doctor_finding writes the finding message, multiple findings append, and the
    command field is derived from the source string — both share one bugs_path store."""
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

    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        report_exception(tmp_path, "dadaia doctor", exc)
    entries = json.loads(bugs_path.read_text(encoding="utf-8"))
    assert len(entries) == 2
    assert entries[1]["traceback_tail"] is not None
    assert "RuntimeError" in entries[1]["traceback_tail"]
    assert entries[1]["exception_type"] == "RuntimeError"

    report_exception(tmp_path, "dadaia cmd3", TypeError("err3"))
    entries = json.loads(bugs_path.read_text(encoding="utf-8"))
    assert len(entries) == 3
    assert entries[2]["exception_type"] == "TypeError"

    report_doctor_finding(tmp_path, "doctor-public", "[missing] stage:agents/foo.md")
    entries = json.loads(bugs_path.read_text(encoding="utf-8"))
    assert len(entries) == 4
    finding_entry = entries[3]
    assert finding_entry["message"] == "[missing] stage:agents/foo.md"
    assert finding_entry["source"] == "doctor-public"
    assert finding_entry["status"] == "open"
    assert finding_entry["exception_type"] is None
    assert finding_entry["traceback_tail"] is None
    assert finding_entry["command"] == "dadaia doctor public"

    report_doctor_finding(
        tmp_path, "doctor-public", "[warn] git-dirty: dadaia_workspace/public/agents/bar.md"
    )
    entries = json.loads(bugs_path.read_text(encoding="utf-8"))
    assert len(entries) == 5
    assert entries[4]["message"] == "[warn] git-dirty: dadaia_workspace/public/agents/bar.md"


@pytest.mark.parametrize(
    "write_fn",
    [
        lambda ws: report_exception(ws, "dadaia x", ValueError("fail")),
        lambda ws: report_doctor_finding(ws, "doctor-public", "[missing] x"),
    ],
)
def test_never_raises_on_write_error(tmp_path: Path, write_fn: object) -> None:
    """Crash-reporter writers must never raise even if the write location is
    inaccessible (a crash reporter must never itself crash)."""
    bugs_dir = tmp_path / ".dadaia" / "bugs"
    bugs_dir.mkdir(parents=True, exist_ok=True)
    reported_json = bugs_dir / "reported.json"
    reported_json.write_text("[]", encoding="utf-8")
    # Make the bugs dir unwritable so os.replace on .tmp fails.
    os.chmod(bugs_dir, stat.S_IRUSR | stat.S_IXUSR)
    try:
        write_fn(tmp_path)  # type: ignore[operator]
    finally:
        os.chmod(bugs_dir, stat.S_IRWXU)


def test_append_entry_creates_appends_and_is_atomic(tmp_path: Path) -> None:
    path = _bugs_path(tmp_path)
    assert not path.exists()
    append_entry(tmp_path, {"foo": "bar"})
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == [{"foo": "bar"}]

    append_entry(tmp_path, {"n": 2})
    assert json.loads(path.read_text(encoding="utf-8")) == [{"foo": "bar"}, {"n": 2}]

    tmp_file = path.with_suffix(".tmp")
    assert not tmp_file.exists(), ".tmp sidecar must not remain after atomic write"
