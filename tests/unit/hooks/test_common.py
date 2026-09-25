"""Unit tests for dadaia_workspace.hooks._common shared primitives.

CRIT: CWE-22 sanitize_session_id and the apply_patch multi-header extractor (feeds the
FROZEN/PROTECTED most-restrictive rule) are kept as standalone tests — never merged away.
``resolve_session_id`` precedence lives in test_common_sid_precedence.py (the single owner
of that seam, shared by gate/heartbeat/ctx-inject).
"""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from dadaia_workspace.hooks import _common


@pytest.mark.parametrize(
    ("stdin_text", "expected"),
    [
        (json.dumps({"tool_name": "Write"}), {"tool_name": "Write"}),
        ("   ", {}),
        ("{not json", {}),
        ("[1, 2, 3]", {}),
    ],
)
def test_read_stdin_json(
    monkeypatch: pytest.MonkeyPatch, stdin_text: str, expected: dict[str, Any]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
    assert _common.read_stdin_json() == expected


def test_target_path_forms() -> None:
    # tool_name / is_write_tool.
    assert _common.tool_name({"tool_name": "Write"}) == "Write"
    assert _common.tool_name({"tool": "edit_file"}) == "edit_file"
    assert _common.tool_name({}) == ""
    assert _common.is_write_tool("Write")
    assert _common.is_write_tool("apply_patch")
    assert not _common.is_write_tool("Read")

    # Direct keys.
    assert _common.target_path({"tool_input": {"file_path": "/a/b.py"}}) == "/a/b.py"
    assert _common.target_path({"path": "/c.py"}) == "/c.py"
    assert _common.target_path({"tool_input": {"notebook_path": "/n.ipynb"}}) == "/n.ipynb"
    # apply_patch header extraction.
    cmd = "*** Begin Patch\n*** Add File: repos/x/foo.py\n+code\n*** End Patch"
    assert _common.target_path({"tool_input": {"command": cmd}}) == "repos/x/foo.py"
    # Unparseable → empty.
    assert _common.target_path({"tool_input": {}}) == ""
    # Backcompat: target_path() keeps its single-value contract (first header) for
    # callers not yet migrated to target_paths().
    multi_cmd = (
        "*** Begin Patch\n"
        "*** Update File: README.md\n"
        "*** Update File: specs/backlog/_archive/x.md\n"
        "*** End Patch"
    )
    assert _common.target_path({"tool_input": {"command": multi_cmd}}) == "README.md"


def test_target_paths_multi_file_all_headers() -> None:
    """T-014-02 (FR-W4-04) regression: target_paths() returns ALL apply_patch file headers
    so the gate can classify every file and let the most restrictive verdict win — the
    unique failure detector this file exists to keep.
    """
    assert _common.target_paths({"tool_input": {"file_path": "/a/b.py"}}) == ["/a/b.py"]
    assert _common.target_paths({"path": "/c.py"}) == ["/c.py"]
    assert _common.target_paths({"tool_input": {"notebook_path": "/n.ipynb"}}) == ["/n.ipynb"]

    cmd = (
        "*** Begin Patch\n"
        "*** Update File: README.md\n"
        "+ok\n"
        "*** Update File: specs/backlog/_archive/x.md\n"
        "+frozen\n"
        "*** Delete File: .dadaia/sessions/runtime/y.ptr\n"
        "*** End Patch"
    )
    assert _common.target_paths({"tool_input": {"command": cmd}}) == [
        "README.md",
        "specs/backlog/_archive/x.md",
        ".dadaia/sessions/runtime/y.ptr",
    ]

    assert _common.target_paths({"tool_input": {}}) == []


def test_sanitize_session_id_strips_traversal() -> None:
    # CWE-22: a session id with '/' or '..' must never survive as a path component.
    assert _common.sanitize_session_id("../../etc/passwd") == "etcpasswd"
    assert _common.sanitize_session_id("abc-123_XYZ") == "abc-123_XYZ"
    assert _common.sanitize_session_id(None) == ""
