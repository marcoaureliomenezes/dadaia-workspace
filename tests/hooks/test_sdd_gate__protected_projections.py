"""The schema and the harness wiring that judge a verdict are PROTECTED.

In-process `sdd_gate.evaluate_payload` on absolute paths, in a workspace with no install ledger.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.hooks import sdd_gate
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess
from tests.helpers.oslib import write_text

_BUG = "agentic-projections-agent-writable"
_PROTECTED = (
    ".dadaia/agentic/schemas/handoff-v1.schema.json",
    ".claude/settings.local.json",
    ".dadaia/states/verdicts/c/x.handoff.json",
)


def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    write_text(states / "spec_contexts.json", json.dumps({"contexts": []}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    return tmp_path


def _verdict(root: Path, tool: str, rel: str) -> str | None:
    return sdd_gate.evaluate_payload(
        {"tool_name": tool, "tool_input": {"file_path": str(root / rel)}, "session_id": "s"}
    )


@pytest.mark.small
@pytest.mark.parametrize("tool", ["Write", "Edit"])
@pytest.mark.parametrize("rel", _PROTECTED)
def test_an_agent_write_to_a_judging_projection_is_blocked_with_one_fix_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tool: str, rel: str
) -> None:
    reason = _verdict(_workspace(tmp_path, monkeypatch), tool, rel)

    assert reason is not None
    assert sum(line.startswith(("fix:", "Agent action:")) for line in reason.splitlines()) == 1


@pytest.mark.small
def test_a_handoff_write_stays_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert (
        _verdict(_workspace(tmp_path, monkeypatch), "Write", ".dadaia/handoff/c/x.handoff.json")
        is None
    )


_VERDICT_RUN = "python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py /t --sha a --context c --slug s --verdict APPROVED --reason r"
_STATS = "python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py stats 0.5.0-rc22"


def _bash(ws: Path, runtime: str | None, command: str, over: dict[str, object]) -> str | None:
    """The block reason the real hook prints for a Bash call under harness *runtime*."""
    env = claude_hook_env(ws, extra={"DADAIA_RUNTIME": runtime} if runtime else None)
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, **over}
    done = run_hook_subprocess("sdd_gate", payload, env)
    assert done.returncode == 0, done.stderr
    block = done.block_envelope()
    return None if block is None else str(block["reason"])


@pytest.mark.medium
@pytest.mark.parametrize(
    ("runtime", "command", "over", "blocked"),
    [
        ("claude", _VERDICT_RUN, {}, True),
        ("claude", _VERDICT_RUN, {"agent_type": None}, True),
        ("claude", _VERDICT_RUN, {"agent_type": "dd-sw-engineer-sr"}, True),
        ("claude", _VERDICT_RUN, {"agent_type": "dd-code-reviewer"}, False),
        ("claude", _STATS, {}, False),
        ("claude", "ls", {}, False),
        ("codex", _VERDICT_RUN, {}, False),
        ("kimi-code", _VERDICT_RUN, {}, False),
        (None, _VERDICT_RUN, {}, False),
    ],
)
def test_the_main_thread_cannot_run_the_verdict_writer_where_the_harness_names_subagents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runtime: str | None,
    command: str,
    over: dict[str, object],
    blocked: bool,
) -> None:
    reason = _bash(_workspace(tmp_path, monkeypatch), runtime, command, over)
    assert (reason is not None) is blocked
