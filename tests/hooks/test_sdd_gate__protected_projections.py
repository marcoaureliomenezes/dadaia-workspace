"""agentic-projections-agent-writable: the schema and the harness wiring that judge a verdict are PROTECTED.

In-process `sdd_gate.evaluate_payload` on absolute paths, in a workspace with no install ledger.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.hooks import sdd_gate

_BUG = "agentic-projections-agent-writable"
_PROTECTED = (".dadaia/agentic/schemas/handoff-v1.schema.json", ".claude/settings.local.json")


def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(json.dumps({"contexts": []}), encoding="utf-8")
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
    assert sum(line.startswith(("fix:", "Operator action:")) for line in reason.splitlines()) == 1


@pytest.mark.small
def test_a_handoff_write_stays_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert (
        _verdict(_workspace(tmp_path, monkeypatch), "Write", ".dadaia/handoff/c/x.handoff.json")
        is None
    )
