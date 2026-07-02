"""Harness-real behavior tests for dadaia_workspace.hooks.root_whitelist.

These drive ``root_whitelist`` as a real Claude Code harness does: a subprocess spawned with
:func:`claude_hook_env` and a ``PreToolUse`` payload piped to stdin. The gate signals ALLOW
with empty stdout and BLOCK with a ``{"decision":"block",...}`` envelope; both are asserted
on the subprocess result, never by importing ``main()`` in-process.

Rewritten from the old in-process ``root_whitelist.main()`` + ``sys.stdin`` simulation (the
pattern the harness-env contract bans). The workspace root the gate consults is delivered
through ``WORKSPACE_ROOT`` — a real harness-provided var — set by ``claude_hook_env``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


def _ws(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    return tmp_path


def _run(tmp_path: Path, payload: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """Invoke root_whitelist as a subprocess; return (stdout, parsed block envelope)."""
    env = claude_hook_env(tmp_path)
    result = run_hook_subprocess("root_whitelist", payload, env)
    assert result.returncode == 0, result.stderr
    return result.stdout, result.block_envelope()


def test_non_write_tool_allows(tmp_path: Path) -> None:
    _ws(tmp_path)
    out, block = _run(tmp_path, {"tool_name": "Read", "tool_input": {"path": "x"}})
    assert out == ""
    assert block is None


def test_whitelisted_root_entry_allows(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "AGENTS.md")}},
    )
    assert out == ""
    assert block is None


def test_pi_root_entry_allows(tmp_path: Path) -> None:
    """`.pi` is a whitelisted root entry (PI Layer-2 harness home).

    A write whose immediate parent is the workspace root and whose basename is ``.pi``
    must be ALLOWED; before T-PIO-05 this was BLOCKED.
    """
    ws = _ws(tmp_path)
    out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / ".pi")}},
    )
    assert out == ""
    assert block is None


def test_subdir_write_allows(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    target = ws / "repos" / "x" / "file.py"
    out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
    )
    assert out == ""
    assert block is None


def test_forbidden_root_entry_blocks(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "junk.txt")}},
    )
    assert block is not None
    assert block["decision"] == "block"
    assert "ROOT WHITELIST GATE" in block["reason"]


def test_operator_exception_allows(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    (ws / ".dadaia" / "states" / "root_exceptions.txt").write_text(
        "# operator exceptions\n*.png\n", encoding="utf-8"
    )
    out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "screenshot.png")}},
    )
    assert out == ""
    assert block is None


def test_unparseable_path_fails_open(tmp_path: Path) -> None:
    _ws(tmp_path)
    out, block = _run(tmp_path, {"tool_name": "Write", "tool_input": {}})
    assert out == ""
    assert block is None


# --- W1-6 (T-47-15): first-path-component classification --------------------------


def test_nested_write_under_new_toplevel_dir_blocks(tmp_path: Path) -> None:
    """A nested write that materializes a forbidden NEW top-level entry is blocked.

    ``<root>/.opencode/agents/foo.md`` used to be allowed (its immediate parent was not the
    root); it must now block because ``.opencode`` is a new, non-whitelisted top-level entry.
    """
    ws = _ws(tmp_path)
    target = ws / ".opencode" / "agents" / "foo.md"
    _out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
    )
    assert block is not None
    assert block["decision"] == "block"
    assert "ROOT WHITELIST GATE" in block["reason"]
    assert ".opencode" in block["reason"]


def test_nested_write_under_existing_operator_dir_allows(tmp_path: Path) -> None:
    """A nested write into an EXISTING (operator-created) top-level dir stays allowed.

    Only a not-yet-existing first component is blocked; an existing non-whitelisted
    top-level entry is presumed operator-created (fail-open per the Root Law).
    """
    ws = _ws(tmp_path)
    (ws / "operator-tool").mkdir()
    target = ws / "operator-tool" / "sub" / "note.txt"
    out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
    )
    assert out == ""
    assert block is None


def test_nested_write_under_whitelisted_root_allows(tmp_path: Path) -> None:
    """A deep write under a whitelisted root entry (.dadaia/...) is allowed regardless."""
    ws = _ws(tmp_path)
    target = ws / ".dadaia" / "tmp" / "agent" / "20260701" / "scratch.json"
    out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
    )
    assert out == ""
    assert block is None


def test_nested_exception_glob_allows(tmp_path: Path) -> None:
    """An operator-exception glob matching the first component allows a nested write."""
    ws = _ws(tmp_path)
    (ws / ".dadaia" / "states" / "root_exceptions.txt").write_text(".opencode\n", encoding="utf-8")
    target = ws / ".opencode" / "agents" / "foo.md"
    out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
    )
    assert out == ""
    assert block is None
