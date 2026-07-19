"""Harness-real behavior tests for dadaia_workspace.hooks.root_whitelist.

These drive ``root_whitelist`` as a real Claude Code harness does: a subprocess spawned with
:func:`claude_hook_env` and a ``PreToolUse`` payload piped to stdin. The gate signals ALLOW
with empty stdout and BLOCK with a ``{"decision":"block",...}`` envelope; both are asserted
on the subprocess result, never by importing ``main()`` in-process.

Rewritten from the old in-process ``root_whitelist.main()`` + ``sys.stdin`` simulation (the
pattern the harness-env contract bans). The workspace root the gate consults is delivered
through ``WORKSPACE_ROOT`` — a real harness-provided var — set by ``claude_hook_env``.

CRIT: root-whitelist is a deterministic enforcement policy — every current input survives
below as a named parametrized row, including the W1-6 first-path-component block and the
fail-open-for-existing-operator-dir decision.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

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


@pytest.mark.parametrize(
    ("name", "target_fn", "reason_fragment"),
    [
        ("forbidden_root_entry", lambda ws: ws / "junk.txt", "ROOT WHITELIST GATE"),
        (
            # W1-6 (T-47-15): a nested write that materializes a forbidden NEW top-level
            # entry is blocked. `<root>/.opencode/agents/foo.md` used to be allowed (its
            # immediate parent was not the root); it must now block because `.opencode` is
            # a new, non-whitelisted top-level entry.
            "nested_write_under_new_toplevel_dir",
            lambda ws: ws / ".opencode" / "agents" / "foo.md",
            ".opencode",
        ),
    ],
)
def test_block_table(
    tmp_path: Path, name: str, target_fn: Callable[[Path], Path], reason_fragment: str
) -> None:
    ws = _ws(tmp_path)
    target = target_fn(ws)
    _out, block = _run(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(target)}})
    assert block is not None
    assert block["decision"] == "block"
    assert "ROOT WHITELIST GATE" in block["reason"]
    assert reason_fragment in block["reason"]


@pytest.mark.parametrize(
    ("name", "setup_fn", "target_fn", "tool_name", "input_key"),
    [
        ("non_write_tool", None, lambda ws: "x", "Read", "path"),
        ("whitelisted_root_entry", None, lambda ws: ws / "AGENTS.md", "Write", "file_path"),
        (
            # `.pi` is a whitelisted root entry (PI Layer-2 harness home). A write whose
            # immediate parent is the workspace root and whose basename is `.pi` must be
            # ALLOWED; before T-PIO-05 this was BLOCKED.
            "pi_root_entry",
            None,
            lambda ws: ws / ".pi",
            "Write",
            "file_path",
        ),
        (
            # `.kimi-code` is a whitelisted root entry (Kimi Code Layer-1 harness home,
            # v0.2.8) — a root-level write of that basename must be ALLOWED.
            "kimi_code_root_entry",
            None,
            lambda ws: ws / ".kimi-code",
            "Write",
            "file_path",
        ),
        ("subdir_write", None, lambda ws: ws / "repos" / "x" / "file.py", "Write", "file_path"),
        ("unparseable_path_fails_open", None, None, "Write", None),
        (
            # A nested write into an EXISTING (operator-created) top-level dir stays
            # allowed. Only a not-yet-existing first component is blocked; an existing
            # non-whitelisted top-level entry is presumed operator-created (fail-open per
            # the Root Law).
            "nested_write_under_existing_operator_dir",
            lambda ws: (ws / "operator-tool").mkdir(),
            lambda ws: ws / "operator-tool" / "sub" / "note.txt",
            "Write",
            "file_path",
        ),
        (
            # A deep write under a whitelisted root entry (.dadaia/...) is allowed
            # regardless.
            "nested_write_under_whitelisted_root",
            None,
            lambda ws: ws / ".dadaia" / "tmp" / "agent" / "20260701" / "scratch.json",
            "Write",
            "file_path",
        ),
    ],
)
def test_allow_table(
    tmp_path: Path,
    name: str,
    setup_fn: Callable[[Path], object] | None,
    target_fn: Callable[[Path], object] | None,
    tool_name: str,
    input_key: str | None,
) -> None:
    ws = _ws(tmp_path)
    if setup_fn is not None:
        setup_fn(ws)
    tool_input: dict[str, Any] = {}
    if input_key is not None:
        target = target_fn(ws) if target_fn is not None else None
        tool_input = {input_key: str(target)}
    out, block = _run(tmp_path, {"tool_name": tool_name, "tool_input": tool_input})
    assert out == ""
    assert block is None


@pytest.mark.parametrize(
    ("name", "exceptions_content", "target_fn"),
    [
        ("exact_glob_match", "# operator exceptions\n*.png\n", lambda ws: ws / "screenshot.png"),
        (
            # An operator-exception glob matching the first component allows a nested
            # write.
            "nested_glob_matches_first_component",
            ".opencode\n",
            lambda ws: ws / ".opencode" / "agents" / "foo.md",
        ),
    ],
)
def test_exception_glob_table(
    tmp_path: Path, name: str, exceptions_content: str, target_fn: Callable[[Path], Path]
) -> None:
    ws = _ws(tmp_path)
    (ws / ".dadaia" / "states" / "root_exceptions.txt").write_text(
        exceptions_content, encoding="utf-8"
    )
    target = target_fn(ws)
    out, block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
    )
    assert out == ""
    assert block is None
