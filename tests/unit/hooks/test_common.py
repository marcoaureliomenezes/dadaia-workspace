"""Unit tests for dadaia_workspace.hooks._common shared primitives."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pytest

from dadaia_workspace.hooks import _common


def test_read_stdin_json_parses_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_name": "Write"})))
    assert _common.read_stdin_json() == {"tool_name": "Write"}


def test_read_stdin_json_empty_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("   "))
    assert _common.read_stdin_json() == {}


def test_read_stdin_json_invalid_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
    assert _common.read_stdin_json() == {}


def test_read_stdin_json_non_object_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("[1, 2, 3]"))
    assert _common.read_stdin_json() == {}


def test_tool_name_handles_both_keys() -> None:
    assert _common.tool_name({"tool_name": "Write"}) == "Write"
    assert _common.tool_name({"tool": "edit_file"}) == "edit_file"
    assert _common.tool_name({}) == ""


def test_is_write_tool() -> None:
    assert _common.is_write_tool("Write")
    assert _common.is_write_tool("apply_patch")
    assert not _common.is_write_tool("Read")


def test_target_path_direct_keys() -> None:
    assert _common.target_path({"tool_input": {"file_path": "/a/b.py"}}) == "/a/b.py"
    assert _common.target_path({"path": "/c.py"}) == "/c.py"
    assert _common.target_path({"tool_input": {"notebook_path": "/n.ipynb"}}) == "/n.ipynb"


def test_target_path_apply_patch_header() -> None:
    cmd = "*** Begin Patch\n*** Add File: repos/x/foo.py\n+code\n*** End Patch"
    assert _common.target_path({"tool_input": {"command": cmd}}) == "repos/x/foo.py"


def test_target_path_unparseable_returns_empty() -> None:
    assert _common.target_path({"tool_input": {}}) == ""


# --------------------------------------------------------------------------- #
# T-014-02 (FR-W4-04): target_paths() returns ALL apply_patch file headers so the
# gate can classify every file and let the most restrictive verdict win.
# Closes sdd-gate-apply-patch-multi-file-first-header-only.
# --------------------------------------------------------------------------- #


def test_target_paths_direct_key_single() -> None:
    assert _common.target_paths({"tool_input": {"file_path": "/a/b.py"}}) == ["/a/b.py"]
    assert _common.target_paths({"path": "/c.py"}) == ["/c.py"]
    assert _common.target_paths({"tool_input": {"notebook_path": "/n.ipynb"}}) == ["/n.ipynb"]


def test_target_paths_apply_patch_multi_file_all_headers() -> None:
    # REGRESSION repro: a multi-file patch whose FIRST file is allowed and whose SECOND
    # file is FROZEN. target_path() returns only README.md (the bug); target_paths()
    # must return BOTH headers so the FROZEN file is classified and blocks the patch.
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: README.md\n"
        "+ok\n"
        "*** Update File: specs/_archive/x.md\n"
        "+frozen\n"
        "*** Delete File: .dadaia/sessions/runtime/y.ptr\n"
        "*** End Patch"
    )
    assert _common.target_paths({"tool_input": {"command": cmd}}) == [
        "README.md",
        "specs/_archive/x.md",
        ".dadaia/sessions/runtime/y.ptr",
    ]


def test_target_paths_unparseable_returns_empty_list() -> None:
    assert _common.target_paths({"tool_input": {}}) == []


def test_target_path_still_returns_first_header_backcompat() -> None:
    # target_path() keeps its single-value contract (first header) for callers not yet
    # migrated; the bug fix lives in callers switching to target_paths().
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: README.md\n"
        "*** Update File: specs/_archive/x.md\n"
        "*** End Patch"
    )
    assert _common.target_path({"tool_input": {"command": cmd}}) == "README.md"


def test_sanitize_session_id_strips_traversal() -> None:
    # CWE-22: a session id with '/' or '..' must never survive as a path component.
    assert _common.sanitize_session_id("../../etc/passwd") == "etcpasswd"
    assert _common.sanitize_session_id("abc-123_XYZ") == "abc-123_XYZ"
    assert _common.sanitize_session_id(None) == ""


def test_resolve_session_id_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
    ):
        monkeypatch.delenv(var, raising=False)
    # Stdin field used when no env var is set.
    assert _common.resolve_session_id({"session_id": "from-stdin"}) == "from-stdin"
    # DADAIA_SESSION_ID overrides everything.
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-sid")
    monkeypatch.setenv("DADAIA_SESSION_ID", "explicit")
    assert _common.resolve_session_id({"session_id": "x"}) == "explicit"


def test_resolve_session_id_default(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
    ):
        monkeypatch.delenv(var, raising=False)
    assert _common.resolve_session_id({}, default="workspace") == "workspace"


def test_emit_block(capsys: pytest.CaptureFixture[str]) -> None:
    _common.emit_block("nope")
    out = json.loads(capsys.readouterr().out)
    assert out == {"decision": "block", "reason": "nope"}


def test_default_python_bin_prefers_venv(tmp_path: Path) -> None:
    from dadaia_workspace.core.platform import PLATFORM

    venv = tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv.mkdir(parents=True)
    py = venv / f"python{PLATFORM.venv_exe_suffix}"
    py.write_text("#!/bin/sh\n", encoding="utf-8")
    assert _common.default_python_bin(tmp_path) == str(py)


def test_default_python_bin_fallback(tmp_path: Path) -> None:
    result = _common.default_python_bin(tmp_path)
    assert result  # never empty; falls back to sys.executable or "python"


def test_atomic_write_text_roundtrip_unicode(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    _common.atomic_write_text(target, "café — ação 日本語")
    assert target.read_text(encoding="utf-8") == "café — ação 日本語"
    # No leftover temp files.
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_text_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    _common.atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_atomic_write_uses_os_replace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # os.replace is the atomic primitive (atomic on Windows too, unlike os.rename).
    calls: list[tuple[str, str]] = []
    real_replace = os.replace

    def spy(src: object, dst: object) -> None:
        calls.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    _common.atomic_write_text(tmp_path / "x.txt", "data")
    assert len(calls) == 1
