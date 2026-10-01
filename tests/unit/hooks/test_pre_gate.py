"""The merged PreToolUse entrypoint ``pre_gate``: first-block-wins over its policies, and
the one envelope every harness parses.

Intent: CONTRACT — T-014-03 (parity with sdd_gate + root_whitelist through one spawn),
pre-gate-allow-envelope-fails-claude-schema, claude-pre-gate-envelope-contract (the
kimi shim's two raw anchors), the Bash arm wired to venv_guard.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.hooks import pre_gate
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

_PATCH = "*** Begin Patch\n*** Update File: worktrees/a/0.5.0a-impl/README.md\n+ok\n*** Update File: {}\n+x\n*** End Patch"


def _spawn(ws: Path, payload: dict[str, Any]) -> Any:
    env = claude_hook_env(ws, session_id="s")
    env.pop("DADAIA_CONTEXT", None)
    result = run_hook_subprocess("pre_gate", {**payload, "session_id": "s"}, env)
    assert result.returncode == 0, result.stderr
    return result


@pytest.mark.parametrize(
    ("tool", "tool_input", "want"),
    [
        ("Write", {"file_path": "repos/a/src/thing.py"}, "worktree.py new a --kind impl"),
        ("NotebookEdit", {"notebook_path": "junk.ipynb"}, None),
        ("Read", {"file_path": "x"}, None),
        ("Write", {"file_path": ".dadaia/sessions/a.json"}, "SEC-01"),
        ("Write", {"file_path": "junk.txt"}, "ROOT WHITELIST GATE"),
        ("apply_patch", {"command": _PATCH.format(".dadaia/sessions/a.json")}, "SEC-01"),
    ],
    ids=[
        "in-repo-write-is-merge-only",
        "notebook-edit-is-root-whitelist-exempt",
        "non-write-tool-allows",
        "protected-sessions-fails-closed",
        "root-whitelist-forbidden-entry-blocks",
        "apply-patch-most-restrictive-header-blocks-the-whole-patch",
    ],
)
def test_non_write_and_protected_matrix(
    tmp_path: Path, tool: str, tool_input: dict[str, str], want: str | None
) -> None:
    """Through one spawn, pre_gate reproduces the standalone sdd_gate and root_whitelist
    verdicts (paths are workspace-relative; ``want`` names the block reason)."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": "a", "state": "alive"}]}), encoding="utf-8"
    )
    (tmp_path / "repos" / "a" / "specs").mkdir(parents=True)
    rooted = {k: v if k == "command" else str(tmp_path / v) for k, v in tool_input.items()}
    block = _spawn(tmp_path, {"tool_name": tool, "tool_input": rooted}).block_envelope()
    if want is None:
        assert block is None, block
    else:
        assert block is not None and want in block["reason"], block


def test_evaluate_payload_first_block_wins_and_faulty_policy_fails_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def rw(_p: dict[str, object]) -> str | None:
        calls.append("rw")
        return "ROOT BLOCK"

    def sdd(_p: dict[str, object]) -> str | None:
        calls.append("sdd")
        return "SDD BLOCK"

    monkeypatch.setattr(pre_gate, "_POLICIES", (rw, sdd))
    assert pre_gate.evaluate_payload({"tool_name": "Write"}) == "ROOT BLOCK"
    assert calls == ["rw"]

    def explode(_p: dict[str, object]) -> str | None:
        raise RuntimeError("boom")

    monkeypatch.setattr(pre_gate, "_POLICIES", (explode, lambda _p: None))
    assert pre_gate.evaluate_payload({"tool_name": "Write"}) is None


@pytest.mark.parametrize(
    ("payload", "blocked"),
    [
        ({"tool_name": "Read", "tool_input": {"file_path": "x"}}, False),
        ({"tool_name": "Bash", "tool_input": {"command": "pip install requests"}}, False),
        ({"tool_name": "Bash", "tool_input": {"command": "dadaia doctor"}}, True),
    ],
    ids=["allow", "allow-bash-pip", "block-bash-venv-guard"],
)
def test_envelope_contract(tmp_path: Path, payload: dict[str, Any], blocked: bool) -> None:
    """Whole stdout is ONE JSON object. Allow carries no verdict at all (Claude's schema
    rejects ``decision: allow`` and interactive sessions ignore ``defer``). Block carries the
    legacy ``"decision": "block"`` (codex + the kimi shim's grep) AND
    ``permissionDecision: deny`` with the same reason, top-level ``reason`` LAST (the shim's
    sed capture); the Bash block is venv_guard's, with the corrected command."""
    raw = _spawn(tmp_path, payload).stdout.strip()
    envelope = json.loads(raw)
    if not blocked:
        assert envelope == {"continue": True, "hookSpecificOutput": {"hookEventName": "PreToolUse"}}
        assert '"decision": "block"' not in raw
        return
    reason = envelope["reason"]
    assert envelope["decision"] == "block"
    assert envelope["hookSpecificOutput"] == {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
    assert '"decision": "block"' in raw
    assert raw.index('"hookSpecificOutput"') < raw.index('"reason": "')
    assert "VENV GUARD" in reason.upper() and ".dadaia/.venv/bin" in reason
