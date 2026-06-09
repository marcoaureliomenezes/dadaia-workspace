"""Integration tests for the PROTECTED classifier in sdd-spec-gate.sh (SEC-01).

``.dadaia/sessions/**`` is CLI-owned runtime state. Most importantly it holds the
single-session lease identity pointer (``.dadaia/sessions/runtime/<ctx>.ptr``) — the
key to the ONE deterministic lock the product keeps. Agent Write/Edit to
``.dadaia/sessions/**`` must be BLOCKED (CLASS=PROTECTED, CWE-284) so a confused-deputy
agent cannot forge the lease ``.ptr`` and steal a Spec Context binding from the holding
session. The dadaia CLI writes session state via Python (outside the Write/Edit tool
gate), so it is unaffected by this block.

History: 0.1.7 rc-3 removed the backlog-ownership persona gate (a lock with no key), so
``.dadaia/sessions/**`` is no longer protected to guard a *persona* pointer — it is
protected to guard *lease identity*. The PROTECTED behavior itself is unchanged; only
its rationale moved. The obsolete persona-pointer→backlog-resolution tests were removed
with the persona gate; backlog ADDITIVE-allow is covered in test_backlog_ownership.py.

These tests invoke the gate source as a black-box subprocess, reusing the harness
conventions of test_backlog_ownership.py.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_GATE = (
    Path(__file__).parent.parent.parent.parent
    / "dadaia_workspace"
    / "public"
    / "scripts"
    / "sdd-spec-gate.sh"
)


def _build_workspace(tmp_path: Path) -> Path:
    """Minimal workspace tree: an ALIVE context + a backlog dir + a sessions dir."""
    state_dir = tmp_path / ".dadaia" / "states"
    state_dir.mkdir(parents=True)
    ctx_data = {
        "schema_version": "2",
        "contexts": [
            {
                "name": "dadaia-workspace",
                "state": "alive",
                "repo_slug": "dadaia-workspace",
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00+00:00",
                "alive_since": "2026-01-01T00:00:00+00:00",
                "dead_since": None,
                "current_branch": "main",
            }
        ],
    }
    (state_dir / "spec_contexts.json").write_text(json.dumps(ctx_data, indent=2), encoding="utf-8")
    (tmp_path / "specs" / "backlog").mkdir(parents=True)
    (tmp_path / ".dadaia" / "sessions" / "runtime").mkdir(parents=True)
    return tmp_path


def _run_gate(
    ws: Path,
    tool: str,
    file_path: str,
    env_overrides: dict[str, str] | None = None,
) -> tuple[str, int]:
    payload: dict = {"tool_name": tool, "tool_input": {"file_path": file_path}}
    env = os.environ.copy()
    for key in [
        "DADAIA_AGENT_PERSONA",
        "CLAUDE_AGENT_PERSONA",
        "CODEX_AGENT_PERSONA",
        "OPENCODE_AGENT_PERSONA",
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
    ]:
        env.pop(key, None)
    env["WORKSPACE_ROOT"] = str(ws)
    env["SDD_GATE_LOG"] = str(ws / "gate.log")
    if env_overrides:
        env.update(env_overrides)
    result = subprocess.run(
        ["bash", str(_GATE)],
        input=json.dumps(payload),
        env=env,
        capture_output=True,
        text=True,
    )
    return result.stdout, result.returncode


# ---------------------------------------------------------------------------
# SEC-01 — agent writes to .dadaia/sessions/** are BLOCKED (no lease .ptr forgery)
# ---------------------------------------------------------------------------


def test_lease_pointer_write_blocked(tmp_path: Path) -> None:
    """Forging a lease .ptr via Write is blocked (CLASS=PROTECTED)."""
    ws = _build_workspace(tmp_path)
    target = str(ws / ".dadaia" / "sessions" / "runtime" / "dadaia-workspace.ptr")
    stdout, rc = _run_gate(ws, tool="Write", file_path=target)
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"
    assert "CLI-owned runtime state" in data["reason"]
    assert "CWE-284" in data["reason"]


def test_session_json_write_blocked(tmp_path: Path) -> None:
    """Forging the session JSON via Write is blocked."""
    ws = _build_workspace(tmp_path)
    target = str(ws / ".dadaia" / "sessions" / "evil.json")
    stdout, rc = _run_gate(ws, tool="Write", file_path=target)
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"


def test_nested_session_edit_blocked(tmp_path: Path) -> None:
    """Edit to any nested path under .dadaia/sessions/ is blocked too."""
    ws = _build_workspace(tmp_path)
    target = str(ws / ".dadaia" / "sessions" / "runtime" / "deep" / "x.ptr")
    stdout, rc = _run_gate(ws, tool="Edit", file_path=target)
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"


def test_read_session_pointer_not_gated(tmp_path: Path) -> None:
    """Read (non-write tool) on a session pointer is never gated."""
    ws = _build_workspace(tmp_path)
    target = str(ws / ".dadaia" / "sessions" / "runtime" / "s.ptr")
    stdout, rc = _run_gate(ws, tool="Read", file_path=target)
    assert rc == 0
    assert "block" not in stdout


def test_other_dadaia_path_not_protected(tmp_path: Path) -> None:
    """A non-sessions .dadaia path (reports) is ADDITIVE/allowed, not PROTECTED."""
    ws = _build_workspace(tmp_path)
    (ws / ".dadaia" / "reports").mkdir(parents=True)
    target = str(ws / ".dadaia" / "reports" / "x.html")
    stdout, rc = _run_gate(ws, tool="Write", file_path=target)
    assert rc == 0
    assert "CLI-owned runtime state" not in stdout


def test_backlog_allowed_even_with_session_pointer_present(tmp_path: Path) -> None:
    """A .ptr present in the session dir does not change backlog ADDITIVE-allow.

    Regression guard: the removed persona gate used to read a .persona pointer here to
    decide backlog ownership. That coupling is gone — backlog flows regardless.
    """
    ws = _build_workspace(tmp_path)
    (ws / ".dadaia" / "sessions" / "runtime" / "sess1.ptr").write_text("sess1\n", encoding="utf-8")
    target = str(ws / "specs" / "backlog" / "item.md")
    stdout, rc = _run_gate(
        ws, tool="Write", file_path=target, env_overrides={"DADAIA_SESSION_ID": "sess1"}
    )
    assert rc == 0
    assert "block" not in stdout
