"""Integration tests for the backlog contract in sdd-spec-gate.sh.

0.1.7 rc-3 removed the backlog-ownership *persona gate*. It was a lock with no key:
no harness sets *_AGENT_PERSONA in the hook process environment and no CLI writes the
.persona pointer, so the legitimate owner (project-manager) was blocked in every
harness (Codex + Claude, both reproduced). Ownership is now a coordination convention
(rule: backlog-ownership), not a gate.

New contract: specs/backlog/** is a plain ADDITIVE path — writes ALWAYS flow,
regardless of persona, exactly like specs/bugs/** and specs/audits/**. The only
deterministic lock in the workspace is the single-session MUTATING lease.

These tests invoke sdd-spec-gate.sh as a black-box subprocess (the source of truth,
not the projection), reusing the harness conventions of test_path_scope.py.
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


def _make_agent_md(name: str) -> str:
    return f"---\nname: {name}\ndescription: Test agent {name}.\n---\n\n# {name.title()}\n"


def _build_workspace(tmp_path: Path, agents: list[str]) -> Path:
    """Minimal workspace tree: agent files + a release with a [-] marker + context."""
    agents_dir = tmp_path / "dadaia_workspace" / "public" / "agents"
    agents_dir.mkdir(parents=True)
    for agent_name in agents:
        (agents_dir / f"{agent_name}.md").write_text(_make_agent_md(agent_name), encoding="utf-8")

    rel = "test-release-v1"
    rel_dir = tmp_path / "specs" / "releases" / rel
    rel_dir.mkdir(parents=True)
    (tmp_path / "specs" / "releases" / "ACTIVE.md").write_text(
        f"release: {rel}\nphase: TASKS\n", encoding="utf-8"
    )
    (rel_dir / "TASKS.md").write_text(
        "# Tasks\n\n- [-] T001 — in-progress task\n", encoding="utf-8"
    )
    (tmp_path / "specs" / "backlog").mkdir(parents=True)

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
    return tmp_path


def _run_gate(
    ws: Path,
    tool: str,
    file_path: str,
    env_overrides: dict[str, str] | None = None,
    payload_meta: dict[str, str] | None = None,
    log_path: Path | None = None,
) -> tuple[str, int, str]:
    if log_path is None:
        log_path = ws / "gate.log"

    payload: dict = {"tool_name": tool, "tool_input": {"file_path": file_path}}
    if payload_meta:
        payload["tool_input"]["_meta"] = payload_meta

    env = os.environ.copy()
    for key in [
        "DADAIA_AGENT_PERSONA",
        "CLAUDE_AGENT_PERSONA",
        "CODEX_AGENT_PERSONA",
        "OPENCODE_AGENT_PERSONA",
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "SDD_LEGACY_FEATURES",
    ]:
        env.pop(key, None)
    env["WORKSPACE_ROOT"] = str(ws)
    env["SDD_GATE_LOG"] = str(log_path)
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        ["bash", str(_GATE)],
        input=json.dumps(payload),
        env=env,
        capture_output=True,
        text=True,
    )
    log_contents = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    return result.stdout, result.returncode, log_contents


def _assert_allowed(stdout: str, rc: int) -> None:
    """A gate ALLOW = exit 0 and no block-decision JSON on stdout."""
    assert rc == 0
    assert "block" not in stdout
    assert "[BACKLOG OWNERSHIP ERROR]" not in stdout


# ---------------------------------------------------------------------------
# New contract — backlog ALWAYS flows (ownership is a convention, not a gate)
# ---------------------------------------------------------------------------


def test_backlog_write_no_persona_is_allowed(tmp_path: Path) -> None:
    """The exact bug repro: a backlog write with NO persona is now ALLOWED.

    This is the case that blocked the legitimate owner in every harness (no harness
    sets *_AGENT_PERSONA in the hook env). It must flow.
    """
    ws = _build_workspace(tmp_path, agents=["project-manager"])
    target = str(ws / "specs" / "backlog" / "new-item.md")

    stdout, rc, _log = _run_gate(ws, tool="Write", file_path=target)
    _assert_allowed(stdout, rc)


def test_backlog_write_as_pm_is_allowed(tmp_path: Path) -> None:
    """project-manager writes backlog freely."""
    ws = _build_workspace(tmp_path, agents=["project-manager"])
    target = str(ws / "specs" / "backlog" / "new-item.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "project-manager"},
    )
    _assert_allowed(stdout, rc)


def test_backlog_write_as_non_pm_is_allowed(tmp_path: Path) -> None:
    """A non-PM persona is no longer blocked — ownership is a convention, not a gate."""
    ws = _build_workspace(tmp_path, agents=["product-engineer", "project-manager"])
    target = str(ws / "specs" / "backlog" / "new-item.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "product-engineer"},
    )
    _assert_allowed(stdout, rc)


def test_backlog_edit_and_nested_path_allowed(tmp_path: Path) -> None:
    """Edit (not just Write) and nested backlog files flow too."""
    ws = _build_workspace(tmp_path, agents=["software-engineer"])
    target = str(ws / "specs" / "backlog" / "subdir" / "item.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Edit",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "software-engineer"},
    )
    _assert_allowed(stdout, rc)


def test_backlog_write_with_active_session_allowed(tmp_path: Path) -> None:
    """Having a session id does not change the backlog ADDITIVE-allow outcome."""
    ws = _build_workspace(tmp_path, agents=["project-manager"])
    target = str(ws / "specs" / "backlog" / "x.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_SESSION_ID": "some-session-id"},
    )
    _assert_allowed(stdout, rc)


def test_backlog_read_passes_through(tmp_path: Path) -> None:
    """Read on a backlog file is never gated (non-write tool)."""
    ws = _build_workspace(tmp_path, agents=["product-engineer"])
    target = str(ws / "specs" / "backlog" / "x.md")

    stdout, rc, _log = _run_gate(ws, tool="Read", file_path=target)
    _assert_allowed(stdout, rc)


def test_no_backlog_ownership_error_token_anywhere(tmp_path: Path) -> None:
    """The retired error token must never appear — the branch is deleted."""
    ws = _build_workspace(tmp_path, agents=["product-engineer", "project-manager"])
    for persona in ("product-engineer", "project-manager", ""):
        env = {"DADAIA_AGENT_PERSONA": persona} if persona else None
        stdout, rc, _log = _run_gate(
            ws,
            tool="Write",
            file_path=str(ws / "specs" / "backlog" / "x.md"),
            env_overrides=env,
        )
        assert rc == 0
        assert "[BACKLOG OWNERSHIP ERROR]" not in stdout
