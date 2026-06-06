"""Integration tests for RULE A2 — backlog ownership — in sdd-spec-gate.sh (T-D5-02).

Only project-manager may create/edit specs/backlog/** entries; every other agent is
a read-only consumer (rule: backlog-ownership). These tests invoke sdd-spec-gate.sh
as a black-box subprocess (the source of truth, not the projection), reusing the
same harness conventions as test_path_scope.py.

Coverage (new gate v0.1.6 contract):
- Non-PM agent write to specs/backlog/** → BLOCKED, error names the agent.
- project-manager write to specs/backlog/** → ALLOWED (ADDITIVE path, no persona block).
- Persona undetectable → fail-open (allowed), no [BACKLOG OWNERSHIP ERROR] emitted.
- Persona resolved via env chain (DADAIA_ > CLAUDE_ > CODEX_ > OPENCODE_).
- Block fires even when a session is active (ADDITIVE path block is pre-lease).
- Non-backlog paths are unaffected by RULE A2.

NOTE (v0.1.6 gate changes):
- payload _meta.agent_persona is NOT parsed by the new gate — persona must come via env.
- Log strings like "backlog-ownership ok" and "FAIL-OPEN backlog-ownership" are not emitted.
- Block JSON uses spaces: {"decision": "block", ...} not {"decision":"block",...}.
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


# ---------------------------------------------------------------------------
# Core acceptance — non-PM blocked, PM allowed
# ---------------------------------------------------------------------------


def test_non_pm_blocked_from_backlog(tmp_path: Path) -> None:
    """A non-project-manager agent writing specs/backlog/** is blocked, named."""
    ws = _build_workspace(tmp_path, agents=["product-engineer", "project-manager"])
    target = str(ws / "specs" / "backlog" / "new-item.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "product-engineer"},
    )
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"
    assert "[BACKLOG OWNERSHIP ERROR]" in data["reason"]
    assert "product-engineer" in data["reason"]
    assert "project-manager" in data["reason"]  # error explains who DOES own backlog


def test_non_pm_specialist_blocked_via_edit(tmp_path: Path) -> None:
    """Edit (not just Write) by a specialist is also blocked."""
    ws = _build_workspace(tmp_path, agents=["software-engineer-python", "project-manager"])
    target = str(ws / "specs" / "backlog" / "existing.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Edit",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "software-engineer-python"},
    )
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"
    assert "[BACKLOG OWNERSHIP ERROR]" in data["reason"]
    assert "software-engineer-python" in data["reason"]


def test_pm_allowed_to_write_backlog(tmp_path: Path) -> None:
    """project-manager writes specs/backlog/** without restriction."""
    ws = _build_workspace(tmp_path, agents=["project-manager"])
    target = str(ws / "specs" / "backlog" / "new-item.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "project-manager"},
    )
    assert rc == 0
    # ADDITIVE path (backlog) + PM persona → allowed (no block JSON emitted)
    assert stdout.strip() == "" or "block" not in stdout
    assert "[BACKLOG OWNERSHIP ERROR]" not in stdout


def test_pm_allowed_via_edit_and_nested_path(tmp_path: Path) -> None:
    """PM may edit nested backlog files too."""
    ws = _build_workspace(tmp_path, agents=["project-manager"])
    target = str(ws / "specs" / "backlog" / "subdir" / "item.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Edit",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "project-manager"},
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout


# ---------------------------------------------------------------------------
# Persona-resolution chain parity with RULE D
# ---------------------------------------------------------------------------


def test_harness_specific_env_resolves_persona(tmp_path: Path) -> None:
    """CLAUDE_AGENT_PERSONA resolves the writer when DADAIA_ is unset → blocked."""
    ws = _build_workspace(tmp_path, agents=["product-engineer", "project-manager"])
    target = str(ws / "specs" / "backlog" / "x.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"CLAUDE_AGENT_PERSONA": "product-engineer"},
    )
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"
    assert "[BACKLOG OWNERSHIP ERROR]" in data["reason"]
    assert "product-engineer" in data["reason"]


def test_payload_meta_not_parsed_fail_open(tmp_path: Path) -> None:
    """The new gate (v0.1.6) does NOT parse _meta.agent_persona from the payload.

    Persona must come via env vars (DADAIA_/CLAUDE_/CODEX_/OPENCODE_AGENT_PERSONA).
    With no env persona and only payload _meta → gate fails open (allowed).
    """
    ws = _build_workspace(tmp_path, agents=["researcher", "project-manager"])
    target = str(ws / "specs" / "backlog" / "x.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        payload_meta={"agent_persona": "researcher"},
        # No env persona set
    )
    assert rc == 0
    # Without an env-var persona the gate fails open — no block emitted
    assert stdout.strip() == "" or "BACKLOG OWNERSHIP ERROR" not in stdout


def test_dadaia_persona_takes_priority(tmp_path: Path) -> None:
    """DADAIA_AGENT_PERSONA wins over CLAUDE_AGENT_PERSONA (priority order)."""
    ws = _build_workspace(tmp_path, agents=["product-engineer", "project-manager"])
    target = str(ws / "specs" / "backlog" / "x.md")

    # DADAIA_ says PM (allow); CLAUDE_ says PE (would block) — DADAIA_ must win → allow.
    stdout, rc, _log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={
            "DADAIA_AGENT_PERSONA": "project-manager",
            "CLAUDE_AGENT_PERSONA": "product-engineer",
        },
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout


# ---------------------------------------------------------------------------
# Fail-open + ordering invariants
# ---------------------------------------------------------------------------


def test_persona_undetectable_fail_open(tmp_path: Path) -> None:
    """No persona signal at all → fail-open (allowed), consistent with RULE D.

    New gate does not emit "FAIL-OPEN backlog-ownership" — it simply allows
    via the ADDITIVE path when no persona env var is set.
    """
    ws = _build_workspace(tmp_path, agents=["project-manager"])
    target = str(ws / "specs" / "backlog" / "x.md")

    stdout, rc, log = _run_gate(ws, tool="Write", file_path=target)
    assert rc == 0
    # No persona → no [BACKLOG OWNERSHIP ERROR] block
    assert "[BACKLOG OWNERSHIP ERROR]" not in stdout
    assert stdout.strip() == ""


def test_block_fires_regardless_of_session(tmp_path: Path) -> None:
    """RULE A2 blocks a non-PM backlog write regardless of whether a session is active.

    The new gate (v0.1.6) processes backlog paths as ADDITIVE and checks the
    persona gate before allowing the write — having a DADAIA_SESSION_ID does not
    bypass the [BACKLOG OWNERSHIP ERROR] block for non-PM agents.
    """
    ws = _build_workspace(tmp_path, agents=["product-engineer", "project-manager"])
    target = str(ws / "specs" / "backlog" / "x.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={
            "DADAIA_AGENT_PERSONA": "product-engineer",
            "DADAIA_SESSION_ID": "irrelevant-session-id",
        },
    )
    assert rc == 0
    data = json.loads(stdout.strip())
    assert data["decision"] == "block"
    assert "[BACKLOG OWNERSHIP ERROR]" in data["reason"]


def test_non_backlog_path_unaffected(tmp_path: Path) -> None:
    """A non-backlog path is not subject to RULE A2 (no backlog block fires)."""
    ws = _build_workspace(tmp_path, agents=["product-engineer", "project-manager"])
    # SPEC.md is a meta-edit path; product-engineer may write it (no backlog block).
    target = str(ws / "specs" / "releases" / "test-release-v1" / "SPEC.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "product-engineer"},
    )
    assert rc == 0
    assert "[BACKLOG OWNERSHIP ERROR]" not in stdout


def test_non_write_tool_passes_through(tmp_path: Path) -> None:
    """Read on a backlog file is never gated (non-write tool)."""
    ws = _build_workspace(tmp_path, agents=["product-engineer"])
    target = str(ws / "specs" / "backlog" / "x.md")

    stdout, rc, _log = _run_gate(
        ws,
        tool="Read",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "product-engineer"},
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
