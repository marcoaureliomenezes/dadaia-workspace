"""Integration tests for the PROTECTED classifier + persona session-pointer fallback
in sdd-spec-gate.sh (T-017-15 + SEC-01).

T-017-15 added a persona session-pointer fallback to the backlog-ownership branch:
when no persona env var is set, the gate resolves the owning role from
``.dadaia/sessions/runtime/<session>.persona`` then the session JSON ``persona`` field
(mirroring the context ``.ptr`` fallback). It stays fail-closed.

SEC-01 (CWE-284): because the fallback trusts those pointer files, agent Write/Edit to
``.dadaia/sessions/**`` must be BLOCKED (CLASS=PROTECTED) so a confused-deputy agent
cannot forge a project-manager pointer and bypass the owner-only backlog gate. The
dadaia CLI writes session state via Python (outside the Write/Edit tool gate), so it is
unaffected by this block.

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
# SEC-01 — agent writes to .dadaia/sessions/** are BLOCKED (no pointer forgery)
# ---------------------------------------------------------------------------


def test_persona_pointer_write_blocked(tmp_path: Path) -> None:
    """Forging a .persona pointer via Write is blocked (CLASS=PROTECTED)."""
    ws = _build_workspace(tmp_path)
    target = str(ws / ".dadaia" / "sessions" / "runtime" / "evil.persona")
    stdout, rc = _run_gate(ws, tool="Write", file_path=target)
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"
    assert "CLI-owned runtime state" in data["reason"]
    assert "CWE-284" in data["reason"]


def test_session_json_write_blocked(tmp_path: Path) -> None:
    """Forging the session JSON (persona field) via Write is blocked."""
    ws = _build_workspace(tmp_path)
    target = str(ws / ".dadaia" / "sessions" / "evil.json")
    stdout, rc = _run_gate(ws, tool="Write", file_path=target)
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"


def test_nested_session_edit_blocked(tmp_path: Path) -> None:
    """Edit to any nested path under .dadaia/sessions/ is blocked too."""
    ws = _build_workspace(tmp_path)
    target = str(ws / ".dadaia" / "sessions" / "runtime" / "deep" / "x.persona")
    stdout, rc = _run_gate(ws, tool="Edit", file_path=target)
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"


def test_read_session_pointer_not_gated(tmp_path: Path) -> None:
    """Read (non-write tool) on a session pointer is never gated."""
    ws = _build_workspace(tmp_path)
    target = str(ws / ".dadaia" / "sessions" / "runtime" / "s.persona")
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


# ---------------------------------------------------------------------------
# T-017-15 — persona session-pointer fallback resolves the owner, fail-closed
# ---------------------------------------------------------------------------


def test_pointer_fallback_resolves_pm_allows_backlog(tmp_path: Path) -> None:
    """A CLI-written .persona pointer = project-manager resolves the owner → backlog allowed."""
    ws = _build_workspace(tmp_path)
    # Simulate the CLI/bootstrap writing the pointer (tests bypass the tool gate).
    (ws / ".dadaia" / "sessions" / "runtime" / "sess1.persona").write_text(
        "project-manager\n", encoding="utf-8"
    )
    target = str(ws / "specs" / "backlog" / "item.md")
    stdout, rc = _run_gate(
        ws, tool="Write", file_path=target, env_overrides={"DADAIA_SESSION_ID": "sess1"}
    )
    assert rc == 0
    assert stdout.strip() == "" or "block" not in stdout


def test_pointer_fallback_non_owner_blocks_backlog(tmp_path: Path) -> None:
    """A .persona pointer naming a non-owner still blocks backlog (fail-closed)."""
    ws = _build_workspace(tmp_path)
    (ws / ".dadaia" / "sessions" / "runtime" / "sess2.persona").write_text(
        "software-engineer\n", encoding="utf-8"
    )
    target = str(ws / "specs" / "backlog" / "item.md")
    stdout, rc = _run_gate(
        ws, tool="Write", file_path=target, env_overrides={"DADAIA_SESSION_ID": "sess2"}
    )
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"
    assert "software-engineer" in data["reason"]


def test_no_pointer_no_env_blocks_backlog(tmp_path: Path) -> None:
    """No env persona and no pointer → backlog write blocked (fail-closed)."""
    ws = _build_workspace(tmp_path)
    target = str(ws / "specs" / "backlog" / "item.md")
    stdout, rc = _run_gate(
        ws, tool="Write", file_path=target, env_overrides={"DADAIA_SESSION_ID": "ghost"}
    )
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"
    assert "unresolved" in data["reason"]


def test_env_persona_takes_precedence_over_pointer(tmp_path: Path) -> None:
    """Env var wins over the pointer: env=project-manager allows even if pointer says otherwise."""
    ws = _build_workspace(tmp_path)
    (ws / ".dadaia" / "sessions" / "runtime" / "sess3.persona").write_text(
        "software-engineer\n", encoding="utf-8"
    )
    target = str(ws / "specs" / "backlog" / "item.md")
    stdout, rc = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_SESSION_ID": "sess3", "DADAIA_AGENT_PERSONA": "project-manager"},
    )
    assert rc == 0
    assert stdout.strip() == "" or "block" not in stdout
